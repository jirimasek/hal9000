"""Audio synthesis service for HAL 9000.

Supports two backends:
  - ElevenLabs (default): cloud TTS via API, higher quality
  - Piper: local offline TTS model, fallback

Usage:
    from tts import text_to_ogg, TTSBackend
    path = text_to_ogg("Hello", backend=TTSBackend.ELEVENLABS)
    path = text_to_ogg("Hello", backend=TTSBackend.PIPER)
"""

import os
import subprocess
import tempfile
import wave
from enum import Enum
from pathlib import Path

import numpy as np

from hal9000 import BASE_DIR, make_workspace_dir, strip_markdown

PIPER_MODEL_PATH = BASE_DIR / "data" / "tts" / "cs_CZ-jirka-medium.onnx"
ELEVENLABS_VOICE_NAME = os.environ.get("ELEVENLABS_VOICE_NAME", "Flint")
ELEVENLABS_MODEL = "eleven_multilingual_v2"


class TTSBackend(str, Enum):
    ELEVENLABS = "elevenlabs"
    PIPER = "piper"


class TTSService:
    def __init__(self):
        self._piper_voice = None
        self._elevenlabs_client = None
        self._elevenlabs_voice_id: str | None = None

    def text_to_ogg(self, text: str, backend: TTSBackend = TTSBackend.ELEVENLABS) -> str:
        """Synthesize text to an OGG Opus file. Returns path to the temp file."""
        text = strip_markdown(text)
        if backend == TTSBackend.ELEVENLABS:
            audio_bytes = self._synthesize_elevenlabs(text)
            return self._mp3_to_ogg(audio_bytes)
        else:
            return self._synthesize_piper_to_ogg(text)

    # ------------------------------------------------------------------ #
    # ElevenLabs                                                           #
    # ------------------------------------------------------------------ #

    def _get_elevenlabs_client(self):
        if self._elevenlabs_client is None:
            from elevenlabs.client import ElevenLabs
            self._elevenlabs_client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
        return self._elevenlabs_client

    def _get_elevenlabs_voice_id(self) -> str:
        if self._elevenlabs_voice_id is None:
            client = self._get_elevenlabs_client()
            voices = client.voices.get_all()
            match = next(
                (v for v in voices.voices if ELEVENLABS_VOICE_NAME.lower() in v.name.lower()),
                None,
            )
            if match is None:
                raise RuntimeError(
                    f"Hlas '{ELEVENLABS_VOICE_NAME}' nebyl v ElevenLabs nalezen."
                )
            self._elevenlabs_voice_id = match.voice_id
        return self._elevenlabs_voice_id

    def _synthesize_elevenlabs(self, text: str) -> bytes:
        client = self._get_elevenlabs_client()
        voice_id = self._get_elevenlabs_voice_id()
        chunks = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=ELEVENLABS_MODEL,
        )
        return b"".join(chunks)

    def _mp3_to_ogg(self, mp3_bytes: bytes) -> str:
        workspace = make_workspace_dir()
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir=workspace) as f:
            f.write(mp3_bytes)
            mp3_path = f.name
        ogg_path = mp3_path.replace(".mp3", ".ogg")
        subprocess.run(
            ["ffmpeg", "-y", "-i", mp3_path, "-c:a", "libopus", ogg_path],
            check=True, capture_output=True,
        )
        os.unlink(mp3_path)
        return ogg_path

    # ------------------------------------------------------------------ #
    # Piper                                                                #
    # ------------------------------------------------------------------ #

    def _get_piper_voice(self):
        if self._piper_voice is None:
            from piper.voice import PiperVoice
            self._piper_voice = PiperVoice.load(PIPER_MODEL_PATH)
        return self._piper_voice

    def _synthesize_piper_to_ogg(self, text: str) -> str:
        voice = self._get_piper_voice()
        workspace = make_workspace_dir()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir=workspace) as f:
            wav_path = f.name
        with wave.open(wav_path, "wb") as wav_out:
            wav_out.setnchannels(1)
            wav_out.setsampwidth(2)
            wav_out.setframerate(voice.config.sample_rate)
            for chunk in voice.synthesize(text):
                wav_out.writeframes((chunk.audio_float_array * 32767).astype(np.int16).tobytes())
        ogg_path = wav_path.replace(".wav", ".ogg")
        subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path, "-c:a", "libopus", ogg_path],
            check=True, capture_output=True,
        )
        os.unlink(wav_path)
        return ogg_path


_service = TTSService()


def text_to_ogg(text: str, backend: TTSBackend = TTSBackend.ELEVENLABS) -> str:
    """Module-level convenience wrapper around TTSService.text_to_ogg."""
    return _service.text_to_ogg(text, backend)
