import requests
import json
import time
from datetime import datetime, timedelta


def fetch_nse_announcements(date):
    """
    Fetches NSE corporate announcements for a given date.

    Parameters:
    date (str): Date in 'YYYY-MM-DD' format.

    Returns:
    list: List of announcements if successful, else an empty list.
    """
    # Convert date to DD-MM-YYYY format for the API
    formatted_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y")

    # API Endpoint
    url = f"https://www.nseindia.com/api/corporate-announcements?index=equities&from_date={formatted_date}&to_date={formatted_date}"

    # Headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
        "DNT": "1",  # Do Not Track request
        "Connection": "keep-alive"
    }

    # Start a session
    session = requests.Session()
    session.headers.update(headers)

    # Step 1: Get NSE home page to set cookies
    home_url = "https://www.nseindia.com"
    session.get(home_url, timeout=5)  # Helps bypass security

    # Step 2: Fetch data from API
    response = session.get(url, timeout=10)

    # Check response status
    if response.status_code == 200:
        data = response.json()

        # Handle different response formats
        if isinstance(data, list):
            return data  # Return list directly
        elif isinstance(data, dict):
            return data.get("data", [])  # Extract 'data' from dictionary

        return []  # Return empty list if format is unknown
    else:
        print(f"Error {response.status_code} for date {date}: {response.text}")
        return []


def save_data(data, filename="nse_announcements.json"):
    """
    Saves the data to a JSON file.

    Parameters:
    data (list): List of announcements.
    filename (str): Name of the JSON file.
    """
    try:
        # Load existing data if file exists
        try:
            with open(filename, "r") as file:
                existing_data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            existing_data = []

        # Append new data
        existing_data.extend(data)

        # Save back to file
        with open(filename, "w") as file:
            json.dump(existing_data, file, indent=4)

        print(f"✅ Saved {len(data)} records for {data[0]['bcastDate']}") if data else print("No new data.")
    except Exception as e:
        print(f"Error saving data: {e}")


def scrape_last_year():
    """
    Iterates over the last 365 days and saves announcements to a file.
    """
    today = datetime.today()
    one_year_ago = today - timedelta(days=365)

    # Iterate over each date in the last year
    for i in range(366):  # 365 days + today's data
        date = (one_year_ago + timedelta(days=i)).strftime("%Y-%m-%d")
        print(f"📅 Fetching data for {date}...")

        announcements = fetch_nse_announcements(date)

        if announcements:
            save_data(announcements)

        # Wait 10 seconds before the next request (to avoid rate limiting)
        time.sleep(10)


# Start scraping
scrape_last_year()