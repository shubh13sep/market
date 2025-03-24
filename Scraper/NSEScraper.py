import requests
import json
import time
from datetime import datetime, timedelta
from enum import Enum



class DataType(Enum):
    Announcement_Equity_Main_Board = "Announcement_Equity_Main_Board"
    Announcement_SME = "Announcement_SME"
    Announcement_Debt = "Announcement_Debt"
    Announcement_Mutual_Fund = "Announcement_Mutual_Fund"
    Announcement_REIT = "Announcement_REIT"
    Announcements_XBRL_CHANGE_IN_KMP = "Announcements_XBRL_CHANGE_IN_KMP"
    Announcements_XBRL_OUTCOME = "Announcements_XBRL_OUTCOME"
    Announcements_XBRL_RESTRUCTURING = "Announcements_XBRL_RESTRUCTURING"
    Announcements_XBRL_FRAUD = "Announcements_XBRL_FRAUD"
    Announcements_XBRL_CORPORATE_DEBT_RESTRUCTURING = "Announcements_XBRL_CORPORATE_DEBT_RESTRUCTURING"
    Announcements_XBRL_NOTICE_SHAREHOLDER_MEETING = "Announcements_XBRL_NOTICE_SHAREHOLDER_MEETING"
    Announcements_XBRL_FUND_RAISE = "Announcements_XBRL_FUND_RAISE"
    Announcements_XBRL_AGREEMENT_MOU = "Announcements_XBRL_AGREEMENT_MOU"
    Announcements_XBRL_ONE_TIME_SETTLEMENT = "Announcements_XBRL_ONE_TIME_SETTLEMENT"
    Announcements_XBRL_INSOLVENCY_RESOLUTION = "Announcements_XBRL_INSOLVENCY_RESOLUTION"

    Board_Meeting_EQUITY = "Board_Meeting_EQUITY"
    Board_Meeting_SME = "Board_Meeting_SME"

    Corporate_Action_EQUITY = "Corporate_Action_EQUITY"
    Corporate_Action_SME = "Corporate_Action_SME"

    Credit_Rating_Details = "Credit_Rating_Details"

    Event_Calendar_EQUITY = "Event_Calendar_EQUITY"
    Event_Calendar_SME = "Event_Calendar_SME"
    Preferential_Issue = "Preferential_Issue"
    Right_Issue = "Right_Issue"
    QIP_InPrinciple = "QIP_InPrinciple"
    QIP_Listing = "QIP_Listing"
    Insider_Trading = "Insider_Trading"

    Issue_Offer_Document_Equity = "Issue_Offer_Document_Equity"
    Issue_Offer_Document_SME = "Issue_Offer_Document_SME"

    Issue_Summary_Document_Buyback_Open_Market_Equity = "Issue_Summary_Document_Buyback_Open_Market_Equity"
    Issue_Summary_Document_Buyback_Tender_Equity = "Issue_Summary_Document_Buyback_Tender_Equity"
    Issue_Summary_Document_OpenOffer_Pre_Equity = "Issue_Summary_Document_OpenOffer_Pre_Equity"
    Issue_Summary_Document_OpenOffer_Post_Equity = "Issue_Summary_Document_OpenOffer_Post_Equity"
    Issue_Summary_Document_VoluntaryDelisting_Pre_Equity = "Issue_Summary_Document_VoluntaryDelisting_Pre_Equity"
    Issue_Summary_Document_VoluntaryDelisting_Post_Equity = "Issue_Summary_Document_VoluntaryDelisting_Post_Equity"

    Issue_Summary_Document_Buyback_Open_Market_SME = "Issue_Summary_Document_Buyback_Open_Market_SME"
    Issue_Summary_Document_Buyback_Tender_SME = "Issue_Summary_Document_Buyback_Tender_SME"
    Issue_Summary_Document_OpenOffer_Pre_SME = "Issue_Summary_Document_OpenOffer_Pre_SME"
    Issue_Summary_Document_OpenOffer_Post_SME = "Issue_Summary_Document_OpenOffer_Post_SME"
    Issue_Summary_Document_VoluntaryDelisting_Pre_SME = "Issue_Summary_Document_VoluntaryDelisting_Pre_SME"
    Issue_Summary_Document_VoluntaryDelisting_Post_SME = "Issue_Summary_Document_VoluntaryDelisting_Post_SME"

    SCHEME_OF_ARRANGEMENT = "SCHEME_OF_ARRANGEMENT"
    QUARTERLY_RESULT_EQUITY = "QUARTERLY_RESULT_EQUITY"
    QUARTERLY_RESULT_SME = "QUARTERLY_RESULT_SME"

    def getUrl(self, from_date: str, to_date:str) -> str:
        """ Returns the API endpoint URL for this data type and date. """
        if self == DataType.Announcement_Equity_Main_Board:
            return f"https://www.nseindia.com/api/corporate-announcements?index=equities&from_date={from_date}&to_date={to_date}"
        elif self == DataType.Announcement_SME:
            return f"https://www.nseindia.com/api/corporate-announcements?index=sme&from_date={from_date}&to_date={to_date}"
        elif self == DataType.Announcement_Debt:
            return f"https://www.nseindia.com/api/corporate-announcements?index=debt&from_date={from_date}&to_date={to_date}"
        elif self == DataType.Announcement_Mutual_Fund:
            return f"https://www.nseindia.com/api/corporate-announcements?index=mf&from_date={from_date}&to_date={to_date}"
        elif self == DataType.Announcement_REIT:
            return f"https://www.nseindia.com/api/corporate-announcements?index=invitsreits&from_date={from_date}&to_date={to_date}"

        elif self == DataType.Announcements_XBRL_CHANGE_IN_KMP:
            return f"https://www.nseindia.com/api/XBRL-announcements?index=equities&from_date={from_date}&to_date={to_date}&type=announcements"
        elif self == DataType.Announcements_XBRL_OUTCOME:
            return f"https://www.nseindia.com/api/XBRL-announcements?index=equities&from_date={from_date}&to_date={to_date}&type=outcome"
        elif self == DataType.Announcements_XBRL_RESTRUCTURING:
            return f"https://www.nseindia.com/api/XBRL-announcements?index=equities&from_date={from_date}&to_date={to_date}&type=Reg30"
        elif self == DataType.Announcements_XBRL_FRAUD:
            return f"https://www.nseindia.com/api/XBRL-announcements?index=equities&from_date={from_date}&to_date={to_date}&type=annFraud"
        elif self == DataType.Announcements_XBRL_CORPORATE_DEBT_RESTRUCTURING:
            return f"https://www.nseindia.com/api/XBRL-announcements?index=equities&from_date={from_date}&to_date={to_date}&type=cdr"
        elif self == DataType.Announcements_XBRL_NOTICE_SHAREHOLDER_MEETING:
            return f"https://www.nseindia.com/api/XBRL-announcements?index=equities&from_date={from_date}&to_date={to_date}&type=shm"
        elif self == DataType.Announcements_XBRL_FUND_RAISE:
            return f"https://www.nseindia.com/api/XBRL-announcements?index=equities&from_date={from_date}&to_date={to_date}&type=fundRaising"
        elif self == DataType.Announcements_XBRL_AGREEMENT_MOU:
            return f"https://www.nseindia.com/api/XBRL-announcements?index=equities&from_date={from_date}&to_date={to_date}&type=agr"
        elif self == DataType.Announcements_XBRL_ONE_TIME_SETTLEMENT:
            return f"https://www.nseindia.com/api/XBRL-announcements?index=equities&from_date={from_date}&to_date={to_date}&type=annOts"
        elif self == DataType.Announcements_XBRL_INSOLVENCY_RESOLUTION:
            return f"https://www.nseindia.com/api/XBRL-announcements?index=equities&from_date={from_date}&to_date={to_date}&type=CIRP"

        elif self == DataType.Board_Meeting_EQUITY:
            return f"https://www.nseindia.com/api/corporate-board-meetings?index=equities&from_date={from_date}&to_date={to_date}"
        elif self == DataType.Board_Meeting_SME:
            return f"https://www.nseindia.com/api/corporate-board-meetings?index=sme&from_date={from_date}&to_date={to_date}"


        elif self == DataType.Corporate_Action_EQUITY:
            return f"https://www.nseindia.com/api/corporates-corporateActions?index=equities&from_date={from_date}&to_date={to_date}"
        elif self == DataType.Corporate_Action_SME:
            return f"https://www.nseindia.com/api/corporates-corporateActions?index=sme&from_date={from_date}&to_date={to_date}"

        elif self == DataType.Credit_Rating_Details:
            return f"https://www.nseindia.com/api/corporate-credit-rating?index=&from_date={from_date}&to_date={to_date}"

        elif self == DataType.Event_Calendar_EQUITY:
            return f"https://www.nseindia.com/api/event-calendar?index=equities&from_date={from_date}&to_date={to_date}"
        elif self == DataType.Event_Calendar_SME:
            return f"https://www.nseindia.com/api/event-calendar?index=sme&from_date={from_date}&to_date={to_date}"

        elif self == DataType.Preferential_Issue:
            return f"https://www.nseindia.com/api/corporate-further-issues-pref?index=FIPREFIP&from_date={from_date}&to_date={to_date}"
        elif self == DataType.Right_Issue:
            return f"https://www.nseindia.com/api/corporate-further-issues-ri?index=FIRIIP&from_date={from_date}&to_date={to_date}"
        elif self == DataType.QIP_InPrinciple:
            return f"https://www.nseindia.com/api/corporate-further-issues-qip?index=FIQIPIP&from_date={from_date}&to_date={to_date}"
        elif self == DataType.QIP_Listing:
            return f"https://www.nseindia.com/api/corporate-further-issues-qip?index=FIQIPLS&from_date={from_date}&to_date={to_date}"
        elif self == DataType.Insider_Trading:
            return f"https://www.nseindia.com/api/corporates-pit?index=equities&from_date={from_date}&to_date={to_date}"

        elif self == DataType.Issue_Offer_Document_Equity:
            return f"https://www.nseindia.com/api/corporates/offerdocs?index=equities&from_date={from_date}&to_date={to_date}"
        elif self == DataType.Issue_Offer_Document_SME:
            return f"https://www.nseindia.com/api/corporates/offerdocs?index=sme&from_date={from_date}&to_date={to_date}"

        elif self == DataType.Issue_Summary_Document_Buyback_Open_Market_Equity:
            return f"https://www.nseindia.com/api/XBRL-announcements?index=equities&from_date={from_date}&to_date={to_date}&type=isdOpenBuyback"
        elif self == DataType.Issue_Summary_Document_Buyback_Tender_Equity:
            return f"https://www.nseindia.com/api/XBRL-announcements?index=equities&from_date={from_date}&to_date={to_date}&type=isdTenderBuyback"
        elif self == DataType.Issue_Summary_Document_OpenOffer_Pre_Equity:
            return f"https://www.nseindia.com/api/XBRL-announcements?index=equities&from_date={from_date}&to_date={to_date}&type=openOfferPre"
        elif self == DataType.Issue_Summary_Document_OpenOffer_Post_Equity:
            return f"https://www.nseindia.com/api/XBRL-announcements?index=equities&from_date={from_date}&to_date={to_date}&type=openOfferPost"
        elif self == DataType.Issue_Summary_Document_VoluntaryDelisting_Pre_Equity:
            return f"https://www.nseindia.com/api/XBRL-announcements?index=equities&from_date={from_date}&to_date={to_date}&type=isdPreVoluntary"
        elif self == DataType.Issue_Summary_Document_VoluntaryDelisting_Post_Equity:
            return f"https://www.nseindia.com/api/XBRL-announcements?index=equities&from_date={from_date}&to_date={to_date}&type=isdPostVoluntary"

        elif self == DataType.Issue_Summary_Document_Buyback_Open_Market_SME:
            return f"https://www.nseindia.com/api/XBRL-announcements?index=sme&from_date={from_date}&to_date={to_date}&type=isdOpenBuyback"
        elif self == DataType.Issue_Summary_Document_Buyback_Tender_SME:
            return f"https://www.nseindia.com/api/XBRL-announcements?index=sme&from_date={from_date}&to_date={to_date}&type=isdTenderBuyback"
        elif self == DataType.Issue_Summary_Document_OpenOffer_Pre_SME:
            return f"https://www.nseindia.com/api/XBRL-announcements?index=sme&from_date={from_date}&to_date={to_date}&type=openOfferPre"
        elif self == DataType.Issue_Summary_Document_OpenOffer_Post_SME:
            return f"https://www.nseindia.com/api/XBRL-announcements?index=sme&from_date={from_date}&to_date={to_date}&type=openOfferPost"
        elif self == DataType.Issue_Summary_Document_VoluntaryDelisting_Pre_SME:
            return f"https://www.nseindia.com/api/XBRL-announcements?index=sme&from_date={from_date}&to_date={to_date}&type=isdPreVoluntary"
        elif self == DataType.Issue_Summary_Document_VoluntaryDelisting_Post_SME:
            return f"https://www.nseindia.com/api/XBRL-announcements?index=sme&from_date={from_date}&to_date={to_date}&type=isdPostVoluntary"
        elif self == DataType.SCHEME_OF_ARRANGEMENT:
            return f"https://www.nseindia.com/api/corporates/offerdocs/arrangementscheme?index=equities&from_date={from_date}&to_date={to_date}"
        elif self == DataType.QUARTERLY_RESULT_EQUITY:
            return f"https://www.nseindia.com/api/corporates-financial-results?index=equities&from_date={from_date}&to_date={to_date}&period=Quarterly"
        elif self == DataType.QUARTERLY_RESULT_SME:
            return f"https://www.nseindia.com/api/corporates-financial-results?index=sme&from_date={from_date}&to_date={to_date}&period=Half-Yearly"

        else:
            raise ValueError("Invalid DataType provided.")

    def getOutputFileName(self) -> str:
        """ Returns the output filename for this data type. """
        return f"{self.value.replace(' ', '_').lower()}_output.json"


