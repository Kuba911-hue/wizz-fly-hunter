import os
import requests
from serpapi import GoogleSearch

ORIGIN = "LTN"
DESTINATION = "POZ"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
SERP_KEY = os.environ.get("SERPAPI_KEY")

def get_google_flights():
    if not SERP_KEY:
        return "⚠️ Błąd: Brak klucza SERPAPI_KEY."

    # Pobieramy najniższe ceny lotów na grudzień 2026
    params = {
        "engine": "google_flights",
        "departure_id": ORIGIN,
        "arrival_id": DESTINATION,
        "outbound_date": "2026-12-18",
        "currency": "GBP",
        "hl": "pl",
        "type": "2",
        "api_key": SERP_KEY
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        
        flights = results.get("best_flights", []) + results.get("other_flights", [])
        
        if not flights:
            return "Brak znalezionych lotów w Google Flights."

        msg = f"✈️ **Ceny lotów LTN ➔ POZ (Google Flights)**\n🗓️ **Grudzień 2026**\n\n"
        
        for flight in flights[:10]:
            price = flight.get("price", "N/A")
            flight_details = flight.get("flights", [{}])[0]
            airline = flight_details.get("airline", "Linia lotnicza")
            dep_time = flight_details.get("departure_airport", {}).get("time", "")
            
            msg += f"📅 `{dep_time}` | **{airline}** | Cena: **£{price}**\n"

        return msg

    except Exception as e:
        return f"⚠️ Błąd SerpApi: {e}"

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def main():
    report = get_google_flights()
    send_telegram(report)

if __name__ == "__main__":
    main()
