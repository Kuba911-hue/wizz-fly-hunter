import os
import requests
import time
from serpapi import GoogleSearch

ORIGIN = "LTN"
DESTINATION = "POZ"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
SERP_KEY = os.environ.get("SERPAPI_KEY")

def get_december_flights():
    if not SERP_KEY:
        return "⚠️ Błąd: Brak klucza SERPAPI_KEY."

    msg = f"✈️ **Ceny lotów LTN ➔ POZ**\n🗓️ **15–24 Grudnia 2026 (Google Flights)**\n\n"
    found_any = False

    # Sprawdzamy dni od 15 do 24 grudnia
    days_to_check = list(range(15, 25))

    for day in days_to_check:
        date_str = f"2026-12-{day:02d}"
        
        params = {
            "engine": "google_flights",
            "departure_id": ORIGIN,
            "arrival_id": DESTINATION,
            "outbound_date": date_str,
            "currency": "GBP",
            "hl": "pl",
            "type": "2",
            "api_key": SERP_KEY
        }

        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            flights = results.get("best_flights", []) + results.get("other_flights", [])
            
            # Szukamy bezpośredniego lotu Wizz Air
            day_flight_found = False
            for flight in flights:
                flight_details = flight.get("flights", [{}])[0]
                airline = flight_details.get("airline", "")
                
                if "Wizz" in airline:
                    price = flight.get("price", "N/A")
                    dep_time = flight_details.get("departure_airport", {}).get("time", "").split(" ")[-1]
                    msg += f"📅 `{date_str}` ({dep_time}): **£{price}**\n"
                    found_any = True
                    day_flight_found = True
                    break
            
            if not day_flight_found:
                msg += f"📅 `{date_str}`: *Brak lotu Wizz Air*\n"

            time.sleep(0.5)

        except Exception as e:
            print(f"Błąd dla daty {date_str}: {e}")

    if not found_any:
        return "Brak bezpośrednich lotów Wizz Air w podanym zakresie dat."

    return msg

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def main():
    report = get_december_flights()
    send_telegram(report)

if __name__ == "__main__":
    main()