def fetch_nse_data(data_type: DataType, start_date, end_date):
    """
    Fetches NSE corporate announcements for a given date.

    Parameters:
    date (str): Date in 'YYYY-MM-DD' format.

    Returns:
    list: List of announcements if successful, else an empty list.
    """

    # API Endpoint
    url = data_type.getUrl(start_date, end_date)
    # Headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
        "DNT": "1",  # Do Not Track request
        "Connection": "keep-alive"
    }

    # # Start a session
    session = requests.Session()
    session.headers.update(headers)

    # Step 1: Get NSE home page to set cookies
    home_url = "https://www.nseindia.com/companies-listing/corporate-filings-financial-results"
    retry_request(session, home_url)
    # session.get(home_url, timeout=5)  # Helps bypass security

    # Step 2: Fetch data from API
    #response = session.get(url, timeout=10)

    # Check response status
    session.headers.update(headers)
    response = retry_request(session, url)
    if response.status_code == 200:
        data = response.json()
        # Handle different response formats
        if isinstance(data, list):
            return data  # Return list directly
        elif isinstance(data, dict):
            return data.get("data", [])  # Extract 'data' from dictionary

        return []  # Return empty list if format is unknown
    else:
        print(f"Error {response.status_code} for date {start_date} to {end_date}: {response.text}")
        return []


