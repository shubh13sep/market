import os
import json
import re
from bs4 import BeautifulSoup

# Directory containing all the HTML files
folder_path = "export"

# Dictionary to store final consolidated data
final_data = {}

# Month name order for sorting
month_order = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
}

# Iterate through all files in the folder
for filename in os.listdir(folder_path):
    if filename.endswith(".html"):  # Process only HTML files
        # Extract the year using regex (first 4 digits in the filename)
        match = re.match(r"(\d{4})", filename)
        if not match:
            print(f"Skipping {filename}: Unable to extract year")
            continue
        year = match.group(1)  # Extracted year (e.g., "2024" from "2024(23).html")

        file_path = os.path.join(folder_path, filename)

        # Read and parse HTML
        with open(file_path, "r", encoding="utf-8") as file:
            soup = BeautifulSoup(file, "html.parser")

        # Locate the pivot table
        table = soup.find("table", class_="dx-pivotgrid-border")

        if not table:
            print(f"Skipping {filename}: No table found")
            continue

        # Extract column headers from <thead>
        thead = table.find("thead", class_="dx-pivotgrid-horizontal-headers")
        headers = [th.get_text(strip=True) for th in thead.find_all("span")] if thead else []

        # Filter out non-month headers (like "Grand Total")
        valid_headers = [h for h in headers if h in month_order]

        # Extract row headers (company names)
        row_tbody = table.find("tbody", class_="dx-pivotgrid-vertical-headers")
        row_headers = [row.find("span").get_text(strip=True) for row in row_tbody.find_all("tr")] if row_tbody else []

        # Extract numerical data from the main data <tbody>
        data_tbody = table.find_all("tbody")[-1]  # Last <tbody> contains numerical values
        data_rows = data_tbody.find_all("tr") if data_tbody else []

        # Process each company's data
        for i, row in enumerate(data_rows):
            values = [td.get_text(strip=True) for td in row.find_all("td")]

            # Ensure row_headers and values have matching indices
            if i >= len(row_headers):
                print(f"Skipping row {i} in {filename}: No matching company name")
                continue

            company_name = row_headers[i]

            # If company doesn't exist in final data, initialize it
            if company_name not in final_data:
                final_data[company_name] = {}

            # Adjust row length if mismatched
            while len(values) < len(valid_headers):
                values.append("--")  # Fill missing values with "--"

            # Add data for this year by modifying month headers
            for j, header in enumerate(valid_headers):
                month_year = f"{header}_{year}"  # E.g., "January_2024"
                final_data[company_name][month_year] = values[j]  # Store value under month-year key

# ** Sorting logic to ensure months appear in correct order **

# Function to sort month-year keys correctly
def sort_months(data_dict):
    def month_key(item):
        month, year = item.split("_")
        return (int(year), month_order[month])  # Sort by year first, then month

    # Keep only valid months and sort them
    sorted_keys = sorted([k for k in data_dict.keys() if "_" in k], key=month_key)
    return {key: data_dict[key] for key in sorted_keys}

# Apply sorting to each company
final_data_sorted = {company: sort_months(data) for company, data in final_data.items()}

# Save the final sorted JSON output
output_file = "shipping_monthly_output.json"
with open(output_file, "w", encoding="utf-8") as json_file:
    json.dump(final_data_sorted, json_file, indent=4)

print(f"Final JSON saved as {output_file}")