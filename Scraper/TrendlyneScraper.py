import os

import requests
import time
import traceback
from Scraper.TrendlyneNavigation import TrendlyneNavigation


def fetch_trendlyne_data(start_date, end_date, navigator, search_phrase="", post_category="" ):
    """
    Fetches paginated data from Trendlyne based on the given date range.

    Args:
        start_date (str): Start date in YYYY-MM-DD format.
        end_date (str): End date in YYYY-MM-DD format.

    Returns:
        list: A list of all records fetched across pages.
    """

    # Base URL with placeholders for dates and page number
    BASE_URL = "https://trendlyne.com/discover/?search_phrase={}&start_date={}&end_date={}&qstime=1741719083&ctype=all&groupCode=None&page_no={}"
    all_records = []
    page = 1

    while True:
        url = BASE_URL.format(search_phrase, start_date, end_date, page)
        if post_category != "":
            url = url + "&post_category=" + post_category

        print(f"Fetching postcategory {search_phrase} page {page}: {url} startDate: {start_date} endDate:{end_date}")

        response = navigator.access_dashboard(url)
        #print(response.text)
        #print(response.json())
        if response.status_code != 200:
            #print(f"Failed to fetch page {page}, status code: {response.status_code}")
            break

        try:
            json_data = response.json()
            output_records = json_data.get("body").get("data")
            #print(output_records)
            if len(output_records) == 0:
                #print("No more data found. Stopping.")
                break

            all_records.extend(output_records)

            #print(f"Fetched {len(output_records)} records from page {page}")

            # If records are less than 10, it's the last page
            if len(output_records) < 10:
                #print("Last page reached.")
                break

            page += 1  # Move to the next page
            time.sleep(1)  # Respectful delay to avoid rate limiting

        except Exception as e:
            print(f"Error processing page {page}: {e}")
            traceback.print_exc()
            break

    print(f"Total records fetched for post_category: {search_phrase} = {len(all_records)}")
    return all_records


from datetime import datetime, timedelta


def generate_date_ranges(start_date, end_date, max_diff=5):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    date_ranges = []
    current_start = start

    while current_start <= end:
        current_end = min(current_start + timedelta(days=max_diff), end)
        date_ranges.append((current_start.strftime("%Y-%m-%d"), current_end.strftime("%Y-%m-%d")))
        current_start = current_end + timedelta(days=1)

    return date_ranges




# Initialize the ScreenerNavigation class
trendlyne = TrendlyneNavigation()

# Example usage
start_date = "2024-01-01"
end_date = "2025-03-12"

all_records = []
date_ranges = generate_date_ranges(start_date, end_date)
print(date_ranges)
# If you want to save the records as a JSON file
import json


# Ensure the directory exists
output_folder = "TrendlyneOutput"
os.makedirs(output_folder, exist_ok=True)

inputs = []
#0: name, 1: search_phrase 2:post_category
#Result
#inputs.append(["resultIntimation", "%22Board+Meeting+Intimation%22+and+%22financial+result%22"])
inputs.append(["investorPPT", "", "102"])

for input in inputs:
    print("starting for post_category" + str(input[0]))
    for range in date_ranges:
        #print(f"fetching category {post_category} startdate:{range[0]} endDate:{range[1]}")
        records = fetch_trendlyne_data(range[0], range[1], trendlyne, input[1], input[2], )
        all_records.extend(records)
    file_name = os.path.join(output_folder, f"trendlyne_data_{input[0]}.json")
    with open(file_name, "w", encoding="utf-8") as file:
        json.dump(all_records, file, indent=4)


print(len(all_records))
print("Data saved to trendlyne_data.json")



