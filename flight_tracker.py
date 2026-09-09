import os
import json
import requests
from datetime import datetime
from serpapi import GoogleSearch

# Pobieranie tokenów ze środowiska
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Klucze SerpApi do rotacji
SERPAPI_KEYS = [
    os.getenv("SERPAPI_KEY"),
    os.getenv("SERPAPI_KEY_2")
]
SERPAPI_KEYS = [k for k in SERPAPI_KEYS if k]

DEPARTURE_ID = "LTN"
ARRIVAL_ID = "POZ"
DATES_TO_CHECK = [f"2026-12-{day:02d}" for day in range(15, 25)]

DAYS_PL = ["Pn", "Wt", "Śr", "Czw", "Pt", "Sob", "Niedz"]
MONTHS_PL = {12: "Gru"}

def format_date_pl(date_str):
    """Formatowanie daty na polski skrót, np. 'Wt, 15 Gru'."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    day_name = DAYS_PL[dt.weekday()]
    day_num = dt.day
    month_name = MONTHS_PL.get(dt.month, str(dt.month))
    return f"{day_name}, {day_num} {month_name}"

def get_flights_for_date(date):
    """Pobiera najtańszy lot i godzinę odlotu z rotacją kluczy SerpApi."""
    if not SERPAPI_KEYS:
        print("⚠️ Brak kluczy SERPAPI_KEY!", flush=True)
        return None, None

    for idx, key in enumerate(SERPAPI_KEYS, start=1):
        try:
            params = {
                "engine": "google_flights",
                "departure_id": DEPARTURE_ID,
                "arrival_id": ARRIVAL_ID,
                "outbound_date": date,
                "type": "2",  # Lot w jedną stronę
                "currency": "GBP",
                "hl": "pl",
                "api_key": key
            }
            search = GoogleSearch(params)
            results = search.get_dict()

            if "error" in results:
                err_msg = str(results["error"])
                if "run out of searches" in err_msg.lower():
                    print(f"⚠️ Klucz #{idx} wyczerpany dla {date}. Przełączam...", flush=True)
                    continue
                else:
                    print(f"⚠️ Błąd SerpApi #{idx} ({date}): {err_msg}", flush=True)
                    return None, None

            best_flights = results.get("best_flights", [])
            other_flights = results.get("other_flights", [])
            all_flights = best_flights + other_flights

            if not all_flights:
                return None, None

            # Znalezienie najtańszego lotu
            cheapest = min(all_flights, key=lambda x: x.get("price", 9999))
            price = cheapest.get("price")

            # Wyciągnięcie godziny odlotu
            dep_time = "07:45"
            flights_leg = cheapest.get("flights", [])
            if flights_leg:
                dt_info = flights_leg[0].get("departure_time")
                if isinstance(dt_info, dict):
                    dep_time = dt_info.get("time", "07:45")
                elif isinstance(dt_info, str):
                    dep_time = dt_info

            return price, dep_time

        except Exception as e:
            print(f"⚠️ Wyjątek przy kluczu #{idx} dla {date}: {e}", flush=True)
            continue

    print(f"❌ Wszystkie klucze wyczerpane dla {date}!", flush=True)
    return None, None

def send_telegram(text):
    """Wysyłanie wiadomości na Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Brak tokena/ID Telegrama!", flush=True)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        print(f"📩 Telegram Status [{res.status_code}]", flush=True)
    except Exception as e:
        print(f"⚠️ Błąd Telegrama: {e}", flush=True)

def load_history():
    """Wczytanie pliku z historią."""
    if os.path.exists("history.json"):
        with open("history.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_history(history):
    """Zapis historii do pliku JSON."""
    with open("history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def get_last_prices(history):
    """Pobiera ostatnio zapisane ceny dla porównania zmian."""
    if not history:
        return {}
    last_key = list(history.keys())[-1]
    return history.get(last_key, {})

def main():
    print("🚀 Rozpoczynanie sprawdzania cen...", flush=True)
    history = load_history()
    last_prices = get_last_prices(history)
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    current_results = {}
    report_lines = [
        "✈️ Ceny lotów LTN ➔ POZ",
        "📅 15–24 Grudnia 2026\n"
    ]

    for date in DATES_TO_CHECK:
        print(f"🔍 Sprawdzanie {date}...", flush=True)
        price, dep_time = get_flights_for_date(date)
        date_formatted = format_date_pl(date)

        if price:
            current_results[date] = price
            prev_price = last_prices.get(date)

            # Wyznaczenie wskaźnika i różnicy ceny po prawej stronie
            if prev_price is not None:
                diff = price - prev_price
                if diff > 0:
                    indicator = f"🔴 ↑ (+£{diff})"
                elif diff < 0:
                    indicator = f"🟢 ↓ (-£{abs(diff)})"
                else:
                    indicator = "⚪️ ="
            else:
                indicator = "⚪️ ="

            time_str = f"({dep_time})" if dep_time else ""
            report_lines.append(f"🗓️ {date_formatted} {time_str}: £{price} {indicator}")
        else:
            report_lines.append(f"🗓️ {date_formatted}: Brak lotu Wizz Air")

    # Stopka z odnośnikiem do dashboardu
    report_lines.append("\n🌐 Pełny dashboard i wykresy:")
    report_lines.append("https://Kuba911-hue.github.io/wizz-fly-hunter/")

    # Zapis w historii
    history[today_str] = current_results
    save_history(history)

    # Wysyłka wiadomości
    report_text = "\n".join(report_lines)
    send_telegram(report_text)
    print("✅ Gotowe.", flush=True)

if __name__ == "__main__":
    main()
