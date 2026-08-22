import os
from datetime import datetime
from curl_cffi import requests

ORIGIN = "LTN"      # Londyn Luton
DESTINATION = "POZ" # Poznań
YEAR = 2026
MONTH = 12

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def fetch_live_wizzair_prices():
    api_url = "https://be.wizzair.com/15.1.0/api/search/timetable"
    
    # Używamy impersonate="chrome120" - udaje prawdziwą przeglądarkę na poziomie TLS
    session = requests.Session(impersonate="chrome120")
    
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://wizzair.com",
        "Referer": "https://wizzair.com/pl-pl/flights/fare-finder/LTN/POZ",
        "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    payload = {
        "flightList": [
            {
                "departureStation": ORIGIN,
                "arrivalStation": DESTINATION,
                "from": f"{YEAR}-{MONTH:02d}-01",
                "to": f"{YEAR}-{MONTH:02d}-31"
            }
        ],
        "priceType": "regular"
    }

    try:
        # Najpierw "odwiedzamy" stronę główną, żeby zebrać ciasteczka sesyjne
        session.get("https://wizzair.com/pl-pl", headers=headers, timeout=15)
        
        # Właściwy strzał po ceny
        response = session.post(api_url, json=payload, headers=headers, timeout=20)
        
        if response.status_code == 200:
            return parse_wizz_response(response.json())
        else:
            print(f"Status Błędu: {response.status_code}")
            return []
    except Exception as e:
        print(f"Wyjątek: {e}")
        return []

def parse_wizz_response(data):
    results = []
    outbound = data.get("outboundFlights", [])
    
    for flight in outbound:
        date_str = flight.get("departureDate", "")
        price_info = flight.get("price", {})
        amount = price_info.get("amount")
        currency = price_info.get("currencyCode", "GBP")
        
        if amount is not None and date_str:
            dt = datetime.strptime(date_str.split("T")[0], "%Y-%m-%d")
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            day_name = days[dt.weekday()]
            
            results.append({
                "date": dt.strftime("%d.%m.%Y"),
                "day_name": day_name,
                "price": float(amount),
                "currency": currency
            })
            
    results.sort(key=lambda x: datetime.strptime(x["date"], "%d.%m.%Y"))
    return results

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
    # Używamy zwykłego zapytania do Telegrama
    requests.post(url, json=payload)

def main():
    flights = fetch_live_wizzair_prices()
    
    if not flights:
        msg = f"📊 **[WizzAir] LTN ➔ POZ (Grudzień {YEAR})**\n\n⚠️ Nie udało się pobrać cen na żywo (WizzAir zblokował połączenie)."
        send_telegram_message(msg)
        return

    msg = f"📊 **[WizzAir] Londyn Luton (LTN) ➔ Poznań (POZ)**\n"
    msg += f"🗓️ **Grudzień {YEAR}**\n\n"
    
    for f in flights:
        msg += f"📅 `{f['date']}` ({f['day_name']}): **{f['price']:.2f} {f['currency']}**\n"

    cheapest = min(flights, key=lambda x: x['price'])
    msg += f"\n💡 **Najtańszy lot:** `{cheapest['date']}` za **{cheapest['price']:.2f} {cheapest['currency']}**!"

    send_telegram_message(msg)

if __name__ == "__main__":
    main()
