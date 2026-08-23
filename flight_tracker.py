import os
import requests

ORIGIN = "LTN"
DESTINATION = "POZ"
YEAR_MONTH = "2026-12"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")

def get_flight_prices():
    url = "https://booking-com15.p.rapidapi.com/api/v1/flights/getMinPrice"
    
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "booking-com15.p.rapidapi.com"
    }
    
    params = {
        "fromId": f"{ORIGIN}.AIRPORT",
        "toId": f"{DESTINATION}.AIRPORT",
        "departDate": f"{YEAR_MONTH}-01",
        "currency_code": "GBP"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        data = response.json()
        if response.status_code == 200 and data.get("status"):
            return data.get("data", {})
        return None
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
    prices_data = get_flight_prices()
    
    if prices_data:
        msg = f"✈️ **Ceny lotów: {ORIGIN} ➔ {DESTINATION}**\n🗓️ **Grudzień 2026**\n\n"
        
        for day, info in prices_data.items():
            price = info.get("price")
            if price:
                msg += f"• `{day}`: **{price} GBP**\n"
                
        send_telegram(msg)
    else:
        send_telegram("⚠️ Wystąpił problem z pobraniem danych. Sprawdź logi w GitHub Actions.")

if __name__ == "__main__":
    main()
