#!/usr/bin/env python3
"""AMNH Early Adventures Monitor - Playwright version"""
import hashlib
import os
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://www.amnh.org/learn-teach/children-and-families/early-adventures"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "amnh-early-adventures")
STATE_FILE = Path("state.txt")

def send_notification(message):
    requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=message.encode('utf-8'),
                  headers={"Title": "AMNH Early Adventures", "Priority": "high", "Tags": "school"})
    print(f"Notification sent: {message}")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL, timeout=60000)
        content = page.content()
        browser.close()

    current_hash = hashlib.md5(content.encode()).hexdigest()
    has_target = "2026-2027" in content or "2026–2027" in content
    previous_hash = STATE_FILE.read_text().strip() if STATE_FILE.exists() else None

    if previous_hash is None:
        STATE_FILE.write_text(current_hash)
        print("Baseline saved.")
        if has_target:
            send_notification("2026-2027 info is ALREADY on the page!")
    elif current_hash != previous_hash:
        STATE_FILE.write_text(current_hash)
        msg = "🎉 Page updated with 2026-2027 info!" if has_target else "Page updated (no 2026-2027 yet)"
        send_notification(msg)
    else:
        print("No changes.")

if __name__ == "__main__":
    main()
