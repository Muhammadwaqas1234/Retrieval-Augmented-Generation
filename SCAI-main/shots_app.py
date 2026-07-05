"""Full-page design captures of the authenticated workspace (DEMO_MODE)."""
from playwright.sync_api import sync_playwright

OUT = r"C:\Users\raiwa\Retrieval-Augmented-Generation\docs\design"
BASE = "http://127.0.0.1:5000"

PAGES = [
    ("/", "04-chat-workspace.png"),
    ("/history", "06-history.png"),
    ("/account", "07-account.png"),
    ("/change_password", "08-change-password.png"),
    ("/subscribe", "09-subscribe.png"),
    ("/subscription_success", "13-subscription-success.png"),
    ("/subscription_cancel", "14-subscription-cancel.png"),
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

    # Chat workspace with the sidebar opened (forced state, designer-style)
    page.goto(BASE + "/", wait_until="networkidle")
    page.wait_for_timeout(500)
    try:
        page.click("#open-sidebar-btn", timeout=3000)
        page.wait_for_timeout(600)
        page.screenshot(path=f"{OUT}\\04b-chat-sidebar-open.png", full_page=True)
        print("captured 04b-chat-sidebar-open.png")
    except Exception as e:
        print("sidebar skip:", e)

    # Upload modal state
    try:
        page.evaluate("document.getElementById('uploadModal').style.display='block'")
        page.wait_for_timeout(400)
        page.screenshot(path=f"{OUT}\\05-upload-modal.png", full_page=True)
        print("captured 05-upload-modal.png")
    except Exception as e:
        print("modal skip:", e)

    browser.close()
