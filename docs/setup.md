# HAL 9000 – Setup Guide

## Directory structure

```
HAL_HOME/                        # Base directory (configured via HAL_HOME env var)
├── conf/
│   ├── config.env               # Applied configuration (gitignored)
│   ├── config.example.env       # Configuration template
│   ├── secrets.env              # Secrets – Telegram token (gitignored)
│   └── secrets.example.env      # Secrets template
├── data/
│   ├── session.json             # Active Claude session state
│   └── tts/
│       └── cs_CZ-jirka-medium.onnx  # Piper TTS voice model
├── docs/                        # Documentation
├── logs/                        # Conversation logs (YYYY-MM-DD/<session_id>.log)
├── scripts/
│   └── telegram_bridge.py       # Main Telegram bridge script
├── venv/                        # Python virtual environment (gitignored)
├── workspace/                   # Temporary files (screenshots, TTS audio)
└── CLAUDE.md                    # HAL 9000 identity and environment configuration
```

## Requirements

- Ubuntu Server 24.04 LTS
- Python 3.12+
- Nginx
- ffmpeg
- A Telegram bot token ([@BotFather](https://t.me/BotFather))

## Installation

### 1. System packages

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg python3-venv python3-pip
```

### 2. Clone the repository

```bash
git clone <repo-url> /home/hal9000
cd /home/hal9000
```

### 3. Python virtual environment

```bash
python3 -m venv venv
venv/bin/pip install python-telegram-bot==22.7 faster-whisper piper-tts playwright
venv/bin/playwright install chromium
```

### 4. TTS voice model

Download the Czech Piper voice model:

```bash
mkdir -p data/tts
curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/cs/cs_CZ/jirka/medium/cs_CZ-jirka-medium.onnx" \
     -o data/tts/cs_CZ-jirka-medium.onnx
curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/cs/cs_CZ/jirka/medium/cs_CZ-jirka-medium.onnx.json" \
     -o data/tts/cs_CZ-jirka-medium.onnx.json
```

### 5. Configuration

```bash
cp conf/secrets.example.env conf/secrets.env
cp conf/config.example.env conf/config.env
```

Edit `conf/secrets.env` and fill in your Telegram bot token:
```
TELEGRAM_TOKEN=your_token_here
```

Edit `conf/config.env` and fill in your Telegram user ID
(find it via [@userinfobot](https://t.me/userinfobot)):
```
ALLOWED_USER_ID=123456789
```

### 6. Runtime directories

```bash
mkdir -p data logs workspace
```

### 7. Systemd service

Create `/etc/systemd/system/hal9000.service`:

```ini
[Unit]
Description=HAL 9000 Telegram Agent
After=network.target

[Service]
User=hal9000
WorkingDirectory=/home/hal9000
ExecStart=/home/hal9000/venv/bin/python3 /home/hal9000/scripts/telegram_bridge.py
Restart=always
RestartSec=10
Environment=PATH=/home/hal9000/.local/bin:/usr/local/bin:/usr/bin:/bin
EnvironmentFile=/home/hal9000/conf/secrets.env
EnvironmentFile=/home/hal9000/conf/config.env

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable hal9000
sudo systemctl start hal9000
```

### 8. Verify

```bash
sudo journalctl -u hal9000 -f
```

You should see `Application started` and receive a startup message in Telegram.
