#!/usr/bin/env python3
"""AMNH Early Adventures Monitor - GitHub Actions version"""

import requests
import hashlib
import os
from pathlib import Path

URL = "https://www.amnh.org/learn-teach/children-and-families/early-adventures"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "amnh-early-adventures")
STATE_FILE = Path("state.txt")

def get_page_content():
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    response = requests.get(URL, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text

def send_notification(message, title="AMNH Early Adventures"):
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode('utf-8'),
        headers={"Title": title, "Priority": "high", "Tags": "school,tada"}
    )
    print(f"Notification sent: {message}")

def main():
    content = get_page_content()
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
        if has_target:
            send_notification("🎉 Page updated with 2026-2027 info! Applications may be open!")
        else:
            send_notification("Page updated (no 2026-2027 info yet)")
    else:
        print("No changes.")

if __name__ == "__main__":
    main()
