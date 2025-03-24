import requests

class ScreenerNavigation:
    def __init__(self):
        # Headers
        self.headers = {
            "Referer": "https://www.screener.in/login/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://www.screener.in",
        }

        # Start a session
        self.session = requests.Session()

        # URLs
        login_url = "https://www.screener.in/login/"
        dashboard_url = "https://www.screener.in/dash/"

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
            "password": "Sammed@55",  # Replace with your Screener password
            "csrfmiddlewaretoken": csrf_token,
        }

        # Step 3: Login Request
        response = self.session.post(login_url, data=payload, headers=self.headers)

        # Debugging the Response
        print("Response Status Code:", response.status_code)
        #print("Response Text:", response.text)
        #print("Response Cookies:", self.session.cookies)

        # Step 4: Check for Login Success
        if (response.status_code == 302 or response.status_code == 200) and "sessionid" in self.session.cookies:
            print("Login successful!")
        else:
            print("Login failed. Check response text for more details." + str(response))

    def access_dashboard(self, url):
        """Access the authenticated dashboard page."""
        response = self.session.get(url, headers=self.headers)

        if response.status_code == 200:
            print("Url content retrieved successfully!")
            #print("Response Text:", response.text)
            return response.text
        else:
            print(f"Failed to access dashboard. Status code: {response.status_code}")
            return None
if __name__ == "__main__":
    screener = ScreenerNavigation()

