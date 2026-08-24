import os
import requests
import time
import json
from datetime import datetime
from serpapi import GoogleSearch

ORIGIN = "LTN"
DESTINATION = "POZ"

GITHUB_USER = "Kuba911-hue"
GITHUB_REPO = "wizz-fly-hunter"
SITE_URL = f"https://{GITHUB_USER}.github.io/{GITHUB_REPO}/"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
SERP_KEY = os.environ.get("SERPAPI_KEY")

HISTORY_FILE = "history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def get_december_flights():
    if not SERP_KEY:
        return "⚠️ Błąd: Brak klucza SERPAPI_KEY.", [], {}

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    history = load_history()

    msg = f"✈️ Ceny lotów LTN ➔ POZ\n🗓️ 15–24 Grudnia 2026\n\n"
    current_data = []

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
            
            day_flight_found = False
            for flight in flights:
                flight_details = flight.get("flights", [{}])[0]
                airline = flight_details.get("airline", "")
                
                if "Wizz" in airline:
                    price = flight.get("price", "N/A")
                    dep_time = flight_details.get("departure_airport", {}).get("time", "").split(" ")[-1]
                    
                    trend = "🆕"
                    trend_html = "<span style='color: #6c757d;'>🆕 Nowy</span>"
                    row_bg = ""

                    if date_str in history and len(history[date_str]) > 0:
                        last_price = history[date_str][-1]["price"]
                        if isinstance(price, int) and isinstance(last_price, int):
                            diff = price - last_price
                            if diff < 0:
                                trend = f"🟢 ↓ (-£{abs(diff)})"
                                trend_html = f"<span style='color: #28a745; font-weight: bold;'>🟢 ↓ (-£{abs(diff)})</span>"
                                row_bg = "style='background-color: #e6f4ea;'"
                            elif diff > 0:
                                trend = f"🔴 ↑ (+£{diff})"
                                trend_html = f"<span style='color: #dc3545; font-weight: bold;'>🔴 ↑ (+£{diff})</span>"
                                row_bg = "style='background-color: #fce8e6;'"
                            else:
                                trend = "⚪ ="
                                trend_html = "<span style='color: #6c757d;'>⚪ Bez zmian</span>"

                    msg += f"📅 {date_str} ({dep_time}): £{price} {trend}\n"
                    
                    current_data.append({
                        "date": date_str,
                        "time": dep_time,
                        "airline": "Wizz Air",
                        "price": price,
                        "trend_html": trend_html,
                        "row_bg": row_bg
                    })
                    
                    if date_str not in history:
                        history[date_str] = []
                    history[date_str].append({"timestamp": timestamp, "price": price})

                    day_flight_found = True
                    break
            
            if not day_flight_found:
                msg += f"📅 {date_str}: Brak lotu Wizz Air\n"
                current_data.append({
                    "date": date_str,
                    "time": "-",
                    "airline": "-",
                    "price": "Brak",
                    "trend_html": "-",
                    "row_bg": ""
                })

            time.sleep(0.5)

        except Exception as e:
            print(f"Błąd dla daty {date_str}: {e}")

    save_history(history)
    msg += f"\n🌐 Pełna historia i wykresy na stronie:\n{SITE_URL}"

    return msg, current_data, history