def save_data(data, current_date, filename):
    """
    Saves the data to a JSON file.

    Parameters:
    data (list): List of announcements.
    filename (str): Name of the JSON file.
    """
    try:
        # Ensure data is a list
        if not isinstance(data, list):
            print(f"❌ Data is not a list! Received: {type(data)}")
            return

        # Handle empty data case
        if not data:
            print("⚠️ No new data to save.")
            return

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


        print(f"✅ Saved {len(data)} records for {current_date}")

    except Exception as e:
        print(f"❌ Error saving data: {e}")


def scrape_data(data_type: DataType, start_date, end_date, batch_size):
    """
    Fetches NSE announcements between start_date and end_date.

    Args:
        start_date (str): Start date in "YYYY-MM-DD" format.
        end_date (str): End date in "YYYY-MM-DD" format.
        :param batch_size:
        :param end_date:
        :param start_date:
        :param data_type:
    """

    # Convert string dates to datetime objects
    start_date = datetime.strptime(start_date, "%d-%m-%Y")
    end_date = datetime.strptime(end_date, "%d-%m-%Y")
    output_file = data_type.getOutputFileName()

    # Ensure start_date is not after end_date
    if start_date > end_date:
        print("❌ Error: Start date cannot be after end date.")
        return

    # Iterate over the date range
    current_date = start_date
    while current_date <= end_date:

        batch_start_date = current_date
        batch_end_date = batch_start_date + timedelta(days=batch_size)

        today = datetime.today()

        if batch_end_date > today:
            print(
                f"⚠️ Warning: End date {batch_end_date.strftime('%d-%m-%Y')} is in the future. Adjusting to today's date: {today.strftime('%d-%m-%Y')}.")
            batch_end_date = today

        formatted_batch_start_date = current_date.strftime("%d-%m-%Y")
        formatted_batch_end_date = batch_end_date.strftime("%d-%m-%Y")
        print(f"📅 Fetching data for {formatted_batch_start_date} to {formatted_batch_end_date}...")

        # Fetch NSE announcements for the current date
        announcements = fetch_nse_data(data_type, formatted_batch_start_date, formatted_batch_end_date)


        # Save data if announcements exist
        if announcements:
            save_data(announcements, current_date, output_file)

        # Wait 10 seconds before the next request (to avoid rate limiting)
        time.sleep(1)

        # Move to the next batch day
        current_date = batch_end_date


