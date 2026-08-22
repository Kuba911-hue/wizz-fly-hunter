import os
import requests
from datetime import datetime, timedelta
from serpapi import GoogleSearch

ORIGIN = "LTN"
DESTINATION = "POZ"
YEAR = 2026
MONTH = 12

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")

def fetch_wizzair_prices():
    if not SERPAPI_KEY:
        print("Brak klucza SERPAPI_KEY!")
        return []

    results_list = []
    
    # Generujemy zapytanie do Google Flights dla całego miesiąca
    # Google Flights pobiera aktywne ceny bezpośrednio z Wizz Air
    params = {
        "engine": "google_flights",
        "departure_id": ORIGIN,
        "arrival_id": DESTINATION,
        "outbound_date": f"{YEAR}-{MONTH:02d}-01",
        "currency": "GBP",
        "hl": "pl",
        "api_key": SERPAPI_KEY,
        "type": "2" # 2 = One-way (lot w jedną stronę)
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        
        # Pobieramy najtańsze loty z wykresu/kalendarza Google Flights
        price_graph = results.get("price_insights", {}).get("price_history", [])
        
        # Przeglądamy propozycje lotów
        best_flights = results.get("best_flights", []) + results.get("other_flights", [])
        
        for flight in best_flights:
            # Sprawdzamy, czy lot obsługuje Wizz Air
            airlines = [leg.get("airline") for leg in flight.get("flights", [])]
            if any("Wizz Air" in airline for airline in airlines if airline):
                flight_date_str = flight.get("flights", [])[0].get("departure_token", "")
                price = flight.get("price")
                
                # Odczytujemy datę odlotu
                departure_time = flight.get("flights", [])[0].get("departure_time", "")
                if departure_time:
                    date_part = departure_time.split(" ")[0] # YYYY-MM-DD
                    dt = datetime.strptime(date_part, "%Y-%m-%d")
                    
                    results_list.append({
                        "date": dt.strftime("%d.%m.%Y"),
                        "day_name": dt.strftime("%a"),
                        "price": float(price)
                    })

        # Usuwamy dublety z tej samej daty i zachowujemy najniższą cenę
        unique_results = {}
        for r in results_list:
            d = r["date"]
            if d not in unique_results or r["price"] < unique_results[d]["price"]:
                unique_results[d] = r

        sorted_list = sorted(unique_results.values(), key=lambda x: datetime.strptime(x["date"], "%d.%m.%Y"))
        return sorted_list

    except Exception as e:
        print(f"Błąd SerpApi: {e}")
        return []

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
    flights = fetch_wizzair_prices()
    
    if not flights:
        msg = f"📊 **[WizzAir] LTN ➔ POZ (Grudzień {YEAR})**\n\n⚠️ Nie udało się pobrać danych z SerpApi (sprawdź klucz API lub dostępność lotów)."
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
