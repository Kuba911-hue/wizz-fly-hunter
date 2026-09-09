import os
import requests
import time
import json
from datetime import datetime

ORIGIN = "LTN"
DESTINATION = "POZ"

GITHUB_USER = "Kuba911-hue"
GITHUB_REPO = "wizz-fly-hunter"
SITE_URL = f"https://{GITHUB_USER}.github.io/{GITHUB_REPO}/"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Pobieranie obu kluczy
SERP_KEYS = [
    os.environ.get("SERPAPI_KEY"),
    os.environ.get("SERPAPI_KEY_2")
]
SERP_KEYS = [key for key in SERP_KEYS if key]

HISTORY_FILE = "history.json"

DAYS_NAMES_PL = ["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Niedz"]
MONTHS_NAMES_PL = ["Sty", "Lut", "Mar", "Kwi", "Maj", "Cze", "Lip", "Sie", "Wrz", "Paź", "Lis", "Gru"]

def format_date_pl(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        day_name = DAYS_NAMES_PL[dt.weekday()]
        month_name = MONTHS_NAMES_PL[dt.month - 1]
        return f"{day_name}, {dt.day} {month_name}"
    except Exception:
        return date_str

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
    if not SERP_KEYS:
        return "⚠️ Błąd krytyczny: Brak jakichkolwiek kluczy SERPAPI w Secrets.", [], {}

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    history = load_history()

    msg = f"✈️ Ceny lotów LTN ➔ POZ\n🗓️ 15–24 Grudnia 2026\n\n"
    current_data = []

    days_to_check = list(range(15, 25))

    for day in days_to_check:
        date_str = f"2026-12-{day:02d}"
        formatted_date = format_date_pl(date_str)
        
        params = {
            "engine": "google_flights",
            "departure_id": ORIGIN,
            "arrival_id": DESTINATION,
            "outbound_date": date_str,
            "currency": "GBP",
            "hl": "pl",
            "type": "2"
        }

        search_successful = False
        flights = []
        
        # Rotacja kluczy - z użyciem czystego API, które jest niezawodne
        for index, current_key in enumerate(SERP_KEYS):
            params["api_key"] = current_key
            try:
                response = requests.get("https://serpapi.com/search", params=params)
                results = response.json()
                
                # Sprawdzamy czy API zgłosiło błąd (np. brak kredytów)
                if "error" in results:
                    print(f"⚠️ Klucz #{index + 1} zwrócił błąd: {results['error']}")
                    continue
                
                # Sukces - pobieramy loty i przerywamy pętlę kluczy
                flights = results.get("best_flights", []) + results.get("other_flights", [])
                search_successful = True
                break
                
            except Exception as e:
                print(f"❌ Błąd połączenia na kluczu #{index + 1}: {e}")
                continue

        # CO JEŚLI WSZYSTKIE KLUCZE ZAWODZĄ?
        if not search_successful:
            msg += f"📅 {formatted_date}: ⚠️ Błąd API (Limit wyczerpany)\n"
            current_data.append({
                "date": date_str,
                "formatted_date": formatted_date,
                "time": "-",
                "airline": "-",
                "price": "Błąd API",
                "trend_html": "<span class='badge bg-danger'>API OFF</span>",
                "row_bg": "table-danger-custom"
            })
            time.sleep(0.5)
            continue # Przechodzimy do następnego dnia

        # Jeśli pobieranie danych się udało:
        day_flight_found = False
        for flight in flights:
            flight_details = flight.get("flights", [{}])[0]
            airline = flight_details.get("airline", "")
            
            if "Wizz" in airline:
                price = flight.get("price", "N/A")
                dep_time = flight_details.get("departure_airport", {}).get("time", "").split(" ")[-1]
                
                trend = "🆕"
                trend_html = "<span class='badge bg-secondary'>🆕 Nowy</span>"
                row_bg = ""

                if date_str in history and len(history[date_str]) > 0:
                    last_price = history[date_str][-1]["price"]
                    if isinstance(price, int) and isinstance(last_price, int):
                        diff = price - last_price
                        if diff < 0:
                            trend = f"🟢 ↓ (-£{abs(diff)})"
                            trend_html = f"<span class='badge bg-success'>🟢 ↓ (-£{abs(diff)})</span>"
                            row_bg = "table-success-custom"
                        elif diff > 0:
                            trend = f"🔴 ↑ (+£{diff})"
                            trend_html = f"<span class='badge bg-danger'>🔴 ↑ (+£{diff})</span>"
                            row_bg = "table-danger-custom"
                        else:
                            trend = "⚪ ="
                            trend_html = "<span class='badge bg-secondary'>⚪ Bez zmian</span>"

                msg += f"📅 {formatted_date} ({dep_time}): £{price} {trend}\n"
                
                current_data.append({
                    "date": date_str,
                    "formatted_date": formatted_date,
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
            msg += f"📅 {formatted_date}: Brak lotu Wizz Air\n"
            current_data.append({
                "date": date_str,
                "formatted_date": formatted_date,
                "time": "-",
                "airline": "-",
                "price": "Brak",
                "trend_html": "-",
                "row_bg": ""
            })

        time.sleep(0.5)

    save_history(history)
    msg += f"\n🌐 Pełny dashboard i wykresy:\n{SITE_URL}"

    return msg, current_data, history

def generate_html(current_data, history):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    valid_prices = [r['price'] for r in current_data if isinstance(r['price'], int)]
    best_deal = min(valid_prices) if valid_prices else 0
    best_deal_item = next((r for r in current_data if r['price'] == best_deal), None)
    avg_price = round(sum(valid_prices) / len(valid_prices)) if valid_prices else 0

    current_rows = ""
    for row in current_data:
        p_val = row['price']
        price_str = f"£{p_val}" if isinstance(p_val, int) else p_val
        
        hist_prices = [e['price'] for e in history.get(row['date'], []) if isinstance(e['price'], int)]
        min_hist = min(hist_prices) if hist_prices else "-"
        min_hist_str = f"£{min_hist}" if isinstance(min_hist, int) else min_hist
        
        advice_html = "<span class='badge bg-secondary'>Brak danych</span>"
        if isinstance(p_val, int):
            if p_val <= best_deal:
                advice_html = "<span class='badge bg-success'>🔥 KUP TERAZ</span>"
            elif p_val > avg_price:
                advice_html = "<span class='badge bg-danger'>⏳ CZEKAJ</span>"
            else:
                advice_html = "<span class='badge bg-warning text-dark'>⚖️ ŚREDNIA</span>"

        current_rows += f"<tr class='{row['row_bg']}'><td><strong>{row['formatted_date']}</strong></td><td>{row['time']}</td><td><strong>{price_str}</strong></td><td><small class='text-muted'>{min_hist_str}</small></td><td>{row['trend_html']}</td><td>{advice_html}</td></tr>\n"

    history_rows = ""
    for date_str in sorted(history.keys()):
        formatted_d = format_date_pl(date_str)
        entries = history[date_str]
        badges = []
        for i, entry in enumerate(entries):
            p = entry['price']
            ts = entry['timestamp']
            
            badge_class = "badge-neutral"
            diff_text = ""
            if i > 0:
                prev_p = entries[i-1]['price']
                if isinstance(p, int) and isinstance(prev_p, int):
                    diff = p - prev_p
                    if diff < 0:
                        badge_class = "badge-down"
                        diff_text = f" <small>(↓£{abs(diff)})</small>"
                    elif diff > 0:
                        badge_class = "badge-up"
                        diff_text = f" <small>(↑£{diff})</small>"

            badge_html = f"<span class='history-badge {badge_class}'><strong>£{p}</strong>{diff_text} <span class='ts'>({ts})</span></span>"
            badges.append(badge_html)
            
        history_rows += f"<tr><td style='white-space: nowrap;'><strong>{formatted_d}</strong></td><td>{' ➔ '.join(badges)}</td></tr>\n"

    all_timestamps = set()
    for entries in history.values():
        for e in entries:
            all_timestamps.add(e['timestamp'])
    sorted_timestamps = sorted(list(all_timestamps))

    chart_datasets = []
    colors = ['#3b82f6', '#10b981', '#ef4444', '#f59e0b', '#8b5cf6', '#06b6d4', '#ec4899', '#6b7280', '#14b8a6', '#eab308']
    
    for idx, date_str in enumerate(sorted(history.keys())):
        entries = {e['timestamp']: e['price'] for e in history[date_str]}
        data_points = [entries.get(ts, None) for ts in sorted_timestamps]
        color = colors[idx % len(colors)]
        chart_datasets.append({
            "label": format_date_pl(date_str),
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

    bar_labels = [row['formatted_date'] for row in current_data]
    bar_values = [row['price'] if isinstance(row['price'], int) else 0 for row in current_data]

    best_deal_text = f"{best_deal_item['formatted_date']} (£{best_deal})" if best_deal_item else "Brak"

    html_content = f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WizzAir Flight Radar - LTN to POZ</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-color: #f8fafc;
            --text-muted: #94a3b8;
            --border-color: #334155;
            --primary: #38bdf8;
            --success-bg: rgba(16, 185, 129, 0.15);
            --danger-bg: rgba(239, 68, 68, 0.15);
        }}

        @media (prefers-color-scheme: light) {{
            :root {{
                --bg-color: #f8fafc;
                --card-bg: #ffffff;
                --text-color: #0f172a;
                --text-muted: #64748b;
                --border-color: #e2e8f0;
                --primary: #0284c7;
                --success-bg: #dcfce7;
                --danger-bg: #fee2e2;
            }}
        }}

        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 20px; background-color: var(--bg-color); color: var(--text-color); }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        
        .card {{ background: var(--card-bg); padding: 20px; border-radius: 16px; border: 1px solid var(--border-color); margin-bottom: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
        
        .deal-banner {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .deal-card {{ background: var(--card-bg); border: 1px solid var(--border-color); padding: 15px; border-radius: 12px; text-align: center; }}
        .deal-card h4 {{ margin: 0 0 5px 0; color: var(--text-muted); font-size: 0.85em; text-transform: uppercase; }}
        .deal-card .val {{ font-size: 1.6em; font-weight: bold; color: var(--primary); }}

        h2, h3 {{ color: var(--text-color); margin-top: 0; }}
        .text-muted {{ color: var(--text-muted); }}

        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.95em; }}
        th, td {{ padding: 12px 10px; text-align: left; border-bottom: 1px solid var(--border-color); }}
        th {{ background-color: rgba(0,0,0,0.05); color: var(--text-muted); font-weight: 600; }}

        .table-success-custom {{ background-color: var(--success-bg); }}
        .table-danger-custom {{ background-color: var(--danger-bg); }}

        .badge {{ display: inline-block; padding: 4px 8px; border-radius: 6px; font-size: 0.8em; font-weight: 600; }}
        .bg-success {{ background: #10b981; color: white; }}
        .bg-danger {{ background: #ef4444; color: white; }}
        .bg-secondary {{ background: #6b7280; color: white; }}
        .bg-warning {{ background: #f59e0b; color: white; }}

        .history-badge {{ display: inline-block; padding: 4px 8px; margin: 2px; border-radius: 6px; font-size: 0.85em; border: 1px solid var(--border-color); }}
        .badge-neutral {{ background: rgba(255,255,255,0.05); }}
        .badge-down {{ background: var(--success-bg); border-color: #10b981; }}
        .badge-up {{ background: var(--danger-bg); border-color: #ef4444; }}
        .ts {{ font-size: 0.8em; color: var(--text-muted); opacity: 0.8; }}

        .chart-container {{ position: relative; height: 350px; width: 100%; margin-top: 15px; }}

        .footer {{ text-align: center; margin-top: 30px; color: var(--text-muted); font-size: 0.8em; opacity: 0.7; }}
    </style>
</head>
<body>

<div class="container">
    <div class="card" style="text-align: center;">
        <h2 style="margin:0; font-size: 1.8em;">✈️ WizzAir Radar: LTN ➔ POZ</h2>
        <p style="margin:5px 0 0 0; color: var(--text-muted);">Okres: 15–24 Grudnia 2026 | Ostatnia aktualizacja: {now}</p>
    </div>

    <div class="deal-banner">
        <div class="deal-card">
            <h4>Złoty Strzał 🎯</h4>
            <div class="val">{best_deal_text}</div>
        </div>
        <div class="deal-card">
            <h4>Średnia Cena Okresu ⚖️</h4>
            <div class="val">£{avg_price}</div>
        </div>
    </div>

    <div class="card">
        <h3>📊 Najnowsze odczyty</h3>
        <div style="overflow-x:auto;">
            <table>
                <tr>
                    <th>Data lotu</th>
                    <th>Godzina</th>
                    <th>Obecna Cena</th>
                    <th>Hist. Min</th>
                    <th>Trend (ostatni skan)</th>
                    <th>Rekomendacja</th>
                </tr>
                {current_rows}
            </table>
        </div>
    </div>

    <div class="card">
        <h3>📉 Wizualizacja trendów (porównanie po datach skanowania)</h3>
        <div class="chart-container">
            <canvas id="trendChart"></canvas>
        </div>
    </div>

    <div class="card">
        <h3>📊 Zestawienie obecnych cen w grudniu</h3>
        <div class="chart-container" style="height: 250px;">
            <canvas id="barChart"></canvas>
        </div>
    </div>

    <div class="card">
        <h3>📜 Historia zmian cen (Timeline)</h3>
        <div style="overflow-x:auto;">
            <table>
                <tr>
                    <th style="width: 120px;">Data lotu</th>
                    <th>Historia pomiarów (od najstarszego)</th>
                </tr>
                {history_rows}
            </table>
        </div>
    </div>
    
    <div class="footer">
        Coded by Jakub Wulczyński | Wizz-Fly-Hunter 2026
    </div>
</div>

<script>
    const chartData = {json.dumps(chart_config)};
    
    const ctx = document.getElementById('trendChart').getContext('2d');
    new Chart(ctx, {{
        type: 'line',
        data: chartData,
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            interaction: {{ mode: 'index', intersect: false }},
            plugins: {{
                legend: {{ position: 'right', labels: {{ color: getComputedStyle(document.body).getPropertyValue('--text-color') }} }}
            }},
            scales: {{
                x: {{ ticks: {{ color: '#94a3b8', maxRotation: 45, minRotation: 45 }} }},
                y: {{ title: {{ display: true, text: 'Cena w GBP (£)' }}, ticks: {{ color: '#94a3b8' }} }}
            }}
        }}
    }});

    const barCtx = document.getElementById('barChart').getContext('2d');
    new Chart(barCtx, {{
        type: 'bar',
        data: {{
            labels: {json.dumps(bar_labels)},
            datasets: [{{
                label: 'Obecna cena (£)',
                data: {json.dumps(bar_values)},
                backgroundColor: 'rgba(56, 189, 248, 0.6)',
                borderColor: '#38bdf8',
                borderWidth: 1,
                borderRadius: 4
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{ legend: {{ display: false }} }},
            scales: {{
                x: {{ ticks: {{ color: '#94a3b8' }} }},
                y: {{ ticks: {{ color: '#94a3b8' }} }}
            }}
        }}
    }});
</script>
</body>
</html>"""
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

def send_telegram_message(message):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "disable_web_page_preview": True
        }
        try:
            requests.post(url, json=payload)
        except Exception as e:
            print(f"Błąd wysyłania Telegram: {e}")
    else:
        print("Brak tokenu/ID Telegrama. Wiadomość:")
        print(message)

if __name__ == "__main__":
    msg, current_data, history = get_december_flights()
    generate_html(current_data, history)
    send_telegram_message(msg)
