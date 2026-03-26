from pathlib import Path
from tempfile import TemporaryDirectory
import asyncio
import base64
import json
import logging
import time
import contextlib
from typing import Callable, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from main import run_pipeline

logger = logging.getLogger("doc-processing")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Doc Processing API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _heartbeat(websocket: WebSocket, stop_event: asyncio.Event, interval_sec: int = 15):
    while not stop_event.is_set():
        await asyncio.sleep(interval_sec)
        if stop_event.is_set():
            break
        await websocket.send_json({"event": "ping", "ts": int(time.time())})


@app.websocket("/ws/process")
async def ws_process(websocket: WebSocket):
    await websocket.accept()
    client = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown"
    logger.info("Frontend connected: %s", client)
    await websocket.send_json({"event": "connected", "client": client})

    heartbeat_stop = asyncio.Event()
    heartbeat_task: Optional[asyncio.Task] = asyncio.create_task(_heartbeat(websocket, heartbeat_stop))

    try:
        while True:
            msg = await websocket.receive_json()
            action = msg.get("action")

            if action == "pong":
                continue

            if action != "process":
                await websocket.send_json({"event": "error", "detail": "Unsupported action"})
                continue

            filename = msg.get("filename", "upload")
            db_path = msg.get("db_path", "data.db")
            file_b64 = msg.get("file_b64")

            if not file_b64:
                await websocket.send_json({"event": "error", "detail": "file_b64 is required"})
                continue

            suffix = Path(filename).suffix.lower()
            if suffix not in {".pdf", ".jpg", ".jpeg", ".png"}:
                await websocket.send_json({"event": "error", "detail": "Only .pdf, .jpg, .jpeg, .png are supported"})
                continue

            def progress_cb(stage_index: int, status: str, detail: Optional[str] = None):
                async def _send():
                    payload = {"event": "step", "index": stage_index, "status": status}
                    if detail:
                        payload["detail"] = detail
                    await websocket.send_json(payload)
                asyncio.create_task(_send())

            def log_cb(message: str):
                async def _send():
                    await websocket.send_json({"event": "log", "message": message})
                asyncio.create_task(_send())

            await websocket.send_json({"event": "step", "index": 0, "status": "running"})
            try:
                with TemporaryDirectory() as tmpdir:
                    temp_path = Path(tmpdir) / filename
                    content = base64.b64decode(file_b64)
                    temp_path.write_bytes(content)

                    await websocket.send_json({"event": "step", "index": 0, "status": "done"})
                    await websocket.send_json({"event": "step", "index": 1, "status": "done"})
                    await websocket.send_json({"event": "step", "index": 2, "status": "running"})
                    await websocket.send_json({"event": "step", "index": 3, "status": "running"})
                    await websocket.send_json({"event": "step", "index": 4, "status": "running"})

                    loop = asyncio.get_running_loop()

                    # If run_pipeline supports callbacks, these will stream node/stage updates.
                    # If not, it still works with existing signature.
                    def _run():
                        try:
                            return run_pipeline(
                                str(temp_path),
                                db_path,
                                progress_callback=progress_cb,
                                log_callback=log_cb,
                            )
                        except TypeError:
                            return run_pipeline(str(temp_path), db_path)

                    result_json = await loop.run_in_executor(None, _run)

                    await websocket.send_json({"event": "step", "index": 2, "status": "done"})
                    await websocket.send_json({"event": "step", "index": 3, "status": "done"})
                    await websocket.send_json({"event": "step", "index": 4, "status": "done"})
                    await websocket.send_json({"event": "step", "index": 5, "status": "running"})

                    try:
                        payload = json.loads(result_json)
                    except Exception:
                        payload = result_json

                    await websocket.send_json({
                        "event": "result",
                        "success": True,
                        "filename": filename,
                        "data": payload
                    })
                    await websocket.send_json({"event": "step", "index": 5, "status": "done"})
                    await websocket.send_json({"event": "done", "ok": True})
            except Exception as exc:
                logger.exception("ws_process failed")
                await websocket.send_json({"event": "error", "detail": str(exc)})
                await websocket.send_json({"event": "done", "ok": False})

    except WebSocketDisconnect:
        logger.info("Frontend disconnected: %s", client)
    finally:
        heartbeat_stop.set()
        if heartbeat_task:
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)