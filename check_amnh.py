#!/usr/bin/env python3
"""AMNH Early Adventures Monitor v2 - with fallback, heartbeat, and better detection"""

import requests
import hashlib
import os
from pathlib import Path
from datetime import datetime

URL = "https://www.amnh.org/learn-teach/children-and-families/early-adventures"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "amnh-early-adventures")
STATE_FILE = Path("state.txt")

def get_page_content():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL, timeout=60000)
        page.wait_for_load_state("networkidle", timeout=60000)
        content = page.content()
        browser.close()
        return content

def send_notification(message, title="AMNH Early Adventures", priority="high", tags="school"):
    try:
        resp = requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode('utf-8'),
            headers={"Title": title, "Priority": priority, "Tags": tags},
            timeout=10
        )
        print(f"Notification sent: {message}")
        return resp.ok
    except Exception as e:
        print(f"ntfy failed: {e}")
        return False

def send_with_fallback(message, title="AMNH Early Adventures", priority="high", tags="school"):
    if not send_notification(message, title, priority, tags):
        raise Exception(f"NTFY FAILED - GitHub will email you. Message: {message}")

def main():
    print(f"Checking {URL}...")

    # Weekly heartbeat on Sundays around noon UTC
    if datetime.utcnow().weekday() == 6 and datetime.utcnow().hour == 12:
        send_notification("Weekly heartbeat: still monitoring, no 2027 yet.", 
                         title="AMNH Monitor Active", priority="low", tags="heartbeat")

    try:
        content = get_page_content()
    except Exception as e:
        send_with_fallback(f"Monitor error: {e}", title="AMNH Monitor Error", tags="warning")
        raise

    current_hash = hashlib.md5(content.encode()).hexdigest()
    has_2027 = "2027" in content
    has_2025 = "2025" in content

    previous_hash = STATE_FILE.read_text().strip() if STATE_FILE.exists() else None
    STATE_FILE.write_text(current_hash)

    if previous_hash is None:
        print(f"Baseline saved. has_2027={has_2027}, has_2025={has_2025}")
        if has_2027:
            send_with_fallback("2027 is ALREADY on the page!", title="🎉 AMNH 2027 Found!", tags="tada")
    elif current_hash != previous_hash:
        if has_2027:
            send_with_fallback("Page now shows 2027! Check it!", title="🎉 AMNH 2027 Found!", tags="tada")
        elif not has_2025:
            send_with_fallback("2025 is gone from the page - they may be updating!", title="AMNH Changing", tags="eyes")
        else:
            print("Page changed but still 2025, no 2027.")
    else:
        print("No changes.")

if __name__ == "__main__":
    main()
