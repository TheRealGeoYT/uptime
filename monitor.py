import json
import os
import sys
import time
import requests

# Konfiguration und Datenpfade
CONFIG_FILE = "config.json"
DATA_FILE = "data/status.json"
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def send_discord_alert(service_name, url, status_code, error_msg):
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ Kein Discord Webhook konfiguriert (DISCORD_WEBHOOK_URL nicht gesetzt).")
        return

    payload = {
        "embeds": [
            {
                "title": f"🚨 Dienst offline: {service_name}",
                "color": 15158332,  # Rot
                "fields": [
                    {"name": "URL", "value": url, "inline": True},
                    {"name": "HTTP Status", "value": str(status_code) if status_code else "N/A", "inline": True},
                    {"name": "Fehlermeldung", "value": str(error_msg), "inline": False}
                ],
                "footer": {"text": "GitHub Uptime Monitor"}
            }
        ]
    }
    
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print(f"🔔 Discord Alert gesendet für {service_name}")
    except Exception as e:
        print(f"❌ Fehler beim Senden des Discord-Alerts: {e}")

def run_checks():
    if not os.path.exists(CONFIG_FILE):
        print(f"Fehler: {CONFIG_FILE} nicht gefunden.")
        sys.exit(1)

    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)

    results = []
    has_failure = False

    for service in config.get("services", []):
        name = service["name"]
        url = service["url"]
        expected_code = service.get("expected_code", 200)

        print(f"Prüfe {name} ({url})...")
        start_time = time.time()
        
        status_code = None
        is_up = False
        error_msg = ""

        try:
            response = requests.get(url, timeout=10)
            latency_ms = round((time.time() - start_time) * 1000, 2)
            status_code = response.status_code

            if status_code == expected_code:
                is_up = True
            else:
                error_msg = f"Unerwarteter Statuscode (Erwartet: {expected_code}, Erhalten: {status_code})"

        except requests.RequestException as e:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            error_msg = str(e)

        if not is_up:
            has_failure = True
            print(f"❌ {name} IST DOWN! ({error_msg})")
            send_discord_alert(name, url, status_code, error_msg)
        else:
            print(f"✅ {name} ist UP ({latency_ms}ms)")

        results.append({
            "name": name,
            "url": url,
            "up": is_up,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "error": error_msg
        })

    # Ergebnisse speichern
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump({"timestamp": int(time.time()), "results": results}, f, indent=2)

    # Wenn ein Dienst down ist, den Workflow mit Fehler beenden (optional, sorgt für rotes X in GitHub)
    if has_failure:
        sys.exit(1)

if __name__ == "__main__":
    run_checks()