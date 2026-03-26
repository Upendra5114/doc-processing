import asyncio
import json
import threading
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import StateGraph, END

from utils.database import AsyncItemRepository
from utils.ocr import extract_text_from_jpg
from utils.pdf_to_jpg import pdf_to_jpgs
from examples import run_llm_on_paragraph, process_llm_output


class PipelineState(TypedDict, total=False):
    input_path: str
    db_path: str
    image_paths: list[str]
    ocr_texts: list[str]
    llm_outputs: list[str]
    uploaded_count: int
    db_rows: list[dict[str, Any]]
    result_json: str


def _is_image_file(path: Path) -> bool:
    return path.suffix.lower() in {".jpg", ".jpeg", ".png"}


def collect_images_from_dir(directory: Path) -> list[str]:
    files = sorted([p for p in directory.iterdir() if p.is_file() and _is_image_file(p)])
    return [str(p) for p in files]


def node_route_input(state: PipelineState) -> PipelineState:
    input_path = Path(state["input_path"])
    if not input_path.exists():
        raise FileNotFoundError(f"Input path not found: {input_path}")

    image_paths: list[str] = []

    if input_path.is_file():
        if input_path.suffix.lower() == ".pdf":
            out_dir = input_path.parent / f"{input_path.stem}_images"
            image_paths = pdf_to_jpgs(input_path, out_dir, dpi=200)
        elif _is_image_file(input_path):
            image_paths = [str(input_path)]
        else:
            raise ValueError("Unsupported file type. Use PDF or image.")
    elif input_path.is_dir():
        image_paths = collect_images_from_dir(input_path)
        if not image_paths:
            raise ValueError(f"No images found in directory: {input_path}")
    else:
        raise ValueError("Unsupported input path type.")

    return {"image_paths": image_paths}


def node_ocr(state: PipelineState) -> PipelineState:
    texts: list[str] = []
    for img in state["image_paths"]:
        texts.append(extract_text_from_jpg(img))
    return {"ocr_texts": texts}


def _run_coro_sync(coro):
    """
    Run coroutine from sync code, whether or not an event loop is already running.
    """
    try:
        asyncio.get_running_loop()
        loop_running = True
    except RuntimeError:
        loop_running = False

    if not loop_running:
        return asyncio.run(coro)

    result = {}
    error = {}

    def _runner():
        try:
            result["value"] = asyncio.run(coro)
        except Exception as e:
            error["exc"] = e

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    t.join()

    if "exc" in error:
        raise error["exc"]
    return result.get("value")


def node_llm_and_db(state: PipelineState) -> PipelineState:
    llm_outputs: list[str] = []
    uploaded_total = 0
    db_path = state.get("db_path", "data.db")

    async def _run():
        nonlocal llm_outputs, uploaded_total
        for text in state["ocr_texts"]:
            generated = run_llm_on_paragraph(text)
            llm_outputs.append(generated)
            result = await process_llm_output(generated, db_path=db_path)
            uploaded_total += int(result.get("uploaded_count", 0))
        return uploaded_total

    _run_coro_sync(_run())
    return {"llm_outputs": llm_outputs, "uploaded_count": uploaded_total}


def node_fetch_db_as_json(state: PipelineState) -> PipelineState:
    db_path = state.get("db_path", "data.db")

    async def _fetch() -> list[dict[str, Any]]:
        repo = AsyncItemRepository(db_path=db_path)
        await repo.init()
        rows = await repo.list_all()
        # date -> iso string for JSON serialization
        for r in rows:
            if "date" in r and hasattr(r["date"], "isoformat"):
                r["date"] = r["date"].isoformat()
        return rows

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop -> safe
        rows = asyncio.run(_fetch())
    else:
        # Running loop exists -> run in a separate thread with its own loop
        result = {}
        err = {}

        def runner():
            try:
                result["rows"] = asyncio.run(_fetch())
            except Exception as e:
                err["e"] = e

        t = threading.Thread(target=runner, daemon=True)
        t.start()
        t.join()

        if "e" in err:
            raise err["e"]
        rows = result["rows"]

    result_json = json.dumps(rows, ensure_ascii=False, indent=2)
    return {"db_rows": rows, "result_json": result_json}


def build_graph():
    graph = StateGraph(PipelineState)

    graph.add_node("route_input", node_route_input)
    graph.add_node("ocr", node_ocr)
    graph.add_node("llm_and_db", node_llm_and_db)
    graph.add_node("fetch_db_json", node_fetch_db_as_json)

    graph.set_entry_point("route_input")
    graph.add_edge("route_input", "ocr")
    graph.add_edge("ocr", "llm_and_db")
    graph.add_edge("llm_and_db", "fetch_db_json")
    graph.add_edge("fetch_db_json", END)

    return graph.compile()


def run_pipeline(input_path: str, db_path: str = "data.db") -> str:
    app = build_graph()
    final_state = app.invoke({"input_path": input_path, "db_path": db_path})
    return final_state["result_json"]


if __name__ == "__main__":
    # Example:
    # 1) PDF file
    # print(run_pipeline("/path/to/file.pdf"))
    # 2) Single image
    # print(run_pipeline("/path/to/image.jpg"))
    # 3) Directory with multiple images
    # print(run_pipeline("/path/to/images_dir"))
    pass