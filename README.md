# HAL 9000

Personal AI assistant running on a VPS, accessible via Telegram. Built on [Claude Code](https://claude.ai/code) CLI, with a Telegram bridge that supports text and voice communication.

## Features

- **Text messaging** – send messages to Claude directly via Telegram
- **Voice input** – voice messages are transcribed using [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- **Voice output** – responses are synthesized using [Piper TTS](https://github.com/rhasspy/piper) with a Czech voice model
- **Conversation continuity** – sessions persist across messages via Claude's `--resume` flag
- **Confirmation flow** – destructive actions require explicit approval via inline buttons
- **Screenshots** – `/screenshot <url>` captures a webpage and sends it as an image

## Stack

| Component | Detail |
|---|---|
| AI | Claude Code CLI (`claude`) |
| Telegram bridge | python-telegram-bot 22.7 |
| Speech-to-text | faster-whisper (Whisper `small`, Czech) |
| Text-to-speech | Piper TTS (`cs_CZ-jirka-medium`) |
| Browser automation | Playwright (Chromium) |

## Setup

See [docs/setup.md](docs/setup.md) for installation and configuration instructions.

## Identity

HAL 9000 communicates in Czech, in the style of the Czech dubbing of *2001: A Space Odyssey*.
