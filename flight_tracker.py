import os
import requests
from datetime import datetime

# Konfiguracja tras i dat
ORIGIN = "LTN"      # Londyn Luton
DESTINATION = "POZ" # Poznań
YEAR = 2026         # Grudzień 2026
MONTH = 12

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def get_wizzair_prices(origin, destination, year, month):
    api_url = "https://be.wizzair.com/15.1.0/api/search/timetable"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json"
    }

    payload = {
        "flightList": [
            {
                "departureStation": origin,
                "arrivalStation": destination,
                "from": f"{year}-{month:02d}-01",
                "to": f"{year}-{month:02d}-31"
            }
        ],
        "priceType": "regular"
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            return parse_timetable(data)
        return []
    except Exception as e:
        print(f"Błąd pobierania danych: {e}")
        return []

def parse_timetable(data):
    results = []
    outbound_flights = data.get("outboundFlights", [])
    for flight in outbound_flights:
        date_str = flight.get("departureDate", "")
        price_data = flight.get("price", {})
        amount = price_data.get("amount")
        currency = price_data.get("currencyCode", "GBP")
        
        if amount is not None and date_str:
            dt = datetime.strptime(date_str.split("T")[0], "%Y-%m-%d")
            results.append({
                "date": dt.strftime("%d.%m.%Y"),
                "day_name": dt.strftime("%a"),
                "price": amount,
                "currency": currency
            })
    return results

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Brak danych autoryzacyjnych Telegram!")
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
    flights = get_wizzair_prices(ORIGIN, DESTINATION, YEAR, MONTH)
    
    if not flights:
        msg = f"📊 **[WizzAir] LTN ➔ POZ (Grudzień {YEAR})**\n\n⚠️ Brak dostępnych lotów lub blokada API."
        send_telegram_message(msg)
        return

    msg = f"📊 **[WizzAir] Zestawienie Ceny: Luton (LTN) ➔ Poznań (POZ)**\n\n"
    for f in flights:
        msg += f"📅 `{f['date']}` ({f['day_name']}): **{f['price']} {f['currency']}**\n"

    cheapest = min(flights, key=lambda x: x['price'])
    msg += f"\n💡 **Najtańszy lot:** `{cheapest['date']}` za **{cheapest['price']} {cheapest['currency']}**!"

    send_telegram_message(msg)

if __name__ == "__main__":
    main()