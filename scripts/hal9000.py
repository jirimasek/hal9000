"""Shared utilities for HAL 9000 scripts."""

import os
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(os.environ["HAL_HOME"])
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ALLOWED_USER_ID = int(os.environ["ALLOWED_USER_ID"])


def make_workspace_dir() -> Path:
    """Return a date-stamped workspace subdirectory, creating it if needed."""
    workspace = BASE_DIR / "workspace" / datetime.now().strftime("%Y-%m-%d")
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


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
