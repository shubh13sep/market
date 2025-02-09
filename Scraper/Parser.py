import json

file = open("StockScanJson.txt", "r")
lines = file.readlines()

for line in lines:
    js = json.loads(line)

    i = 1

    while(i<len(js['table'])):
        row = js['table'][i]
        i = i+1
        industry = row[6]
        name = row[0]
        bseCode = row[2]
        nseCode = row[1]

        print(str(industry) + "," + str(name)+ "," + str(bseCode) + "," + str(nseCode))





