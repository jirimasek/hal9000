#!/usr/bin/env python3
"""Send a message to the owner via Telegram.

Usage:
    notify.py text "Your message here"
    notify.py voice "Text to synthesize and send as voice"
    notify.py image /path/to/image.png ["Optional caption"]
"""

import os
import sys
import asyncio
from telegram import Bot
from hal9000 import TELEGRAM_TOKEN, ALLOWED_USER_ID, text_to_ogg, md_to_html


async def send(mode: str, content: str, caption: str | None = None):
    async with Bot(token=TELEGRAM_TOKEN) as bot:
        if mode == "text":
            await bot.send_message(chat_id=ALLOWED_USER_ID, text=md_to_html(content), parse_mode="HTML")

        elif mode == "voice":
            ogg_path = text_to_ogg(content)
            with open(ogg_path, "rb") as audio:
                await bot.send_voice(chat_id=ALLOWED_USER_ID, voice=audio)
            os.unlink(ogg_path)

        elif mode == "image":
            with open(content, "rb") as img:
                await bot.send_photo(chat_id=ALLOWED_USER_ID, photo=img, caption=caption)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    mode = sys.argv[1]
    content = sys.argv[2]
    caption = sys.argv[3] if len(sys.argv) > 3 else None

    if mode not in ("text", "voice", "image"):
        print(f"Unknown mode: {mode}. Use text, voice, or image.")
        sys.exit(1)

    asyncio.run(send(mode, content, caption))


if __name__ == "__main__":
    main()
