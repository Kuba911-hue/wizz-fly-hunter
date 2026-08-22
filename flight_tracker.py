import os
import re
import requests
from datetime import datetime
from PIL import Image
import pytesseract
from playwright.sync_api import sync_playwright

ORIGIN = "london-luton"
DESTINATION = "poznan"
YEAR = 2026
MONTH = 12

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def process_image_ocr(image_path, bbox):
    """Wyciąga tekst z wyciętego fragmentu zrzutu ekranu."""
    img = Image.open(image_path)
    cropped = img.crop(bbox) # (left, top, right, bottom)
    
    # Przetwarzanie OCR skonfigurowane do czytania cyfr i kropek
    text = pytesseract.image_to_string(cropped, config='--psm 6 -c tessedit_char_whitelist=0123456789.GBP£')
    
    # Wyciąganie kwoty za pomocą regex
    match = re.search(r'(\d+[\.,]\d{2})', text)
    if match:
        val = match.group(1).replace(',', '.')
        return float(val)
    return None

def fetch_prices_via_ocr():
    flights = []
    screenshot_path = "page.png"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Ustawiamy rozdzielczość tak, by kalendarz mieścił się bez przewijania
        context = browser.new_context(viewport={"width": 1600, "height": 1000})
        page = context.new_page()

        try:
            url = f"https://www.wizzair.com/en-gb/flights/fare-finder/{ORIGIN}/{DESTINATION}/0/0/0/1/0/0/{YEAR}-{MONTH:02d}-01/{YEAR}-{MONTH:02d}-01?flexible=anytime&duration=1_week"
            page.goto(url, wait_until="networkidle", timeout=60000)

            # Odrzucenie baneru ciasteczek
            try:
                page.click("#onetrust-accept-btn-handler", timeout=5000)
            except Exception:
                pass

            page.wait_for_timeout(3000)
            page.screenshot(path=screenshot_path)

            # Pobieramy współrzędne wszystkich dativek z kalendarza w lewym panelu (Loty z Luton)
            day_elements = page.query_selector_all(".fare-finder__calendar__day")

            for elem in day_elements:
                date_attr = elem.get_attribute("data-date")
                
                # Zbieramy tylko loty wylotowe dla wybranego miesiąca (z lewego panelu)
                if date_attr and date_attr.startswith(f"{YEAR}-{MONTH:02d}"):
                    box = elem.bounding_box()
                    if box and box['x'] < 800: # Filtrujemy lewy panel (LTN -> POZ)
                        # Wyznaczamy marginesy do cięcia samej kwoty na kafelku
                        crop_box = (
                            int(box['x']),
                            int(box['y']),
                            int(box['x'] + box['width']),
                            int(box['y'] + box['height'])
                        )
                        
                        price = process_image_ocr(screenshot_path, crop_box)
                        if price:
                            dt = datetime.strptime(date_attr, "%Y-%m-%d")
                            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                            flights.append({
                                "date": dt.strftime("%d.%m.%Y"),
                                "day_name": day_names[dt.weekday()],
                                "price": price
                            })

        except Exception as e:
            print(f"Błąd Playwright/OCR: {e}")
        finally:
            browser.close()
            if os.path.exists(screenshot_path):
                os.remove(screenshot_path)

    flights.sort(key=lambda x: datetime.strptime(x["date"], "%d.%m.%Y"))
    return flights

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(message)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

def main():
    flights = fetch_prices_via_ocr()
    
    if not flights:
        msg = f"📊 **[WizzAir OCR] LTN ➔ POZ (Grudzień {YEAR})**\n\n⚠️ Nie udało się odczytać cen ze zdjęcia."
        send_telegram_message(msg)
        return

    msg = f"📊 **[WizzAir OCR] Londyn Luton (LTN) ➔ Poznań (POZ)**\n"
    msg += f"🗓️ **Grudzień {YEAR}**\n\n"
    
    for f in flights:
        msg += f"📅 `{f['date']}` ({f['day_name']}): **{f['price']:.2f} GBP**\n"

    cheapest = min(flights, key=lambda x: x['price'])
    msg += f"\n💡 **Najtańszy lot:** `{cheapest['date']}` za **{cheapest['price']:.2f} GBP**!"

    send_telegram_message(msg)

if __name__ == "__main__":
    main()
