import os
import requests
from datetime import datetime

ORIGIN = "LTN"        # London Luton
DESTINATION = "POZ"   # Poznań
YEAR = 2026
MONTH = 12

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def get_monthly_prices():
    # Pobieramy cały zakres dat dla wskazanego miesiąca
    date_from = f"01/{MONTH:02d}/{YEAR}"
    date_to = f"31/{MONTH:02d}/{YEAR}"

    url = "https://api.skypicker.com/flights"
    params = {
        "fly_from": ORIGIN,
        "fly_to": DESTINATION,
        "date_from": date_from,
        "date_to": date_to,
        "curr": "GBP",
        "partner": "picky",
        "direct_flights": 1,
        "one_per_date": 1,  # Wyciąga dokładnie 1 najtańszy lot z każdego dnia
        "sort": "date"
    }

    try:
        response = requests.get(url, params=params, timeout=20)
        data = response.json()
        return data.get("data", [])
    except Exception as e:
        print(f"Błąd Kiwi API: {e}")
        return None

def send_telegram_message(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Brak tokenu Telegram!")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

def main():
    flights = get_monthly_prices()

    if flights:
        msg = f"✈️ **Ceny lotów: {ORIGIN} ➔ {DESTINATION}**\n🗓️ **Grudzień {YEAR} (Kiwi.com)**\n\n"
        
        for flight in flights:
            # Formatowanie daty z timestampu UNIX
            date_str = datetime.fromtimestamp(flight["dTime"]).strftime("%d.%m (%a)")
            price = flight["price"]
            airline = flight["airlines"][0] if flight.get("airlines") else "Flight"
            
            msg += f"• `{date_str}` ➔ **{price} GBP** ({airline})\n"

        send_telegram_message(msg)
    else:
        send_telegram_message("⚠️ Nie udało się pobrać danych o cenach z Kiwi.com.")

if __name__ == "__main__":
    main()
