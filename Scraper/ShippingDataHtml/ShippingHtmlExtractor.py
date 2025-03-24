import os
from bs4 import BeautifulSoup
import csv

# Folder containing input HTML files
input_folder = "Inputs"
output_file = "output.csv"

# Initialize data storage
all_data = []
header_written = False

# Loop through all HTML files in the inputs folder
for filename in os.listdir(input_folder):
    if filename.endswith(".htm"):  # Process only HTML files
        file_path = os.path.join(input_folder, filename)

        # Read HTML file
        with open(file_path, "r", encoding="utf-8") as file:
            html = file.read()

        # Parse HTML
        soup = BeautifulSoup(html, "html.parser")

        # Extract table headers (quarters)
        quarters = [th.text for th in soup.select(".dx-pivotgrid-horizontal-headers td span")]

        # Extract row headers (shippers)
        shippers = [td.text for td in soup.select(".dx-pivotgrid-vertical-headers td span")]

        # Extract data cells
        data_rows = soup.select(".dx-pivotgrid-area-data tbody tr")
        data = [[td.text for td in row.find_all("td")] for row in data_rows]

        # Combine shipper names with their corresponding data
        for shipper, row_data in zip(shippers, data):
            all_data.append([filename, shipper] + row_data)

        # Write headers only once (first file)
        if not header_written:
            all_headers = ["Filename", "Shipper"] + quarters
            all_data.insert(0, all_headers)
            header_written = True

# Write to single CSV file
with open(output_file, "w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerows(all_data)

print(f"CSV file '{output_file}' created successfully!")