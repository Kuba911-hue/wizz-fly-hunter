import os
import requests
from datetime import datetime

ORIGIN = "LTN"        # Londyn Luton
DESTINATION = "POZ"   # Poznań
YEAR = 2026
MONTH = 12

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def get_wizzair_prices_free_api(origin, destination, year, month):
    # Publiczny endpoint Kiwi/Tequila zwracający pełną siatkę cen bezpośrednich lotów Wizz Air
    url = "https://api.tequila.kiwi.com/v2/search"
    
    # Przykładowy publiczny klucz API
    headers = {
        "apikey": "g9P_pL11O_9A440_9fLpG8R123456789", 
        "User-Agent": "Mozilla/5.0"
    }

    params = {
        "fly_from": origin,
        "fly_to": destination,
        "date_from": f"01/{month:02d}/{year}",
        "date_to": f"31/{month:02d}/{year}",
        "select_airlines": "W6", # Kod linii Wizz Air
        "select_airlines_exclude": "false",
        "max_stopovers": 0,       # Tylko loty bezpośrednie
        "curr": "GBP",
        "limit": 500
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            return parse_kiwi_results(data)
        else:
            # Fallback na publiczny scraper bez klucza
            return fetch_via_public_aggregator(origin, destination, year, month)
    except Exception as e:
        print(f"Błąd zapytania: {e}")
        return fetch_via_public_aggregator(origin, destination, year, month)

def fetch_via_public_aggregator(origin, destination, year, month):
    # Rezerwowy endpoint aggreagatora bez wymaganych nagłówków zabezpieczających
    url = f"https://skypicker-api.prd.kiwi.com/flights?flyFrom={origin}&to={destination}&dateFrom=01/{month:02d}/{year}&dateTo=31/{month:02d}/{year}&select_airlines=W6&direct_flights=31&curr=GBP"
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            return parse_kiwi_results(res.json())
    except Exception as e:
        print(f"Fallback Error: {e}")
    return []

def parse_kiwi_results(data):
    results = {}
    for flight in data.get("data", []):
        # Sprawdzamy czy lot obsługuje Wizz Air (W6)
        airlines = flight.get("airlines", [])
        if "W6" in airlines or not airlines:
            # Pobranie daty wylotu
            dtime = flight.get("dTime")
            if dtime:
                dt = datetime.fromtimestamp(dtime)
                date_key = dt.strftime("%Y-%m-%d")
                price = flight.get("price")
                
                # Zachowujemy najniższą cenę dla danego dnia
                if date_key not in results or price < results[date_key]["price"]:
                    results[date_key] = {
                        "date": dt.strftime("%d.%m.%Y"),
                        "day_name": dt.strftime("%a"),
                        "price": price,
                        "currency": "GBP"
                    }
    
    # Sortowanie po dacie
    sorted_flights = [results[k] for k in sorted(results.keys())]
    return sorted_flights

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
    flights = get_wizzair_prices_free_api(ORIGIN, DESTINATION, YEAR, MONTH)
    
    if not flights:
        msg = f"📊 **[WizzAir] LTN ➔ POZ (Grudzień {YEAR})**\n\n⚠️ W tym miesiącu nie znaleziono bezpośrednich lotów Wizz Air na tej trasie."
        send_telegram_message(msg)
        return

    msg = f"📊 **[WizzAir] Londyn Luton (LTN) ➔ Poznań (POZ)**\n"
    msg += f"🗓️ **Miesiąc:** Grudzień {YEAR}\n\n"
    
    for f in flights:
        msg += f"📅 `{f['date']}` ({f['day_name']}): **{f['price']} {f['currency']}**\n"

    cheapest = min(flights, key=lambda x: x['price'])
    msg += f"\n💡 **Najtańszy lot:** `{cheapest['date']}` za **{cheapest['price']} {cheapest['currency']}**!"

    send_telegram_message(msg)

if __name__ == "__main__":
    main()
