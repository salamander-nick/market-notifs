import json
import os
from datetime import datetime
import pytz

import yfinance as yf
import smtplib
from email.message import EmailMessage

# =====================
# CONFIG
# =====================
THRESHOLD_PCT = -5.0
TIMEZONE = pytz.timezone("US/Eastern")

EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_TO = os.environ.get("EMAIL_TO")

# =====================
# HELPERS
# =====================
def is_market_hours():
    now = datetime.now(TIMEZONE)

    if now.weekday() >= 5:  # Saturday/Sunday
        return False

    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)

    return market_open <= now <= market_close


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def send_email(subject, body):
    msg = EmailMessage()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)


# =====================
# MAIN LOGIC
# =====================
def main():
    if not is_market_hours():
        print("Outside market hours. Exiting.")
        # return

    watchlist = load_json("watchlist.json", {})
    alert_state = load_json("alert_state.json", {})

    today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")

    for ticker in watchlist.keys():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2d")

            if len(hist) < 2:
                print(f"Not enough data for {ticker}")
                continue

            prev_close = hist["Close"].iloc[-2]
            current_price = hist["Close"].iloc[-1]

            pct_change = (current_price - prev_close) / prev_close * 100

            print(f"{ticker}: {pct_change:.2f}%")

            already_alerted = (
                ticker in alert_state and alert_state[ticker] == today
            )

            if pct_change <= THRESHOLD_PCT and not already_alerted:
                message = (
                    f"📉 STOCK ALERT\n\n"
                    f"{ticker} is down {pct_change:.2f}% today\n"
                    f"Prev close: ${prev_close:.2f}\n"
                    f"Current: ${current_price:.2f}\n\n"
                    f"Potential buy opportunity 👀"
                )

                send_email(
                    subject=f"Stock Alert: {ticker} down {pct_change:.2f}%",
                    body=message
                )
                alert_state[ticker] = today

        except Exception as e:
            print(f"Error processing {ticker}: {e}")

    save_json("alert_state.json", alert_state)


if __name__ == "__main__":
    main()

