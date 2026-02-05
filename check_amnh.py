#!/usr/bin/env python3
"""AMNH Early Adventures Monitor - GitHub Actions version with Playwright"""

import hashlib
import os
import sys
from pathlib import Path

URL = "https://www.amnh.org/learn-teach/children-and-families/early-adventures"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "amnh-early-adventures")
STATE_FILE = Path("state.txt")
FAIL_COUNT_FILE = Path("fail_count.txt")

def send_notification(message, title="AMNH Early Adventures"):
    import requests
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode('utf-8'),
        headers={"Title": title, "Priority": "high", "Tags": "school,tada"}
    )
    print(f"Notification sent: {message}")

def get_fail_count():
    if FAIL_COUNT_FILE.exists():
        return int(FAIL_COUNT_FILE.read_text().strip() or "0")
    return 0

def set_fail_count(count):
    FAIL_COUNT_FILE.write_text(str(count))

def main():
    from playwright.sync_api import sync_playwright
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(URL, timeout=60000)  # 60 sec timeout for navigation
            
            # Wait for actual content to load (the main content area)
            page.wait_for_selector("main", timeout=60000)
            
            content = page.content()
            browser.close()
        
        # Success - reset fail counter
        set_fail_count(0)
        
    except Exception as e:
        fail_count = get_fail_count() + 1
        set_fail_count(fail_count)
        print(f"Fetch failed (attempt {fail_count}): {e}")
        
        if fail_count >= 3:
            send_notification(f"Monitor failed 3x in a row: {e}", title="⚠️ AMNH Monitor Error")
            set_fail_count(0)  # Reset after notifying
        
        sys.exit(0)  # Don't fail the workflow
    
    current_hash = hashlib.md5(content.encode()).hexdigest()
    has_2027 = "2027" in content
    
    previous_hash = STATE_FILE.read_text().strip() if STATE_FILE.exists() else None
    
    if previous_hash is None:
        STATE_FILE.write_text(current_hash)
        print("Baseline saved.")
        if has_2027:
            send_notification("2027 info is ALREADY on the page!")
    elif current_hash != previous_hash:
        STATE_FILE.write_text(current_hash)
        if has_2027:
            send_notification("🎉 Page updated with 2027 info! Applications may be open!")
    else:
        print("No changes.")

if __name__ == "__main__":
    main()
