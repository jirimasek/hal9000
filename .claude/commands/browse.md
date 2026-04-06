Use Playwright (installed in the venv at `$HAL_HOME/venv/bin/python3`) to interact with a headless Chromium browser.

## Taking a screenshot

Save screenshots to the dated workspace directory: `$HAL_HOME/workspace/YYYY-MM-DD/`.

```python
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

async def screenshot(url: str):
    workspace = Path(os.environ["HAL_HOME"]) / "workspace" / datetime.now().strftime("%Y-%m-%d")
    workspace.mkdir(parents=True, exist_ok=True)
    path = str(workspace / "screenshot.png")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        await page.goto(url, timeout=30000, wait_until="networkidle")
        await page.screenshot(path=path, full_page=False)
        await browser.close()

    return path

path = asyncio.run(screenshot(sys.argv[1]))
print(f"[SEND_IMAGE:{path}]")
```

Run via: `$HAL_HOME/venv/bin/python3 script.py "https://url-to-screenshot.com"`

After printing the marker, the Telegram bridge will send the image to the user and delete the file.

## Reading page content

Use `page.inner_text("body")` or `page.content()` to extract text or HTML for further analysis.

## Notes

- Always close the browser after use
- `$HAL_HOME` is available as an environment variable
- For pages requiring interaction (login, scroll, click), use Playwright's full API
