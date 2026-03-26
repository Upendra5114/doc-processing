import json
from typing import Iterator, Optional
from urllib import request, error

from groq import Groq


def stream_completion(
    prompt: str,
    system_message: str,
    api_provider: str,
    api_endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: str = "",
    timeout: int = 120,
) -> Iterator[str]:
    provider = (api_provider or "").strip().lower()
    if provider not in {"groq", "ollama"}:
        raise ValueError("api_provider must be 'groq' or 'ollama'")

    if provider == "groq":
        if not api_key:
            raise ValueError("api_key is required for Groq")
        yield from _stream_groq(
            prompt=prompt,
            system_message=system_message,
            endpoint=api_endpoint,
            api_key=api_key,
            model_name=model_name,
            timeout=timeout,
        )
        return

    if not api_endpoint:
        raise ValueError("api_endpoint is required for Ollama")
    yield from _stream_ollama(
        prompt=prompt,
        system_message=system_message,
        endpoint=api_endpoint,
        model_name=model_name,
        timeout=timeout,
    )


def _stream_groq(
    prompt: str,
    system_message: str,
    endpoint: Optional[str],
    api_key: str,
    model_name: str,
    timeout: int,
) -> Iterator[str]:
    # Let Groq SDK use its default base URL to avoid duplicated /openai/v1 paths.
    if endpoint and endpoint.strip():
        client = Groq(api_key=api_key, base_url=endpoint.strip(), timeout=timeout)
    else:
        client = Groq(api_key=api_key, timeout=timeout)

    stream = client.chat.completions.create(
        model=model_name,
        stream=True,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ],
    )

    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
    return


def _stream_ollama(
    prompt: str,
    system_message: str,
    endpoint: str,
    model_name: str,
    timeout: int,
) -> Iterator[str]:
    payload = {
        "model": model_name,
        "stream": True,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ],
    }

    headers = {"Content-Type": "application/json"}

    for line in _post_json_stream(endpoint, payload, headers, timeout):
        # Ollama /api/chat streams one JSON object per line
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        chunk = obj.get("message", {}).get("content")
        if chunk:
            yield chunk

        if obj.get("done") is True:
            break


def _post_json_stream(
    url: str,
    payload: dict,
    headers: dict,
    timeout: int,
) -> Iterator[str]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url=url, data=data, headers=headers, method="POST")

    try:
        with request.urlopen(req, timeout=timeout) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="ignore").strip()
                if line:
                    yield line
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Connection error: {exc}") from exc


def complete_text_from_stream(
    prompt: str,
    system_message: str,
    api_provider: str,
    api_endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: str = "",
    timeout: int = 120,
) -> str:
    """
    Convenience wrapper that returns the fully collected text.
    For Groq, api_endpoint is optional and defaults to Groq SDK base URL.
    """
    chunks = stream_completion(
        prompt=prompt,
        system_message=system_message,
        api_provider=api_provider,
        api_endpoint=api_endpoint,
        api_key=api_key,
        model_name=model_name,
        timeout=timeout,
    )
    return "".join(chunks)