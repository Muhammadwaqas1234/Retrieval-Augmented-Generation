"""Render the design-sheet collage to a single LinkedIn-ready PNG."""
from pathlib import Path
from playwright.sync_api import sync_playwright

SHEET = Path(r"C:\Users\raiwa\Retrieval-Augmented-Generation\docs\design\design-sheet.html")
OUT = r"C:\Users\raiwa\Retrieval-Augmented-Generation\docs\design\design-sheet.png"

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 2200, "height": 1200})
    page = ctx.new_page()
    page.goto(SHEET.as_uri(), wait_until="networkidle")
    page.wait_for_timeout(1500)
    page.screenshot(path=OUT, full_page=True)
    print("captured design-sheet.png")
    browser.close()
