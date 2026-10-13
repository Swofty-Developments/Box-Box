"""
Speech for the engineer's lines. Every subfolder registers one provider; TTS_PROVIDER picks which one runs.
Without its key the provider stays silent and the rest of Box-Box runs as normal.
AUDIO_PLAY_COMMAND plays each line on this machine ({file} is the audio path) instead of in the dashboard.
"""
import asyncio
import os
import shlex
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv

from .base import TTS_PROVIDERS, TtsProvider

load_dotenv()
TTS_PROVIDERS.discover(__name__, __path__)

AUDIO_DIR = Path(__file__).resolve().parent.parent / "static" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
CLEANUP_MAX_AGE = int(os.getenv("TTS_CLEANUP_MAX_AGE", "3600"))
# Long lines take longer to synthesise and to play
MAX_CHARS = 180

provider: TtsProvider = TTS_PROVIDERS.get(os.getenv("TTS_PROVIDER", "elevenlabs").strip().lower())()

PLAY_COMMAND = os.getenv("AUDIO_PLAY_COMMAND", "").strip()
_play_argv = shlex.split(PLAY_COMMAND, posix=os.name != "nt") if PLAY_COMMAND else []
_play_lock = asyncio.Lock()


def describe() -> str:
    reason = provider.missing()
    where = f", played with {_play_argv[0]}" if _play_argv else ", played in the dashboard"
    return f"{provider.describe()}" + (f" (off: {reason})" if reason else where)


def plays_locally() -> bool:
    return bool(_play_argv)


async def play(url: str):
    """Play one line on this machine, after any line already playing."""
    path = str(AUDIO_DIR / url.rsplit("/", 1)[-1])
    async with _play_lock:
        try:
            proc = await asyncio.create_subprocess_exec(
                *[arg.replace("{file}", path) for arg in _play_argv],
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
        except Exception as e:
            print(f"Audio playback failed: {e}")


def cleanup_old_audio():
    now = time.time()
    for f in AUDIO_DIR.iterdir():
        if f.is_file() and (now - f.stat().st_mtime) > CLEANUP_MAX_AGE:
            f.unlink(missing_ok=True)


async def synthesize(text: str) -> str | None:
    """Speak one line; returns the URL the dashboard plays, or None."""
    text = (text or "").strip()
    if not text or provider.missing():
        return None
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS - 3].rsplit(" ", 1)[0] + "…"
    try:
        audio = await provider.audio(text)
    except Exception as e:
        print(f"{provider.label} speech failed: {e}")
        return None
    name = f"{uuid.uuid4().hex}.{provider.extension}"
    (AUDIO_DIR / name).write_bytes(audio)
    cleanup_old_audio()
    return f"/audio/{name}"
