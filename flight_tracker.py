import os
import requests
from playwright.sync_api import sync_playwright

ORIGIN = "london-luton"
DESTINATION = "poznan"
YEAR = 2026
MONTH = 12

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def capture_screenshot():
    screenshot_path = "calendar.png"
    
    with sync_playwright() as p:
        # Uruchomienie przeglądarki z ekranem full-HD
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            url = f"https://www.wizzair.com/en-gb/flights/fare-finder/{ORIGIN}/{DESTINATION}/0/0/0/1/0/0/{YEAR}-{MONTH:02d}-01/{YEAR}-{MONTH:02d}-01?flexible=anytime&duration=1_week"
            page.goto(url, wait_until="networkidle", timeout=60000)

            # Próba zamknięcia baneru ciasteczek
            try:
                page.click("#onetrust-accept-btn-handler", timeout=5000)
            except Exception:
                pass

            # Odczekanie na pełne załadowanie elementów kalendarza
            page.wait_for_timeout(5000)
            
            # Zrzut całej strony
            page.screenshot(path=screenshot_path, full_page=True)
            return screenshot_path

        except Exception as e:
            print(f"Błąd Playwright: {e}")
            return None
        finally:
            browser.close()

def send_telegram_photo(photo_path, caption):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Brak tokenu Telegram!")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open(photo_path, "rb") as photo:
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "caption": caption,
            "parse_mode": "Markdown"
        }
        files = {"photo": photo}
        requests.post(url, data=payload, files=files)

def main():
    photo = capture_screenshot()
    
    if photo and os.path.exists(photo):
        caption = f"📸 **WizzAir Fare Finder: LTN ➔ POZ**\n🗓️ **Grudzień {YEAR}**"
        send_telegram_photo(photo, caption)
        os.remove(photo)
    else:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": "⚠️ Nie udało się wygenerować zrzutu ekranu kalendarza."
        }
        requests.post(url, json=payload)

if __name__ == "__main__":
    main()