def retry_request(session, url, max_retries=5, timeout=60, backoff_factor=5):
    """Retries an HTTP GET request with exponential backoff."""

    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=timeout)
            print(response.status_code)
            print(str(response.text))

            if response.status_code == 200:
                return response  # Successful response

            print(f"⚠️ Attempt {attempt + 1} failed: HTTP {response.status_code}")

        except requests.exceptions.Timeout:
            print(f"⏳ Timeout on attempt {attempt + 1}, retrying...")
        except requests.exceptions.RequestException as e:
            print(f"🚨 Request error: {e}")

        # Exponential backoff before retrying
        time.sleep(backoff_factor * (attempt + 1))

    print(f"❌ Failed to fetch data after {max_retries} retries.")
    return None

# Start scraping
#scrape_data(DataType.Announcement_SME,"01-01-2010", "04-02-2025")
#scrape_data(DataType.Announcement_Debt,"01-01-2010", "04-02-2025", 100)
#scrape_data(DataType.Announcement_REIT,"01-01-2010", "04-02-2025", 200)
#scrape_data(DataType.Announcement_Mutual_Fund,""01-01-2010", "04-02-2025", 300)
#scrape_data(DataType.Announcements_XBRL_CHANGE_IN_KMP,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Announcements_XBRL_OUTCOME,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Announcements_XBRL_RESTRUCTURING,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Announcements_XBRL_FRAUD,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Announcements_XBRL_CORPORATE_DEBT_RESTRUCTURING,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Announcements_XBRL_NOTICE_SHAREHOLDER_MEETING,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Announcements_XBRL_FUND_RAISE,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Announcements_XBRL_AGREEMENT_MOU,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Announcements_XBRL_ONE_TIME_SETTLEMENT,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Announcements_XBRL_INSOLVENCY_RESOLUTION,"01-01-2010", "04-02-2025", 300)



