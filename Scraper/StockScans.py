import json
import time

import requests

def request(url_name, origin_name, referer_name, cookie_name, scan_name) :
    # Define the URL

    # Define the headers
    headers = {
        "accept": "application/json",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en;q=0.9,en-IN;q=0.8",
        "content-type": "application/json",
        "cookie": cookie_name,
        "dnt": "1",
        "origin": origin_name,
        "referer": referer_name,
        "sec-ch-ua": '"Chromium";v="130", "Microsoft Edge";v="130", "Not?A_Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
        "version": "3.1",
    }

    # Define the payload
    payload = {
        "ratiosType": "Default",
        "timePeriod": "Latest",
        "scan": {
            "scanName": scan_name,
            "scanDescription": scan_name,
            "industry": [scan_name],
            "index": [],
            "sector": [],
            "tags": [],
            "filters": [
                {
                    "left": "Market Capitalization",
                    "right": "500",
                    "sign": ">="
                }
            ]
        },
        "watchlists": {},
        "type": "saved",
        "sortBy": "Market Capitalization",
        "order": -1,
        "offset": 0,
        "limit": 50
    }

    # Make the POST request
    response = requests.post(url_name, headers=headers, json=payload)

    # Print the response
    print("Status Code:", response.status_code)
    print("Response JSON:", response.json())
    return response

url = "https://www.stockscans.in/api/scans/scan-companies"
origin = "https://www.stockscans.in"
referer = "https://www.stockscans.in/stock-scans/new?industry=Realty%20-%20Construction%20&amp;%20Contracting&filters=Market%20Capitalization%3E=500&tags="
cookie = "authtoken=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE3MzkyMzY4NzMsInZlcnNpb24iOiIwLjAiLCJfaWQiOiI2Nzg1NWM0NmFhZTIzNmYxNzA3MDMwOTYifQ.xpd9asQro5MUV2dVBufj-7B8CPRaUmPhmn1m4RhpN_E"


#read file
file = open("StockScanURL.txt", "r")
write_file = open("StockScanJson.txt", "w")
for line in file.readlines():
    line = line.replace('\n','')
    print(line)
    if line is not None:
        # Get the industry name
        industry = line.split("=",2)[1].replace("%20", " ").replace("&amp;", "&").replace('\n','')
        print(industry)
        response = request(url, origin, line, cookie, industry)

        write_file.write(str(response.json()))
        write_file.write('\n')
        time.sleep(0.5)

file.close()

