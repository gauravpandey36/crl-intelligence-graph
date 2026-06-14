#!/usr/bin/env python3
"""Minimal, dependency-free Anthropic completion helper for the companion guide.

Pure standard library (urllib) so the portal runs with zero `pip install`.
The API key is read from the ANTHROPIC_API_KEY environment variable ONLY and is
never logged or placed into a prompt. Bring your own key:

    export ANTHROPIC_API_KEY=sk-ant-...

Raises on any failure so the caller (guide.py) keeps its own graceful fallback.
Public FDA data tool. Educational, not regulatory advice.
"""
from __future__ import annotations

import json
import os
import urllib.request

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


def complete(system: str, prompt: str, *, model: str, num_predict: int = 500,
             temperature: float = 0.3, timeout: int = 60) -> str:
    """Return Claude's text completion for (system, prompt). Raises on error."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set (the companion needs your own key)")
    body = json.dumps({
        "model": model,
        "max_tokens": max(64, int(num_predict)),
        "system": system,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "content-type": "application/json",
        "anthropic-version": API_VERSION,
        "x-api-key": key,  # value never logged
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    parts = data.get("content") or []
    return "".join(p.get("text", "") for p in parts if p.get("type") == "text").strip()
