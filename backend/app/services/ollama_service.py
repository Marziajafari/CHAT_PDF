"""Thin client for the local Ollama server (no cloud, no API keys)."""
from typing import Dict, List, Optional

import httpx

from app.core.config import settings
from app.services.errors import OllamaError

_http = httpx.Client()


def chat(
    messages: List[Dict[str, str]],
    json_mode: bool = False,
    temperature: float = 0.2,
    num_predict: Optional[int] = None,
    model: Optional[str] = None,
) -> str:
    """Send a chat request and return the model's reply text."""
    model = model or settings.chat_model
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "keep_alive": settings.ollama_keep_alive,
        "options": {
            "temperature": temperature,
            "num_ctx": settings.ollama_num_ctx,
            "num_predict": num_predict or settings.ollama_num_predict,
        },
    }
    if json_mode:
        payload["format"] = "json"
    try:
        response = _http.post(
            f"{settings.ollama_url}/api/chat",
            json=payload,
            timeout=httpx.Timeout(settings.ollama_timeout, connect=5.0),
        )
    except httpx.ConnectError:
        raise OllamaError(
            "Cannot reach Ollama. Start it with `ollama serve` (or open the Ollama app) and try again."
        ) from None
    except httpx.TimeoutException:
        raise OllamaError(
            "The local model took too long to answer. Try a shorter question or close other programs to free RAM."
        ) from None
    except httpx.HTTPError:
        raise OllamaError("Communication with Ollama failed.") from None

    if response.status_code == 404:
        raise OllamaError(f"Model '{model}' is not installed. Run: ollama pull {model}")
    if response.status_code >= 400:
        raise OllamaError(f"Ollama returned an error (HTTP {response.status_code}).")
    try:
        return response.json()["message"]["content"].strip()
    except (KeyError, ValueError):
        raise OllamaError("Ollama returned an unexpected response.") from None


def status() -> dict:
    """Is Ollama running, and is the configured model installed?"""
    result = {
        "reachable": False,
        "model": settings.chat_model,
        "model_available": False,
        "installed_models": [],
    }
    try:
        response = _http.get(f"{settings.ollama_url}/api/tags", timeout=2.0)
        response.raise_for_status()
        names = [m.get("name", "") for m in response.json().get("models", [])]
        result["reachable"] = True
        result["installed_models"] = names
        wanted = settings.chat_model
        result["model_available"] = any(
            n == wanted or n.split(":")[0] == wanted or (":" not in wanted and n == f"{wanted}:latest")
            for n in names
        )
    except Exception:
        pass
    return result
