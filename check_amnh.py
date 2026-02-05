#!/usr/bin/env python3
"""AMNH Early Adventures Monitor - checks for 2027 mention"""
import requests
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://www.amnh.org/learn-teach/children-and-families/early-adventures"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "amnh-early-adventures")
STATE_FILE = Path("state.txt")

def send_notification(message, title="AMNH Early Adventures", priority="high", tags="school,tada"):
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode('utf-8'),
        headers={"Title": title, "Priority": priority, "Tags": tags}
    )
    print(f"Notification sent: {message}")

def get_page_content():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle")
        content = page.content()
        browser.close()
        return content

def main():
    try:
        content = get_page_content()
    except Exception as e:
        send_notification(f"Monitor failed: {e}", priority="default", tags="warning")
        raise

    found_2027 = "2027" in content
    already_notified = STATE_FILE.exists() and STATE_FILE.read_text().strip() == "notified"

    if found_2027 and not already_notified:
        send_notification("🎉 2027 found on the Early Adventures page! Applications may be open!")
        STATE_FILE.write_text("notified")
    elif found_2027:
        print("2027 still there, already notified.")
    else:
        print("No 2027 yet.")
        STATE_FILE.write_text("waiting")

if __name__ == "__main__":
    main()
