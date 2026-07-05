"""Full-page design captures of the public pages (designer-style)."""
from playwright.sync_api import sync_playwright

OUT = r"C:\Users\raiwa\Retrieval-Augmented-Generation\docs\design"
BASE = "http://127.0.0.1:5000"

PAGES = [
    ("/", "01-landing.png"),
    ("/register", "02-register.png"),
    ("/login", "03-login.png"),
    ("/support", "10-support.png"),
    ("/condition", "11-terms-conditions.png"),
    ("/privacy", "12-privacy.png"),
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1600, "height": 1000}, device_scale_factor=2)
    page = ctx.new_page()
    for url, name in PAGES:
        page.goto(BASE + url, wait_until="networkidle")
        page.wait_for_timeout(700)
        page.screenshot(path=f"{OUT}\\{name}", full_page=True)
        print("captured", name)
    browser.close()
