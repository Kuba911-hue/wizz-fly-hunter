import os
import requests

ORIGIN = "LTN"
DESTINATION = "POZ"
YEAR_MONTH = "2026-12"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")

def get_skyscanner_prices():
    url = "https://skyscanner44.p.rapidapi.com/search-extended"
    
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "skyscanner44.p.rapidapi.com"
    }
    
    params = {
        "adults": "1",
        "origin": ORIGIN,
        "destination": DESTINATION,
        "departureDate": YEAR_MONTH,
        "currency": "GBP",
        "locale": "en-GB"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        return response.json()
    except Exception as e:
        print(f"Błąd API: {e}")
        return None

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def main():
    data = get_skyscanner_prices()
    
    if data and "itineraries" in str(data):
        msg = f"✈️ **Ceny Skyscanner: LTN ➔ POZ**\n🗓️ **Grudzień 2026**\n\n"
        
        # Wyciąganie i formatowanie cen z odpowiedzi JSON
        # (struktura zależy od konkretnego API na RapidAPI)
        msg += "Znaleziono aktualne oferty na ten miesiąc!"
        send_telegram(msg)
    else:
        send_telegram("⚠️ Nie udało się pobrać danych z Skyscanner API.")

if __name__ == "__main__":
    main()
