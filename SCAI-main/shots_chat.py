"""Chat workspace captures with a staged, realistic conversation."""
from playwright.sync_api import sync_playwright

OUT = r"C:\Users\raiwa\Retrieval-Augmented-Generation\docs\design"
BASE = "http://127.0.0.1:5000"

DEMO = """
const box = document.getElementById('chat-messages');
box.innerHTML = `
  <div id="user-message" class="chat-message">What is the minimum concrete cover for reinforcement in a coastal environment?</div>
  <div id="response-message" class="chat-message">Based on the indexed standard, reinforced concrete permanently exposed to a marine environment requires a minimum cover of <b>65 mm (2.5 in)</b> for cast-in-place members. For precast elements manufactured under plant-controlled conditions, this may be reduced to 50 mm. The document further recommends sulfate-resistant cement and a maximum water-cement ratio of 0.40 for members in the tidal and splash zones.</div>
  <div id="additional-question" class="chat-message">How do cover requirements change for post-tensioned members?</div>
  <div id="additional-question" class="chat-message">What curing duration applies in marine exposure?</div>
  <div id="additional-question" class="chat-message">Which cement types best resist chloride attack?</div>
  <div id="user-message" class="chat-message">What curing duration applies in marine exposure?</div>
  <div id="response-message" class="chat-message">The standard specifies a minimum <b>7-day continuous moist curing</b> period for concrete in marine exposure classes, extended to 10 days when supplementary cementitious materials such as fly ash or slag exceed 30% of the binder. Formwork left in place may count toward curing provided exposed surfaces are kept wet.</div>
`;
const cc = document.querySelector('.chat-container');
if (cc) cc.scrollTop = cc.scrollHeight;
"""

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1600, "height": 1000}, device_scale_factor=2)
    page = ctx.new_page()

    # 04 — conversation view
    page.goto(BASE + "/", wait_until="networkidle")
    page.wait_for_timeout(600)
    page.evaluate(DEMO)
    page.wait_for_timeout(400)
    page.screenshot(path=f"{OUT}\\04-chat-workspace.png", full_page=True)
    print("captured 04-chat-workspace.png")

    # 04b — same conversation with the sidebar open
    page.click("#open-sidebar-btn")
    page.wait_for_timeout(600)
    page.screenshot(path=f"{OUT}\\04b-chat-sidebar-open.png", full_page=True)
    print("captured 04b-chat-sidebar-open.png")

    # 05 — upload modal over the conversation
    page.evaluate("document.getElementById('uploadModal').style.display='block'")
    page.wait_for_timeout(400)
    page.screenshot(path=f"{OUT}\\05-upload-modal.png", full_page=True)
    print("captured 05-upload-modal.png")

    browser.close()
