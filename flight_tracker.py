import os
import requests
from playwright.sync_api import sync_playwright

ORIGIN = "london-luton"
DESTINATION = "poznan"
YEAR = 2026
MONTH = 12

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def capture_clean_calendar():
    screenshot_path = "calendar_clean.png"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Ustawienie okna na rozdzielczość, w której kalendarz wypełnia cały ekran
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            url = f"https://www.wizzair.com/en-gb/flights/fare-finder/{ORIGIN}/{DESTINATION}/0/0/0/1/0/0/{YEAR}-{MONTH:02d}-01/{YEAR}-{MONTH:02d}-01?flexible=anytime&duration=1_week"
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)

            # Usuwamy baner cookies oraz nakładkę zaciemniającą tło bezpośrednio z HTML
            page.evaluate("""() => {
                const selectors = [
                    '#onetrust-banner-sdk',
                    '.onetrust-pc-dark-filter',
                    '#onetrust-consent-sdk'
                ];
                selectors.forEach(sel => {
                    const el = document.querySelector(sel);
                    if (el) el.remove();
                });
            }""")

            page.wait_for_timeout(1000)

            # Robimy zrzut widocznego obszaru
            page.screenshot(path=screenshot_path)
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
    photo = capture_clean_calendar()
    
    if photo and os.path.exists(photo):
        caption = f"✈️ **WizzAir Fare Finder: LTN ➔ POZ**\n🗓️ **Grudzień {YEAR}**"
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
