import os
import requests

ORIGIN = "LTN"
DESTINATION = "POZ"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def get_kiwi_prices():
    # Publiczne API Kiwi pobierające bezpośrednio loty bez pośredników
    url = "https://api.skypicker.com/flights"
    params = {
        "fly_from": ORIGIN,
        "fly_to": DESTINATION,
        "date_from": "01/12/2026",
        "date_to": "31/12/2026",
        "curr": "GBP",
        "direct_flights": 1,
        "limit": 15,
        "sort": "price"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        res = requests.get(url, params=params, headers=headers, timeout=20)
        if res.status_code != 200:
            return None
            
        data = res.json().get("data", [])
        if not data:
            return "Brak bezpośrednich lotów w podanym terminie."

        results = {}
        for flight in data:
            # Formatowanie daty wylotu
            dtime = flight.get("local_departure", "").split("T")[0]
            price = flight.get("price")
            airline = flight.get("airlines", ["Wizz Air"])[0]
            
            # Grupowanie po dacie, aby zachować najniższą cenę danego dnia
            if dtime not in results or price < results[dtime]["price"]:
                results[dtime] = {"price": price, "airline": airline}

        # Budowanie czytelnej wiadomości tekstowej
        msg = f"✈️ **Ceny lotów bezpośrednich: {ORIGIN} ➔ {DESTINATION}**\n🗓️ **Grudzień 2026 (Kiwi)**\n\n"
        for date in sorted(results.keys()):
            info = results[date]
            msg += f"📅 `{date}`: **£{info['price']}** ({info['airline']})\n"
            
        return msg

    except Exception as e:
        print(f"Błąd Kiwi: {e}")
        return None

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def main():
    report = get_kiwi_prices()
    if report:
        send_telegram(report)
    else:
        send_telegram("⚠️ Nie udało się pobrać danych z Kiwi API. Sprawdź połączenie.")

if __name__ == "__main__":
    main()