# scrape_data(DataType.Board_Meeting_EQUITY,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Board_Meeting_SME,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Corporate_Action_EQUITY,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Corporate_Action_SME,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Credit_Rating_Details,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Event_Calendar_EQUITY,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Event_Calendar_SME,"01-01-2010", "04-02-2025", 300)
#scrape_data(DataType.Preferential_Issue,"01-01-2010", "04-02-2025", 300)
#scrape_data(DataType.Right_Issue,"01-01-2010", "04-02-2025", 300)
#scrape_data(DataType.Insider_Trading,"01-01-2010", "04-02-2025", 300)
#scrape_data(DataType.Issue_Offer_Document_Equity,"01-01-2010", "04-02-2025", 300)
#scrape_data(DataType.Issue_Offer_Document_SME,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Issue_Summary_Document_Buyback_Open_Market_Equity,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Issue_Summary_Document_Buyback_Tender_Equity,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Issue_Summary_Document_OpenOffer_Pre_Equity,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Issue_Summary_Document_OpenOffer_Post_Equity,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Issue_Summary_Document_VoluntaryDelisting_Pre_Equity,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Issue_Summary_Document_VoluntaryDelisting_Post_Equity,"01-01-2010", "04-02-2025", 300)
#
# scrape_data(DataType.Issue_Summary_Document_Buyback_Open_Market_SME,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Issue_Summary_Document_Buyback_Tender_SME,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Issue_Summary_Document_OpenOffer_Pre_SME,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Issue_Summary_Document_OpenOffer_Post_SME,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Issue_Summary_Document_VoluntaryDelisting_Pre_SME,"01-01-2010", "04-02-2025", 300)
# scrape_data(DataType.Issue_Summary_Document_VoluntaryDelisting_Post_SME,"01-01-2010", "04-02-2025", 300)
#scrape_data(DataType.QIP_InPrinciple,"01-01-2010", "04-02-2025", 300)
#scrape_data(DataType.QIP_Listing, "01-01-2010", "04-02-2025", 300)
#scrape_data(DataType.SCHEME_OF_ARRANGEMENT, "01-01-2010", "04-02-2025", 300)
scrape_data(DataType.QUARTERLY_RESULT_EQUITY, "01-01-2007", "22-03-2025", 300)
scrape_data(DataType.QUARTERLY_RESULT_SME, "01-01-2007", "22-03-2025", 300)




