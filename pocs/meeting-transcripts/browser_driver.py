import os
import time

from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROME_PROFILE_DIR = os.path.join(BASE_DIR, "chrome_profile")
JS_FILE = os.path.join(BASE_DIR, "meet_audio_capture.js")


def run(meet_url, ws_port, headless=True):
    """Launch Chromium, join a Google Meet, and wait for it to end.

    Args:
        meet_url: Google Meet URL to join.
        ws_port: WebSocket port for the audio capture JS to connect to.
        headless: If False, opens a visible browser (needed for first-run login).
    """
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=CHROME_PROFILE_DIR,
            headless=headless,
            args=[
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                "--auto-select-desktop-capture-source=Google Meet",
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
            ignore_default_args=["--enable-automation"],
            permissions=["microphone", "camera"],
            channel="chromium",
        )

        page = browser.pages[0] if browser.pages else browser.new_page()

        # Inject the WS port and audio capture script before navigation
        page.add_init_script(script=f"window.__GARFIELD_WS_PORT = {ws_port};")
        page.add_init_script(path=JS_FILE)

        print(f"[browser] Navigating to {meet_url}")
        page.goto(meet_url, wait_until="networkidle", timeout=60000)

        # Wait for the pre-join or in-meeting page to load
        time.sleep(5)

        # Turn off mic and camera if buttons are visible
        _try_click(page, '[aria-label*="microphone" i][aria-label*="turn off" i]')
        _try_click(page, '[aria-label*="camera" i][aria-label*="turn off" i]')

        # Click "Join now" or "Ask to join"
        joined = False
        for selector in [
            'button:has-text("Join now")',
            'button:has-text("Ask to join")',
            'button:has-text("Join")',
        ]:
            try:
                btn = page.locator(selector).first
                if btn.is_visible(timeout=3000):
                    btn.click()
                    joined = True
                    print(f"[browser] Clicked: {selector}")
                    break
            except Exception:
                continue

        if not joined:
            print("[browser] Could not find join button - may need manual login")
            if headless:
                print("[browser] Re-run with headless=False for first-time login")
                browser.close()
                return

        print("[browser] In meeting, waiting for it to end...")

        # Monitor for meeting end
        while True:
            try:
                # Check if "You left the meeting" or "Meeting ended" appears
                if page.locator('text="You left the meeting"').count() > 0:
                    print("[browser] Meeting ended: left the meeting")
                    break
                if page.locator('text="The meeting has ended"').count() > 0:
                    print("[browser] Meeting ended")
                    break

                # Check participant count - leave if alone for 30s
                # (This is best-effort; Meet's DOM changes frequently)
            except Exception:
                pass

            time.sleep(5)

        browser.close()
        print("[browser] Browser closed")


def _try_click(page, selector):
    try:
        el = page.locator(selector).first
        if el.is_visible(timeout=2000):
            el.click()
            print(f"[browser] Clicked: {selector}")
    except Exception:
        pass
