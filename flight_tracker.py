import os
import requests
from playwright.sync_api import sync_playwright

ORIGIN = "london-luton"
DESTINATION = "poznan"
YEAR = 2026
MONTH = 12

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def capture_wizzair():
    screenshot_path = "wizzair.png"
    url = f"https://www.wizzair.com/en-gb/flights/fare-finder/{ORIGIN}/{DESTINATION}/0/0/0/1/0/0/{YEAR}-{MONTH:02d}-01/{YEAR}-{MONTH:02d}-01?flexible=anytime&duration=1_week"

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            locale="en-GB",
            timezone_id="Europe/London"
        )
        
        page = context.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Czekamy na załadowanie kalendarza
            try:
                page.wait_for_selector(".fare-finder__calendar__price", timeout=20000)
            except Exception:
                page.wait_for_timeout(6000)

            # 1. Spróbujmy kliknąć przycisk "Accept all" lub "Deny all" na banerze OneTrust
            try:
                btn = page.query_selector("#onetrust-accept-btn-handler, #onetrust-reject-all-handler")
                if btn:
                    btn.click()
                    page.wait_for_timeout(1000)
            except Exception:
                pass

            # 2. Usuwamy fizycznie z drzewa DOM wszystkie nakładki cookies i ich tła
            page.evaluate("""() => {
                const selectors = [
                    '#onetrust-consent-sdk',
                    '#onetrust-banner-sdk',
                    '.onetrust-pc-dark-filter',
                    'div[id*="onetrust"]',
                    'div[class*="onetrust"]'
                ];
                selectors.forEach(selector => {
                    document.querySelectorAll(selector).forEach(el => el.remove());
                });
                document.body.style.overflow = 'auto';
            }""")

            page.wait_for_timeout(1000)
            page.screenshot(path=screenshot_path)
            return screenshot_path

        except Exception as e:
            print(f"Błąd WizzAir: {e}")
            try:
                page.screenshot(path=screenshot_path)
                return screenshot_path
            except Exception:
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
    photo = capture_wizzair()
    if photo and os.path.exists(photo):
        send_telegram_photo(photo, f"✈️ **WizzAir Fare Finder: LTN ➔ POZ**\n🗓️ **Grudzień {YEAR}**")
        os.remove(photo)
    else:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": "⚠️ Nie udało się pobrać zrzutu ekranu."})

if __name__ == "__main__":
    main()
