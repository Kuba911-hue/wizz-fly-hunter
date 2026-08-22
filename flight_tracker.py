import os
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

ORIGIN = "LTN"      # Londyn Luton
DESTINATION = "POZ" # Poznań
YEAR = 2026
MONTH = 12

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def fetch_prices_with_playwright():
    flights = []
    
    with sync_playwright() as p:
        # Uruchamiamy przeglądarkę Chromium
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        try:
            # Wejście bezpośrednio na stronę fare-finder WizzAir dla zadanej trasy i miesiąca
            url = f"https://wizzair.com/pl-pl/flights/fare-finder/{ORIGIN}/{DESTINATION}/{YEAR}-{MONTH:02d}-01"
            page.goto(url, wait_until="networkidle", timeout=60000)

            # Zamknięcie okna z ciasteczkami jeśli się pojawi
            try:
                page.click("#onetrust-accept-btn-handler", timeout=5000)
            except Exception:
                pass

            # Czekamy na wyrenderowanie kafelków z cenami w kalendarzu
            page.wait_for_selector(".fare-finder__calendar__day", timeout=15000)

            days = page.query_selector_all(".fare-finder__calendar__day")

            for day in days:
                date_attr = day.get_attribute("data-date") # np. 2026-12-15
                price_elem = day.query_selector(".fare-finder__calendar__price")
                
                if date_attr and price_elem:
                    price_text = price_elem.inner_text().strip()
                    # Czyszczenie tekstu z waluty (np. "£45.99" lub "45.99 GBP")
                    price_clean = "".join(c for c in price_text if c.isdigit() or c in ['.', ',']).replace(',', '.')
                    
                    if price_clean:
                        dt = datetime.strptime(date_attr, "%Y-%m-%d")
                        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                        
                        flights.append({
                            "date": dt.strftime("%d.%m.%Y"),
                            "day_name": day_names[dt.weekday()],
                            "price": float(price_clean)
                        })

        except Exception as e:
            print(f"Błąd Playwright: {e}")
        finally:
            browser.close()
            
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
    flights = fetch_prices_with_playwright()
    
    if not flights:
        msg = f"📊 **[WizzAir] LTN ➔ POZ (Grudzień {YEAR})**\n\n⚠️ Nie udało się odczytać kalendarza cen ze strony."
        send_telegram_message(msg)
        return

    msg = f"📊 **[WizzAir] Londyn Luton (LTN) ➔ Poznań (POZ)**\n"
    msg += f"🗓️ **Grudzień {YEAR}**\n\n"
    
    for f in flights:
        msg += f"📅 `{f['date']}` ({f['day_name']}): **{f['price']:.2f} GBP**\n"

    cheapest = min(flights, key=lambda x: x['price'])
    msg += f"\n💡 **Najtańszy lot:** `{cheapest['date']}` za **{cheapest['price']:.2f} GBP**!"

    send_telegram_message(msg)

if __name__ == "__main__":
    main()
