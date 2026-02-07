#!/usr/bin/env python3
"""AMNH Early Adventures Monitor v2 - with fallback, heartbeat, and better detection"""
import requests
import hashlib
import os
import json
from pathlib import Path
from datetime import datetime, timezone

URL = "https://www.amnh.org/learn-teach/children-and-families/early-adventures"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "amnh-early-adventures")
STATE_FILE = Path("state.txt")
ERROR_STATE_FILE = Path("error_state.json")

# Only notify after this many consecutive errors (4 * 15min = 1 hour)
ERROR_THRESHOLD = 4
# Re-notify about persistent errors every 4 hours
ERROR_RE_NOTIFY_HOURS = 4


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


def load_error_state():
    if ERROR_STATE_FILE.exists():
        try:
            return json.loads(ERROR_STATE_FILE.read_text())
        except (json.JSONDecodeError, KeyError):
            pass
    return {"consecutive_errors": 0, "first_error_time": None, "last_notified_time": None}


def save_error_state(state):
    ERROR_STATE_FILE.write_text(json.dumps(state))


def handle_error(error):
    """Track consecutive errors; only notify after persistent failures."""
    state = load_error_state()
    state["consecutive_errors"] += 1
    now = datetime.now(timezone.utc).isoformat()

    if state["first_error_time"] is None:
        state["first_error_time"] = now

    print(f"Error #{state['consecutive_errors']}: {error}")

    if state["consecutive_errors"] >= ERROR_THRESHOLD:
        # Check if we already notified recently
        should_notify = True
        if state["last_notified_time"]:
            last = datetime.fromisoformat(state["last_notified_time"])
            hours_since = (datetime.now(timezone.utc) - last).total_seconds() / 3600
            if hours_since < ERROR_RE_NOTIFY_HOURS:
                should_notify = False
                print(f"Suppressing error notification (last sent {hours_since:.1f}h ago)")

        if should_notify:
            hours_failing = (datetime.now(timezone.utc) - datetime.fromisoformat(state["first_error_time"])).total_seconds() / 3600
            send_with_fallback(
                f"Failing for ~{hours_failing:.0f}h ({state['consecutive_errors']} consecutive errors). Latest: {error}",
                title="AMNH Monitor Error (Persistent)",
                tags="warning"
            )
            state["last_notified_time"] = now
    else:
        print(f"Transient error ({state['consecutive_errors']}/{ERROR_THRESHOLD} before notifying)")

    save_error_state(state)


def clear_error_state():
    """Reset error tracking on success. Notify recovery if we had alerted."""
    state = load_error_state()
    if state["consecutive_errors"] == 0:
        return  # Nothing to clear, no commit needed
    if state["last_notified_time"] and state["consecutive_errors"] >= ERROR_THRESHOLD:
        send_notification(
            f"Recovered after {state['consecutive_errors']} consecutive errors.",
            title="AMNH Monitor Recovered",
            priority="low",
            tags="white_check_mark"
        )
    print(f"Cleared {state['consecutive_errors']} consecutive errors")
    save_error_state({"consecutive_errors": 0, "first_error_time": None, "last_notified_time": None})


def main():
    print(f"Checking {URL}...")

    # Weekly heartbeat on Sundays around noon UTC
    if datetime.now(timezone.utc).weekday() == 6 and datetime.now(timezone.utc).hour == 12:
        send_notification("Weekly heartbeat: still monitoring, no 2027 yet.",
                         title="AMNH Monitor Active", priority="low", tags="heartbeat")

    try:
        content = get_page_content()
    except Exception as e:
        handle_error(str(e))
        return  # Exit cleanly so the workflow doesn't also fail and email you

    # Success - clear any error streak
    clear_error_state()

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
