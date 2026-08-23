import os
import requests
from playwright.sync_api import sync_playwright

ORIGIN = "LTN"
DESTINATION = "POZ"
MONTH = "2026-12"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def capture_azair():
    screenshot_path = "azair.png"
    url = f"https://www.azair.eu/azfind.php?src={ORIGIN}&dst={DESTINATION}&depmonth={MONTH}&minnights=1&maxnights=14&direct=1&currency=GBP"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            page.screenshot(path=screenshot_path)
            return screenshot_path
        except Exception as e:
            print(f"Błąd Azair: {e}")
            return None
        finally:
            browser.close()

def send_telegram_photo(photo_path, caption):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open(photo_path, "rb") as photo:
        payload = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "Markdown"}
        requests.post(url, data=payload, files={"photo": photo})

def main():
    photo = capture_azair()
    if photo and os.path.exists(photo):
        send_telegram_photo(photo, f"✈️ **Rozkład & Ceny: LTN ➔ POZ**\n🗓️ **Grudzień 2026 (Azair)**")
        os.remove(photo)
    else:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": "⚠️ Nie udało się pobrać zrzutu ekranu."})

if __name__ == "__main__":
    main()
