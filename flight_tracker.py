import os
import requests
import time
from datetime import datetime
from serpapi import GoogleSearch

ORIGIN = "LTN"
DESTINATION = "POZ"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
SERP_KEY = os.environ.get("SERPAPI_KEY")

def get_december_flights():
    if not SERP_KEY:
        return "⚠️ Błąd: Brak klucza SERPAPI_KEY.", []

    msg = f"✈️ **Ceny lotów LTN ➔ POZ**\n🗓️ **15–24 Grudnia 2026 (Google Flights)**\n\n"
    table_data = []

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
                    msg += f"📅 `{date_str}` ({dep_time}): **£{price}**\n"
                    table_data.append({"date": date_str, "time": dep_time, "airline": "Wizz Air", "price": f"£{price}"})
                    day_flight_found = True
                    break
            
            if not day_flight_found:
                msg += f"📅 `{date_str}`: *Brak lotu Wizz Air*\n"
                table_data.append({"date": date_str, "time": "-", "airline": "-", "price": "Brak lotu"})

            time.sleep(0.5)

        except Exception as e:
            print(f"Błąd dla daty {date_str}: {e}")

    return msg, table_data

def generate_html(table_data):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = ""
    for row in table_data:
        highlight = "style='background-color: #e6ffe6; font-weight: bold;'" if "£" in row['price'] and int(row['price'].replace('£','')) <= 70 else ""
        rows += f"<tr {highlight}><td>{row['date']}</td><td>{row['time']}</td><td>{row['airline']}</td><td>{row['price']}</td></tr>\n"

    html_content = f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ceny lotów LTN -> POZ</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 30px; background-color: #f4f4f9; }}
        h2 {{ color: #333; }}
        table {{ width: 100%; max-width: 600px; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #0056b3; color: white; }}
        tr:hover {{ background-color: #f1f1f1; }}
        .updated {{ font-size: 0.85em; color: #666; margin-top: 15px; }}
    </style>
</head>
<body>
    <h2>✈️ Ceny lotów London Luton (LTN) ➔ Poznań (POZ)</h2>
    <p>Grudzień 2026</p>
    <table>
        <thead>
            <tr>
                <th>Data</th>
                <th>Godzina</th>
                <th>Linia</th>
                <th>Cena</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    <p class="updated">Ostatnia aktualizacja: {now} UTC</p>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def main():
    report, table_data = get_december_flights()
    generate_html(table_data)
    send_telegram(report)

if __name__ == "__main__":
    main()
