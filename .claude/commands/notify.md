Send a proactive message to Jiří via Telegram using `$HAL_HOME/scripts/notify.py`.

## Usage

```bash
# Load environment (required in non-interactive shells)
set -a && source $HAL_HOME/conf/config.env && source $HAL_HOME/conf/secrets.env && set +a

# Send a text message
$HAL_HOME/venv/bin/python3 $HAL_HOME/scripts/notify.py text "Your message here"

# Send a voice message (text will be synthesized via Piper TTS)
$HAL_HOME/venv/bin/python3 $HAL_HOME/scripts/notify.py voice "Text to synthesize"

# Send an image with optional caption
$HAL_HOME/venv/bin/python3 $HAL_HOME/scripts/notify.py image /path/to/image.png "Optional caption"
```

## Notes

- Use `text` for standard responses
- Use `voice` when Jiří explicitly requests a voice message
- Use `image` after saving a file to `$HAL_HOME/workspace/YYYY-MM-DD/`
- Markdown in `text` messages is automatically converted to Telegram HTML
- Markdown in `voice` messages is automatically stripped before synthesis
