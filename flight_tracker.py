import os
import json
import requests
from datetime import datetime
from serpapi import GoogleSearch

# Pobieranie tokenów z Environment Variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Lista kluczy SerpApi do rotacji
SERPAPI_KEYS = [
    os.getenv("SERPAPI_KEY"),
    os.getenv("SERPAPI_KEY_2")
]
# Filtrowanie pustych kluczy
SERPAPI_KEYS = [k for k in SERPAPI_KEYS if k]

# Konfiguracja wyszukiwania (LTN -> POZ)
DEPARTURE_ID = "LTN"
ARRIVAL_ID = "POZ"
DATES_TO_CHECK = [f"2026-12-{day:02d}" for day in range(15, 25)]

def get_flights_for_date(date):
    """Pobiera najtańszy lot dla podanej daty, automatycznie rotując kluczami SerpApi."""
    if not SERPAPI_KEYS:
        print("⚠️ Brak skonfigurowanych kluczy SERPAPI_KEY!", flush=True)
        return None

    for idx, key in enumerate(SERPAPI_KEYS, start=1):
        try:
            params = {
                "engine": "google_flights",
                "departure_id": DEPARTURE_ID,
                "arrival_id": ARRIVAL_ID,
                "outbound_date": date,
                "type": "2",  # 2 oznacza lot w jedną stronę (One way)
                "currency": "GBP",
                "hl": "pl",
                "api_key": key
            }
            search = GoogleSearch(params)
            results = search.get_dict()

            # Sprawdzenie błędu wyczerpania limitu
            if "error" in results:
                err_msg = str(results["error"])
                if "run out of searches" in err_msg.lower():
                    print(f"⚠️ Klucz SerpApi #{idx} wyczerpany dla daty {date}. Przełączam na kolejny...", flush=True)
                    continue  # Przejście do kolejnego klucza
                else:
                    print(f"⚠️ Błąd SerpApi #{idx} ({date}): {err_msg}", flush=True)
                    return None

            best_flights = results.get("best_flights", [])
            other_flights = results.get("other_flights", [])
            all_flights = best_flights + other_flights

            if not all_flights:
                return None

            return min(f.get("price", 9999) for f in all_flights)

        except Exception as e:
            print(f"⚠️ Wyjątek przy kluczu #{idx} dla daty {date}: {e}", flush=True)
            continue

    print(f"❌ Wszystkie klucze SerpApi zostały wyczerpane dla daty {date}!", flush=True)
    return None

def send_telegram(text):
    """Wysyłanie powiadomienia na Telegram z pełnym logowaniem."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Brak TELEGRAM_TOKEN lub TELEGRAM_CHAT_ID w środowisku!", flush=True)
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
    """Wczytywanie historii z pliku JSON."""
    if os.path.exists("history.json"):
        with open("history.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_history(history):
    """Zapisywanie aktualnej historii cen do JSON."""
    with open("history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def main():
    print("🚀 Rozpoczynanie weryfikacji cen lotów...", flush=True)
    history = load_history()
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    current_results = {}
    report_lines = [f"✈️ **Raport Ceny Lotów (LTN -> POZ)**\n📅 _{today_str}_\n"]

    for date in DATES_TO_CHECK:
        print(f"🔍 Sprawdzanie {date}...", flush=True)
        price = get_flights_for_date(date)
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
    print("✅ Proces zakończony powodzeniem.", flush=True)

if __name__ == "__main__":
    main()
