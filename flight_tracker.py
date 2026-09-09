import os
import json
import requests
from datetime import datetime
from serpapi import GoogleSearch

# Pobranie zmiennych środowiskowych
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
HASDATA_KEY = os.getenv("HASDATA_KEY")

# Konfiguracja lotów (LTN -> POZ, Grudzień 2026)
DEPARTURE_ID = "LTN"
ARRIVAL_ID = "POZ"
DATES_TO_CHECK = [f"2026-12-{day:02d}" for day in range(15, 25)]

def get_flights_serpapi(date):
    """Pobieranie danych z SerpApi."""
    if not SERPAPI_KEY:
        return None
    try:
        params = {
            "engine": "google_flights",
            "departure_id": DEPARTURE_ID,
            "arrival_id": ARRIVAL_ID,
            "outbound_date": date,
            "currency": "GBP",
            "hl": "pl",
            "api_key": SERPAPI_KEY
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        
        if "error" in results:
            print(f"⚠️ SerpApi Error dla {date}: {results['error']}", flush=True)
            return None
            
        best_flights = results.get("best_flights", [])
        other_flights = results.get("other_flights", [])
        all_flights = best_flights + other_flights
        
        if not all_flights:
            return None
            
        # Wyciąganie najtańszego lotu
        min_price = min(f.get("price", 9999) for f in all_flights)
        return min_price
    except Exception as e:
        print(f"⚠️ Wyjątek SerpApi ({date}): {e}", flush=True)
        return None

def get_flights_hasdata(date):
    """Fallback: Pobieranie danych z HasData API."""
    if not HASDATA_KEY:
        return None
    try:
        url = "https://api.hasdata.com/scrape/google-flights"
        headers = {
            "x-api-key": HASDATA_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "departureId": DEPARTURE_ID,
            "arrivalId": ARRIVAL_ID,
            "outboundDate": date,
            "currency": "GBP",
            "hl": "pl"
        }
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"⚠️ HasData HTTP Error {response.status_code} dla {date}", flush=True)
            return None
            
        data = response.json()
        best_flights = data.get("bestFlights", [])
        other_flights = data.get("otherFlights", [])
        all_flights = best_flights + other_flights
        
        if not all_flights:
            return None
            
        min_price = min(f.get("price", 9999) for f in all_flights)
        return min_price
    except Exception as e:
        print(f"⚠️ Wyjątek HasData ({date}): {e}", flush=True)
        return None

def fetch_price_for_date(date):
    """Próbuje SerpApi, a w przypadku niepowodzenia przełącza się na HasData."""
    print(f"🔍 Sprawdzanie {date} via SerpApi...", flush=True)
    price = get_flights_serpapi(date)
    
    if price is None:
        print(f"🔄 Przełączanie na HasData dla daty {date}...", flush=True)
        price = get_flights_hasdata(date)
        
    return price

def send_telegram(text):
    """Wysyłanie powiadomienia na Telegram z pełnym logowaniem."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Brak tokena/ID Telegrama!", flush=True)
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        print(f"📩 Telegram Status [{res.status_code}]: {res.text}", flush=True)
    except Exception as e:
        print(f"⚠️ Błąd wysyłania Telegram: {e}", flush=True)

def load_history():
    """Wczytywanie pliku history.json."""
    if os.path.exists("history.json"):
        with open("history.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_history(history):
    """Zapisywanie danych do history.json."""
    with open("history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def main():
    print("🚀 Rozpoczynanie weryfikacji cen lotów...", flush=True)
    history = load_history()
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    current_results = {}
    report_lines = [f"✈️ **Raport Ceny Lotów (LTN -> POZ)**\n📅 _{today_str}_\n"]
    
    for date in DATES_TO_CHECK:
        price = fetch_price_for_date(date)
        if price:
            current_results[date] = price
            report_lines.append(f"• `{date}`: **£{price}**")
        else:
            report_lines.append(f"• `{date}`: ❌ Brak danych")
            
    # Zapis historii
    history[today_str] = current_results
    save_history(history)
    
    # Wysyłka powiadomienia
    report_text = "\n".join(report_lines)
    send_telegram(report_text)
    print("✅ Proces zakończony.", flush=True)

if __name__ == "__main__":
    main()
