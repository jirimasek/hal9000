"""Shared utilities for HAL 9000 scripts."""

import os
import re
import subprocess
import tempfile
import wave
import numpy as np
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(os.environ["HAL_HOME"])
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ALLOWED_USER_ID = int(os.environ["ALLOWED_USER_ID"])
TTS_MODEL_PATH = BASE_DIR / "data" / "tts" / "cs_CZ-jirka-medium.onnx"

_piper_voice = None


def get_piper_voice():
    """Return the Piper TTS voice, loading it on first call."""
    global _piper_voice
    if _piper_voice is None:
        from piper.voice import PiperVoice
        _piper_voice = PiperVoice.load(TTS_MODEL_PATH)
    return _piper_voice


def make_workspace_dir() -> Path:
    """Return a date-stamped workspace subdirectory, creating it if needed."""
    workspace = BASE_DIR / "workspace" / datetime.now().strftime("%Y-%m-%d")
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def text_to_ogg(text: str) -> str:
    """Synthesize text to an OGG Opus file using Piper TTS. Returns path to temp file."""
    voice = get_piper_voice()
    text = strip_markdown(text)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir=make_workspace_dir()) as f:
        wav_path = f.name

    with wave.open(wav_path, "wb") as wav_out:
        # Piper 1.4+ returns an AudioChunk iterable; WAV headers must be set
        # by the caller and frames written manually per chunk.
        wav_out.setnchannels(1)
        wav_out.setsampwidth(2)  # 16-bit PCM
        wav_out.setframerate(voice.config.sample_rate)
        for chunk in voice.synthesize(text):
            wav_out.writeframes((chunk.audio_float_array * 32767).astype(np.int16).tobytes())

    ogg_path = wav_path.replace(".wav", ".ogg")
    subprocess.run(
        ["ffmpeg", "-y", "-i", wav_path, "-c:a", "libopus", ogg_path],
        check=True, capture_output=True
    )
    os.unlink(wav_path)
    return ogg_path


def strip_markdown(text: str) -> str:
    """Remove Markdown syntax for plain-text TTS input."""
    text = re.sub(r'```[\w]*\n?.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`[^`]+`', '', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'(?<![_\w])_(.+?)_(?![_\w])', r'\1', text)
    text = re.sub(r'#+\s', '', text)
    text = re.sub(r'\n{2,}', ' ', text)
    return text.strip()


def md_to_html(text: str) -> str:
    """Convert standard Markdown to Telegram HTML."""
    # Protect code blocks from further processing
    code_blocks: list[str] = []
    def save_code_block(m: re.Match) -> str:
        code_blocks.append(m.group(1))
        return f"\x00CB{len(code_blocks)-1}\x00"
    text = re.sub(r'```(?:\w*\n?)(.*?)```', save_code_block, text, flags=re.DOTALL)

    # Protect inline code
    inline_codes: list[str] = []
    def save_inline(m: re.Match) -> str:
        inline_codes.append(m.group(1))
        return f"\x00IC{len(inline_codes)-1}\x00"
    text = re.sub(r'`([^`\n]+)`', save_inline, text)

    # Escape HTML in remaining text
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Bold and italic
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text, flags=re.DOTALL)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'(?<![_\w])_(.+?)_(?![_\w])', r'<i>\1</i>', text)

    # Restore inline code
    for i, code in enumerate(inline_codes):
        esc = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        text = text.replace(f"\x00IC{i}\x00", f"<code>{esc}</code>")

    # Restore code blocks
    for i, code in enumerate(code_blocks):
        esc = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        text = text.replace(f"\x00CB{i}\x00", f"<pre><code>{esc.strip()}</code></pre>")

    return text
