"""Listen: short generated sentences read aloud with ElevenLabs (the coach's plan, the game's summary, a coach answer).

Only the sentence on screen is sent: no name, customer id or account number. The audio is cached by a hash of the
text, so each sentence is generated once. ELEVENLABS_API_KEY (and optionally ELEVENLABS_VOICE_ID) live in .env.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import httpx

CACHE = Path(__file__).resolve().parent.parent / "state" / "voice"
MODEL = "eleven_multilingual_v2"     # speaks English, Finnish and Swedish with one voice
DEFAULT_VOICE = "21m00Tcm4TlvDq8ikWAM"  # a stock ElevenLabs voice; override with ELEVENLABS_VOICE_ID
MAX_CHARS = 400


def configured() -> bool:
    return bool(os.environ.get("ELEVENLABS_API_KEY"))


def speak(text: str) -> Path:
    """MP3 of the text, from cache or ElevenLabs."""
    text = " ".join((text or "").split())[:MAX_CHARS]
    if not text:
        raise ValueError("nothing to say")
    voice = os.environ.get("ELEVENLABS_VOICE_ID") or DEFAULT_VOICE
    f = CACHE / (hashlib.sha256(f"{voice}:{MODEL}:{text}".encode()).hexdigest()[:32] + ".mp3")
    if f.exists():
        return f
    r = httpx.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128",
                   headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]}, timeout=60,
                   json={"text": text, "model_id": MODEL})
    r.raise_for_status()
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_bytes(r.content)
    return f
