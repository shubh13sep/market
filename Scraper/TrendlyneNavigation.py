import time

import requests

class TrendlyneNavigation:
    def __init__(self):
        # Headers
        self.headers = {
            "Referer": "https://trendlyne.com/features/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://www.screener.in",
        }

        # Start a session
        self.session = requests.Session()

        # URLs
        login_url = "https://trendlyne.com/accounts/login/"
        dashboard_url = "https://trendlyne.com/discover/"

        # Step 1: Get CSRF Token
        login_page = self.session.get(login_url, headers=self.headers)
        csrf_token = self.session.cookies.get("csrftoken")
        if csrf_token:
            print(f"CSRF token retrieved: {csrf_token}")
        else:
            print("Failed to retrieve CSRF token.")
            exit()

        # Step 2: Prepare Payload
        payload = {
            "username": "shubhamsethi@outlook.com",  # Replace with your Screener username
            "password": "Shub123$",  # Replace with your Trendlyne password
            "csrfmiddlewaretoken": csrf_token,
        }

        # Step 3: Login Request
        response = self.session.post(login_url, data=payload, headers=self.headers)

        # Debugging the Response
        print("Response Status Code:", response.status_code)
        #print("Response Text:", response.text)
        #print("Response Cookies:", self.session.cookies)

        # Step 4: Check for Login Success
        if (response.status_code == 302 or response.status_code == 200):
            print("Login successful!")
        else:
            print("Login failed. Check response text for more details." + str(response))
            print(response.text)

    def access_dashboard(self, url, max_retries=5, base_delay=2):
        """Access the authenticated dashboard page."""
        headers = {
            "Referer": "https://trendlyne.com/features/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "X-Requested-With": "XMLHttpRequest",
            "Accept-Language": "en-US,en;q=0.9,en-IN;q=0.8",
            "Content-Type": "application/x-www-form-urlencoded",
            "DNT": "1"
        }

        attempt = 0
        while attempt < max_retries:
            response = self.session.get(url, headers=headers)
            if response.status_code == 200:
                return response

            wait_time = base_delay * (2 ** attempt)
            print(
                f"Attempt {attempt + 1} failed. Status code: {response.status_code}. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            attempt += 1

        print("Failed to access dashboard after multiple attempts.")
        return None
if __name__ == "__main__":
    trendlyne = TrendlyneNavigation()

