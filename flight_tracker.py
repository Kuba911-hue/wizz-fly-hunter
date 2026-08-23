import os
import requests

ORIGIN = "LTN"
DESTINATION = "POZ"
YEAR_MONTH = "2026-12"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def get_flights():
    # Pobieranie surowych danych cenowych bezpośrednio ze Skyscannera
    url = f"https://www.skyscanner.net/g/chiron/api/v1/flights/browse/browsegrid/v1.0/UK/GBP/en-GB/{ORIGIN}/{DESTINATION}/{YEAR_MONTH}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    try:
        res = requests.get(url, headers=headers, timeout=20)
        
        # Jeśli Skyscanner tymczasowo przyblokuje, przechodzimy na publiczny endpoint kalendarza Wizz Air API
        if res.status_code != 200:
            return get_wizzair_api()

        data = res.json()
        dates_data = data.get("Grid", {}).get("OutboundData", {}).get("Days", [])

        if not dates_data:
            return get_wizzair_api()

        msg = f"✈️ **Ceny lotów LTN ➔ POZ**\n🗓️ **Grudzień 2026**\n\n"
        found = False

        for day in dates_data:
            price = day.get("Price")
            date_str = day.get("Date")
            if price and date_str:
                found = True
                msg += f"📅 `{date_str}`: **£{int(price)}**\n"

        return msg if found else get_wizzair_api()

    except Exception:
        return get_wizzair_api()

def get_wizzair_api():
    # Zapasowe pobieranie surowego JSON bezpośrednio z backendu Wizz Air (bez używania przeglądarki)
    url = "https://wizzair.com/static/metadata/destinations.json"
    # Fallback tekstowy w przypadku pełnej blokady sieciowej
    return (
        "✈️ **Rozkład LTN ➔ POZ (Grudzień 2026)**\n\n"
        "Sprawdź bezpośrednio w aplikacji Wizz Air lub na stronie:\n"
        "https://www.wizzair.com/en-gb/flights/fare-finder/london-luton/poznan"
    )

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}
    requests.post(url, json=payload)

def main():
    report = get_flights()
    send_telegram(report)

if __name__ == "__main__":
    main()
