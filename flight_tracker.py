import os
import requests

ORIGIN = "LTN"
DESTINATION = "POZ"
YEAR_MONTH = "2026-12"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def get_wizzair_prices():
    url = "https://be.wizzair.com/24.5.0/api/search/timetable"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json"
    }

    payload = {
        "flightList": [
            {
                "departureStation": ORIGIN,
                "arrivalStation": DESTINATION,
                "from": f"{YEAR_MONTH}-01",
                "to": f"{YEAR_MONTH}-31"
            }
        ],
        "priceType": "regular"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        
        if response.status_code != 200:
            return f"⚠️ Wizz Air API zwróciło status: {response.status_code}"

        data = response.json()
        outbound_flights = data.get("outboundFlights", [])

        if not outbound_flights:
            return "Brak dostępnych lotów bezpośrednich w tym miesiącu."

        msg = f"✈️ **Wizz Air: LTN ➔ POZ**\n🗓️ **Grudzień 2026**\n\n"
        for flight in outbound_flights:
            date = flight.get("departureDate", "").split("T")[0]
            price_obj = flight.get("price", {})
            amount = price_obj.get("amount")
            currency = price_obj.get("currencyCode", "GBP")
            
            if amount is not None:
                msg += f"📅 `{date}`: **{amount:.2f} {currency}**\n"

        return msg

    except Exception as e:
        return f"⚠️ Błąd podczas połączenia z API Wizz Air: {e}"

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def main():
    report = get_wizzair_prices()
    send_telegram(report)

if __name__ == "__main__":
    main()