def generate_html(current_data, history):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    current_rows = ""
    for row in current_data:
        p_val = row['price']
        price_str = f"£{p_val}" if isinstance(p_val, int) else p_val
        current_rows += f"<tr {row['row_bg']}><td><strong>{row['date']}</strong></td><td>{row['time']}</td><td>{row['airline']}</td><td><strong>{price_str}</strong></td><td>{row['trend_html']}</td></tr>\n"

    # Przygotowanie czytelnej historii z badgami
    history_rows = ""
    for date_str in sorted(history.keys()):
        entries = history[date_str]
        badges = []
        for i, entry in enumerate(entries):
            p = entry['price']
            ts = entry['timestamp']
            
            # Kolorowanie zmian w historii
            badge_style = "background: #e9ecef; color: #495057;"
            diff_text = ""
            if i > 0:
                prev_p = entries[i-1]['price']
                if isinstance(p, int) and isinstance(prev_p, int):
                    diff = p - prev_p
                    if diff < 0:
                        badge_style = "background: #d4edda; color: #155724; border: 1px solid #c3e6cb;"
                        diff_text = f" <small>(↓£{abs(diff)})</small>"
                    elif diff > 0:
                        badge_style = "background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;"
                        diff_text = f" <small>(↑£{diff})</small>"

            badge_html = f"<span style='display: inline-block; padding: 4px 8px; margin: 2px; border-radius: 6px; font-size: 0.9em; {badge_style}'><strong>£{p}</strong>{diff_text} <span style='font-size: 0.75em; opacity: 0.75;'>({ts})</span></span>"
            badges.append(badge_html)
            
        history_rows += f"<tr><td style='white-space: nowrap;'><strong>{date_str}</strong></td><td>{' ➔ '.join(badges)}</td></tr>\n"

    # Przygotowanie danych do wykresu (Chart.js)
    all_timestamps = set()
    for entries in history.values():
        for e in entries:
            all_timestamps.add(e['timestamp'])
    sorted_timestamps = sorted(list(all_timestamps))

    chart_datasets = []
    colors = ['#007bff', '#28a745', '#dc3545', '#fd7e14', '#6f42c1', '#17a2b8', '#e83e8c', '#6c757d', '#20c997', '#ffc107']
    
    for idx, date_str in enumerate(sorted(history.keys())):
        entries = {e['timestamp']: e['price'] for e in history[date_str]}
        data_points = [entries.get(ts, None) for ts in sorted_timestamps]
        color = colors[idx % len(colors)]
        chart_datasets.append({
            "label": date_str,
            "data": data_points,
            "borderColor": color,
            "backgroundColor": color,
            "fill": False,
            "tension": 0.2
        })

    chart_config = {
        "labels": sorted_timestamps,
        "datasets": chart_datasets
    }

    html_content = f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ceny lotów LTN -> POZ</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 20px; background-color: #f4f6f9; color: #333; }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        .card {{ background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 25px; }}
        h2, h3 {{ color: #0056b3; margin-top: 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #edf2f7; }}
        th {{ background-color: #0056b3; color: white; font-weight: 600; }}
        th:first-child {{ border-top-left-radius: 8px; }}
        th:last-child {{ border-top-right-radius: 8px; }}
        .updated {{ font-size: 0.85em; color: #6c757d; text-align: right; margin-top: 10px; }}
        .chart-container {{ position: relative; height: 350px; width: 100%; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h2>✈️ Ceny lotów London Luton (LTN) ➔ Poznań (POZ)</h2>
            <p style="color: #666; margin-bottom: 0;">Okres: <strong>15–24 Grudnia 2026</strong> (Wizz Air)</p>
        </div>

        <div class="card">
            <h3>📈 Wykres zmian cen w czasie</h3>
            <div class="chart-container">
                <canvas id="priceChart"></canvas>
            </div>
        </div>

        <div class="card">
            <h3>📊 Aktualne ceny i ost. zmiana</h3>
            <table>
                <thead>
                    <tr>
                        <th>Data lotu</th>
                        <th>Godzina</th>
                        <th>Linia</th>
                        <th>Cena</th>
                        <th>Status / Zmiana</th>
                    </tr>
                </thead>
                <tbody>
                    {current_rows}
                </tbody>
            </table>
        </div>

        <div class="card">
            <h3>📜 Pełna historia pomiarów</h3>
            <table>
                <thead>
                    <tr>
                        <th>Data lotu</th>
                        <th>Historia odczytów</th>
                    </tr>
                </thead>
                <tbody>
                    {history_rows}
                </tbody>
            </table>
            <p class="updated">Ostatnia aktualizacja danych: {now} UTC</p>
        </div>
    </div>

    <script>
        const chartData = {json.dumps(chart_config)};
        const ctx = document.getElementById('priceChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: chartData,
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                    }},
                    tooltip: {{
                        mode: 'index',
                        intersect: false
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: false,
                        title: {{
                            display: true,
                            text: 'Cena (£)'
                        }}
                    }},
                    x: {{
                        title: {{
                            display: true,
                            text: 'Data sprawdzania'
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Brak TOKENA lub CHAT_ID Telegrama")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": text,
        "disable_web_page_preview": False
    }
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"⚠️ Błąd wysyłania Telegram: {response.status_code} - {response.text}")

def main():
    report, current_data, history = get_december_flights()
    generate_html(current_data, history)
    send_telegram(report)

if __name__ == "__main__":
    main()
