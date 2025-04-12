import os

from Scraper.ScreenerNavigation import ScreenerNavigation
import time


def scrape(content:str):
    from bs4 import BeautifulSoup

    # Sample HTML content (replace this with the actual HTML content)
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <!-- Head content omitted for brevity -->
      </head>
      <body class="light flex-column">
        <!-- Body content omitted for brevity -->
        <div class="margin-top-20 margin-bottom-36">
          <div>
            <a href="/company/517548/" class="font-weight-500 font-size-15" target="_blank">
              <i class="icon-link-ext"></i>
              <span class="hover-link ink-900">
                Starlite Components Ltd
              </span>
            </a>
          </div>

          <div class="font-size-17 font-weight-500">
            <a href="https://www.bseindia.com/stockinfo/AnnPdfOpen.aspx?Pname=b297b026-923c-449a-9972-d8205fedc45b.pdf" target="_blank">
              Monitoring Committee Meeting Outcome For Compliance Of Regulation 30 Of SEBI (LODR) Regulations, 2015 For Acceptance Of Deemed Resignation Of Existing Directors And Appointment Of New Board And Approval Of Reduction Of Share Capital.
            </a>
          </div>

          <div class="ink-700 font-size-16">
            Directors And Appointment <b>Of</b> New Board <b>Of</b> Directors And Approval <b>Of</b> Reduction <b>Of</b> Share Capital.

    Pursuant to <b>NCLT</b> Order dated March 14, 2024, the
          </div>

          <div class="margin-top-4 ink-700 font-size-14">

            Announcement -

            24 Jan 2025
          </div>
        </div>
        <!-- More content omitted for brevity -->
      </body>
    </html>
    """
    html_content = content
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find all the announcement blocks
    announcement_blocks = soup.find_all('div', class_='margin-top-20 margin-bottom-36')
    # Initialize a list to store the extracted data
    extracted_data = []

    # Loop through each announcement block and extract the required information
    for block in announcement_blocks:
        company_name = block.find('span', class_='hover-link ink-900').text.strip()
        title = block.find('div', class_='font-size-17 font-weight-500').text.strip()
        detail = block.find('div', class_='ink-700 font-size-16').text.strip()
        announcement_date = block.find('div', class_='margin-top-4 ink-700 font-size-14').text.strip().split('-')[
            -1].strip()
        announcement_url = block.find('div', class_='font-size-17 font-weight-500').find('a')['href']

        # Append the extracted data to the list
        extracted_data.append({
            'Company Name': company_name,
            'Title': title,
            'Detail': detail,
            'Announcement Date': announcement_date,
            'Announcement URL': announcement_url
        })

    # Print the extracted data
    for data in extracted_data:
         print(data)


    # Find the 'Next' button <a> tag containing "Next"
    if html_content.find("Next") == -1:
        print("🚫 No 'Next' button found on this page.")
        return [extracted_data, False]
    return [extracted_data, True]

def scrape_url(baseUrl, outputFile):
    # Open the file in append mode
    output_folder = "ScreenerOutput"
    file_name = os.path.join(output_folder, outputFile)
    with open(file_name, "a") as file:
        file.write("[ \n")
        # Iterate over pages (assuming there are 10 pages, adjust as needed)
        for page in range(1, 26):  # Change 11 to the total number of pages + 1
            # Construct the URL for the current page
            url = baseUrl + str(page)
            print("URL:" + url)
            # Access the dashboard and get the response
            response = screener.access_dashboard(url)

            # Scrape the response
            scraped_data = scrape(response)

            # Write the scraped data to the file
            for data in scraped_data[0]:
                file.write(str(data) + ", \n")  # Write each data entry as a new line

            # Print progress (optional)
            print(f"Page {page} scraped and data appended to {outputFile}")

            # Add a 5-second delay before the next call
            time.sleep(5)
            if(scraped_data[1] == False):
                break
        file.write("\n ]")

def append_pagenum(url):
    # append page
    return url + "&page="

# Initialize the ScreenerNavigation class
screener = ScreenerNavigation()
urlOutputMapping = {
# "https://www.screener.in/full-text-search/?q=%22proposal%22+And+%22buyback%22&type=announcements":"BuybackConsideration.json",
# "https://www.screener.in/full-text-search/?q=%22Buyback%22+AND+%22Board%22+AND+%22Outcome%22&type=announcements":"BuybackApproval.json",
# "https://www.screener.in/full-text-search/?q=%22Record+Date%22+And+%22buyback%22&type=announcements":"BuybackRecordDate.json",
# "https://www.screener.in/full-text-search/?q=-Newspaper+-%22Closure+of+Buy+Back%22+-%22Fixes+Record+Date%22+-%22Updates+on+Buy+back%22+-%22CHANGE+IN+RECORD+DATE%22+-%22Post+Buyback%22+-%22Board+Meeting+Outcome%22+-%22Board+Meeting+Intimation%22+%22Buyback%22+AND+%22Letter+Of+Offer%22&type=announcements":"BuybackLetterOfOffer.json",
# "https://www.screener.in/full-text-search/?q=-Newspaper+%22Public+Announcement%22+AND+%22Buyback%22&type=announcements":"BuybackPublicAnnouncement.json",
# "https://www.screener.in/full-text-search/?q=extinguishment+AND+Buyback&type=announcements":"BuybackExtinguishmentOfShares.json",
# "https://www.screener.in/full-text-search/?q=%22Special+resolution%22+And+%22buyback%22&type=announcements":"BuybackSpecialResolution.json",
# "https://www.screener.in/full-text-search/?q=%22Board+Meeting%22+AND+%22To+Consider%22+AND+%22PREFERENTIAL%22&type=announcements":"PreferentialAllotment-BoardConsideration.json",
# "https://www.screener.in/full-text-search/?q=%22Allotment%22+AND+%22Board+Meeting%22+AND+%22Preferential%22&type=announcements":"PreferentialAllotment-BoardApproval.json",
# "https://www.screener.in/full-text-search/?q=%22Voting+results%22+and+%22Scrutinizer+Report%22+and+%22preferential%22&type=announcements":"PreferentialAllotment-ShareholderApproval.json",
# "https://www.screener.in/full-text-search/?q=%22Board%22+And+%22allotment%22+and+%22outcome%22":"PreferentialAllotment-Allotment.json",
# "https://www.screener.in/full-text-search/?q=%22preferential%22+AND+%22Approval+For+Listing%22":"PreferentialAllotment-Listing.json",
# "https://www.screener.in/full-text-search/?q=%22Preferential+Allotment%22+AND+%22DEVIATION%22+AND+%22Funds%22":"PreferentialAllotment-DeviationFund.json",
# "https://www.screener.in/full-text-search/?q=%22split%22+AND+%22Intimation%22&type=announcements":"StockSplit.json",
# "https://www.screener.in/full-text-search/?q=-%22approved%22+-%22considered+and+recommended%22+%28%22Bonus+Issue%22+AND+%22Consider%22%29&type=announcements&page=3":"BonusIssue-Consider.json",
# "https://www.screener.in/full-text-search/?q=%22Board%22+AND+%22recommends%22+AND+%22Bonus+Issue%22&type=announcements":"BonusIssue-BoardApproval.json",
# "https://www.screener.in/full-text-search/?q=%22Bonus%22+and+%22record+date%22&type=announcements":"BonusIssue-RecordDate.json",
# "https://www.screener.in/full-text-search/?q=-%22record+date%22+%28%22Allotment%22+AND++%22Bonus%22%29&type=announcements":"BonusIIssue-Allotment.json",
# "https://www.screener.in/full-text-search/?q=%22consider%22+AND+%22Dividend%22+AND+%22Board%22&type=announcements":"DividendConsideration.json",
# "https://www.screener.in/full-text-search/?q=%22DIVIDEND%22+AND+%22RECORD+Date%22&type=announcements":"DividendRecordDate.json",
# "https://www.screener.in/full-text-search/?q=%22dividend+shall+be+paid%22&type=announcements":"DividendPaymentDate.json",
# "https://www.screener.in/full-text-search/?q=-%22Commissioner%22+-%22tax%22+-%22gst%22+%22order+received%22+or+%22award+of+order%22+or+%22Notification+of+Award%22+or+%22letter+of+intent%22+or+%22large+order%22+or++%22Order+for+Procurement%22+or+%22Awarding+of+order%22+or+%22bagged+an+order+%22+or+%22Letter+of+Award%22+or+%22repeat+order%22+or+%22additional+order%22+or+%22Contract+Award%22%29&type=announcements":"OrderWinsAndNewBusiness.json",
# "https://www.screener.in/full-text-search/?q=%22Capacity+Expansion%22+OR+%22Factory+Expansion%22+OR+%22Capital+Expenditure%22+OR+%22New+Facility+Setup%22+OR+%22Industrial+Growth+Plan%22+OR+%22Production+Capacity+Increase%22+OR+%22Manufacturing+Expansion%22+OR+%22Operational+Scaling%22+OR+%22Plant+Modernization%22+OR+%22Capacity+Augmentation%22+OR+%22Production+Facility+Expansion%22+OR+%22Industrial+Expansion+Plan%22+OR+%22Capital+Deployment%22+OR+%22Asset+Expansion%22+OR+%22Growth+Capex%22+OR+%22Greenfield+Investment%22+OR+%22Brownfield+Expansion%22+OR+%22New+Manufacturing+Unit%22+OR+%22Machinery+Procurement%22+OR+%22Production+Line+Upgrade%22+OR+%22Factory+Commissioning%22+OR+%22Supply+Chain+Expansion%22+OR+%22Operational+Capacity+Boost%22+OR+%22Increased+Throughput%22+OR+%22New+Manufacturing+Plant%22+OR+%22Production+Line+Addition%22+OR+%22Operational+Efficiency+Enhancement%22+OR+%22Automation+Investment%22+OR+%22Environmental+Clearance+for+Expansion%22+OR+%22Industrial+License+Approval%22+OR+%22Land+Acquisition+for+Expansion%22+OR+%22SEZ+%28Special+Economic+Zone%29+Approval%22+OR+%22MoU+for+Industrial+Development%22&type=announcements":"CapacityExpansionAndCapexPlans.json",
# "https://www.screener.in/full-text-search/?q=%22Board+Meeting%22+AND+%22Intimation%22+AND+%22financial+result%22":"ResultIntimation.json",
# "https://www.screener.in/full-text-search/?q=-Newspaper+%28%22Financial+Results+%22+or+%22Integrated+Filing%22%29&type=announcements":"ResultAnnouncement.json",
# "https://www.screener.in/full-text-search/?q=%22Financial+Results+%22+AND+Newspaper&type=announcements":"ResultNewspaperAnnouncement.json",
# "https://www.screener.in/full-text-search/?q=%22Investor+Meet%22+AND+Intimation&type=announcements":"InvestorMeet.json",
# "https://www.screener.in/full-text-search/?q=%28%22Business+Update+Call%22+or+%22Schedule+of+Earnings+Call+%22+or+%22Earnings+Conference+Call%22+or+%22Earnings+Call%22%29+-transcript+-recording&type=announcements":"ConferenceCall.json",
# "https://www.screener.in/full-text-search/?q=+transcript&type=announcements":"EarningCallTranscript.json",
# "https://www.screener.in/full-text-search/?q=%22Listing+of+Equity+Shares%22&type=announcements":"StockExchangeListings.json",
# "https://www.screener.in/full-text-search/?q=%22Joint+venture%22+Or+%22strategic+partnership%22+or+%22Business+tie-up%22&type=announcements":"JointVenturesAndPartnerships.json",
# "https://www.screener.in/full-text-search/?q=%22USFDA%22++or+%22Clinical+trial+results%22+or+%22Drug+application%22+or+%22Drug+Approval%22+&type=announcements":"SaleOrTransferOfAssets.json",
# "https://www.screener.in/full-text-search/?q=%22management+change%22+or+%22resignation%22+or+%22appointment%22+or+%22new+leadership%22+&type=announcements":"ManagementChange.json",
# "https://www.screener.in/full-text-search/?q=%22SAST%22+or+%22Substantial+Acquisition%22&type=announcements":"SASTNotification.json",
# "https://www.screener.in/full-text-search/?q=%22Public+Announcement%22+AND+%22Open+Offer%22&type=announcements":"OpenOffersAnnouncement.json",
# "https://www.screener.in/full-text-search/?q=disruption&type=announcements":"IncidentReports.json",
# "https://www.screener.in/full-text-search/?q=%22USFDA%22++or+%22Clinical+trial+results%22+or+%22Drug+application%22+or+%22Drug+Approval%22+&type=announcements":"USFDAApprovalsRejections.json",
# "https://www.screener.in/full-text-search/?q=earning+presentation&type=announcements":"InvestorPresentation.json",
# "https://www.screener.in/full-text-search/?q=-Calcutta+-Metropolitan+-Luxembourg+-Newspaper+-CIRP+%28%22Delisting%22+AND+%22Voluntary%22+AND+%22Proposal%22+AND+%22Intimation%22&type=announcements":"DelistingProposal.json",
# "https://www.screener.in/full-text-search/?q=-Calcutta+-Metropolitan+-Luxembourg+-Newspaper+-CIRP+%28%22Delisting%22+AND+%22Public+Announcement%22+AND+%22Detailed%22%29&type=announcements":"DelistingAnnouncement.json",
# "https://www.screener.in/full-text-search/?q=-Calcutta+-Metropolitan+-Luxembourg+-Newspaper+-CIRP+%28%22Delisting%22+AND+%22+Intimation%22+AND++%22Floor+Price%22%29&type=announcements":"DelistingFloorPriceIntimation.json",
# "https://www.screener.in/full-text-search/?q=-Calcutta+-Metropolitan+-Luxembourg+-Newspaper+-CIRP+%28%22Letter+Of+Offer%22+AND+%22Delisting%22%29&type=announcements":"DelistingLetterOfOffer.json",
# "https://www.screener.in/full-text-search/?q=-Calcutta+-Metropolitan+-Luxembourg+-Newspaper+-CIRP+%28%22Reverse+Book+Building%22+AND+%22Delisting%22+AND+%22Outcome%22%29&type=announcements":"Delisting-ReverseBookBuildingOutcome.json",
# "https://www.screener.in/full-text-search/?q=-Calcutta+-Metropolitan+-Luxembourg+-Newspaper+-CIRP+%28%22Post+Offer%22+AND+%22Delisting%22+AND+%22Public+Announcement%22%29&type=announcements":"Delisting-PostOffer.json",
# "https://www.screener.in/full-text-search/?q=%22Press+Release%22&type=announcements":"PressRelease.json",
# "https://www.screener.in/full-text-search/?q=recording+audio&type=announcements":"AudioRecording.json",
# "https://www.screener.in/full-text-search/?q=%22litigation%22+or+%22arbitration%22+or+%22legal+matter%22+or+%22legal+disputes%22+or+%22legal%22+or+%22litigations%22&type=announcements":"LegalAndDisputes.json",
# "https://www.screener.in/full-text-search/?q=-%22ESGS%22+%28%22ESG%22+or+%22Environmental%2C+Social%2C+Governance%22%29&type=announcements":"ESGInitiatives.json",
#"https://www.screener.in/full-text-search/?q=-Newspaper+%28%22demerger%22+and+%22scheme+of+arrangement%22%29&type=announcements":"DemergerAnnouncement.json",
# "https://www.screener.in/full-text-search/?q=-Newspaper+%28%22demerger%22+and+%22Order%22+and+%22NCLT%22%29&type=announcements": "DemergerNCLTApproval.json",
# "https://www.screener.in/full-text-search/?q=%22demerger%22+and+%22record+date%22&type=announcements":"DemergerRecordDate.json",
# "https://www.screener.in/full-text-search/?q=-Newspaper+-NCLT+-%22record+date%22+-%22scheme+of+arrangement%22+%28%22demerger%22%29&type=announcements":"DemergerOthers.json"
# "https://www.screener.in/full-text-search/?q=%22Board+Meeting%22+AND+%22consider%22+and+%22warrants%22+AND+%22fund%22+AND+%22Raise%22&type=announcements":"WarrantConsideration.json",
# "https://www.screener.in/full-text-search/?q=-conversion+-%22To+consider%22+%22warrant%22+and+%22allotment+of%22&type=announcements":"WarrantAllotment.json",
# "https://www.screener.in/full-text-search/?q=%22conversion+of+warrants%22&type=announcements":"WarrantConversion.json",
# "https://www.screener.in/full-text-search/?q=-conversion+-%22To+consider%22+-allotment+%22warrant%22&type=announcements":"WarrantOthers.json"
# "https://www.screener.in/full-text-search/?q=-warrant+-Proposal+%28%22right%22+and+%22amount%22%29&type=announcements":"RightApproved.json",
# "https://www.screener.in/full-text-search/?q=%22Record+Date%22+AND++%22Rights+Issue%22+And+%22Fixed%22&type=announcements":"RightRecordDate.json",
# "https://www.screener.in/full-text-search/?q=%22Right%22+AND+%22Letter+of+Offer%22&type=announcements":"RightLetterOfOffer.json",
# "https://www.screener.in/full-text-search/?q=-Obligations+%22Listing%22+AND+%22Of+Shares%22+AND+%22Rights%22&type=announcements":"RightsListingOfShares.json",
# "https://www.screener.in/full-text-search/?q=-%22Fund+Raise%22+-SAST+-%22considered+and+approved%22+-%22Letter+Of+Offer%22+-%22Record+date%22+-%22Change+in+Management%22-warrant+-%22Record+Date%22+-%22Raising+of+Funds%22+-%22Intimation+of+Right+issue%22+%22rights%22&type=announcements":"RightsOthers.json"
# "https://www.screener.in/full-text-search/?q=%22Board%22+AND+%22Fund+Raise%22+and+%22Right%22&type=announcements":"RightConsider1.json",
# "https://www.screener.in/full-text-search/?q=-%22Record+Date%22+%22Corporate+Action-Intimation+of+Right+issue%22&type=announcements":"RightConsider2.json"
#"https://www.screener.in/full-text-search/?q=%22open+offer%22+and+%22detailed+public+statement%22&type=announcements":"OpenOfferDPS.json"
#"https://www.screener.in/full-text-search/?q=%22open+offer%22+and+%22Letter+of+Offer%22&type=announcements":"OpenOfferLetterOfOffer.json",
#"https://www.screener.in/full-text-search/?q=%22open+offer%22+and+%22Submission+of+recommendations%22&type=announcements":"OpenOfferSubmissionOfRecommendations.json",
#"https://www.screener.in/full-text-search/?q=Divestment+or+%22sale+of+plants%22+or+%22business+unit+sale%22+or+%22sale+of+non-core%22+or+%22Ownership+Transfer%22+or+%22Asset+Disposal%22+or+%22asset+monetization%22&type=announcements": "SaleOrTransferOfAssets.json",
#"https://www.screener.in/full-text-search/?q=%22open+offer%22+and+%22outcome%22+and+%22Independent+Directors%22&type=announcements": "OpenOfferSubmissionOfRecommendations1.json",
#"https://www.screener.in/full-text-search/?q=%22open+offer%22+and+%22post+offer%22&type=announcements":"OpenOfferPostOffer.json",
#"https://www.screener.in/full-text-search/?q=-%22public+statement%22+-%22Public+Announcement%22+-%22Corrigendum+to+Public+Announcement%22+-%22Letter+of+Offer%22+-%22Submission+of+recommendations%22+-%22Post+Offer%22+%22open+offer%22&type=announcements":"OpenOfferOthers.json"
#"https://www.screener.in/full-text-search/?q=-Newspaper+Publication%22+%22buy+back%22+and+%22Post%22+and+%22Announcement%22&type=announcements":"BuybackPostAnnouncement1.json",
#"https://www.screener.in/full-text-search/?q=-Newspaper+Publication%22+and+%22Post%22+and+%22Announcement%22+and+%22buyback%22&type=announcements":"BuybackPostAnnouncement2.json"
# "https://www.screener.in/full-text-search/?q=-%22record+date%22+%22board+meeting%22+and+%22split%22+and+%22to+consider%22+&type=announcements": "StockSplitConsider.json",
# "https://www.screener.in/full-text-search/?q=%22split%22+AND+%22Intimation+of+Sub+division%22&type=announcements": "StockSplitApproval1.json",
# "https://www.screener.in/full-text-search/?q=-%22consider%22+-%22Intimation%22+%22split%22+AND+%22Approval%22&type=announcements": "StockSplitApproval2.json",
# "https://www.screener.in/full-text-search/?q=%22split%22+AND+%22Intimation+of+Sub+division%22&type=announcements": "StockSplitApproval1.json",
# "https://www.screener.in/full-text-search/?q=-%22consider%22+-%22Intimation%22+%22split%22+AND+%22Approval%22&type=announcements": "StockSplitApproval2.json",
# "https://www.screener.in/full-text-search/?q=%22record+date%22+and+%22Sub-+Division%22&type=announcements":"StockSplitRecordDate1.json",
# "https://www.screener.in/full-text-search/?q=%22Record+Date%22+and+%22split%22+&type=announcements": "StockSplitRecordDate2.json",
# "https://www.screener.in/full-text-search/?q=-%22Sub-Division%2FSplit+Of+Equity+Shares%22+-%22Investor+Presentation%22+-%22Outcome+Of+Board+Meeting%22+-%22Outcome+of+Sub+division%22+-%22consider%22+-%22Intimation%22+-%22record+date%22+-%22Approval%22+-%22recommended+sub-division%22+-%22approved%22+%22split%22&type=announcements": "StockSplitOthers.json"
"https://www.screener.in/full-text-search/?q=%22board+meeting%22+and+%22Qualified+Institutions+Placement%22+and+%22consider%22&type=announcements":"QIPConsideration1.json",
"https://www.screener.in/full-text-search/?q=-%22floor+price%22+%22Announcement+under+Regulation+30%22+and+%22Qualified+Institutional+Placement%22+and+%22PROPOSAL%22+&type=announcements":"QIPConsideration2.json",
"https://www.screener.in/full-text-search/?q=%22qip%22+and+%22floor+price%22&type=announcements":"QIPFloorPrice1.json",
"https://www.screener.in/full-text-search/?q=%22Qualified+Institutional+Placement%22+and+%22floor+price%22&type=announcements":"QIPFloorPrice2.json",
"https://www.screener.in/full-text-search/?q=%22floor+price%22+and+%22Announcement+under+Regulation+30%22+and+%22Qualified+Institutional+Placement%22+and+%22PROPOSAL%22&type=announcements":"QIPFloorPrice3.json",
"https://www.screener.in/full-text-search/?q=-%22floor+price%22+-%22Announcement+under+Regulation+30%22+++-%22PROPOSAL%22+-%22consider%22+%22Qualified+Institutional+Placement%22+-%22Raising+of+funds%22+-%22Fund+Raise%22+-%22Approval+for+raising+funds%22&type=announcements":"QIPOthers.json"


}




# Base URL without the page number
#base_url = "https://www.screener.in/full-text-search/?q=%22Outcome%22+and+%22Buyback%22&type=announcements"
#base_url = "https://www.screener.in/full-text-search/?q=%22SAST%22+or+%22Substantial+Acquisition%22&type=announcements"
#base_url = "https://www.screener.in/full-text-search/?q=demerger+or+merger&type=announcements"
#base_url = "https://www.screener.in/full-text-search/?q=-Calcutta+-Metropolitan+-Luxembourg+-Newspaper+-CIRP+Stock+Exchange+Delisting+Voluntary&type=announcements"
#base_url = "https://www.screener.in/full-text-search/?q=%22USFDA%22++or+%22Clinical+trial+results%22+or+%22Drug+application%22+or+%22Drug+Approval%22+&type=announcements"
#base_url = "https://www.screener.in/full-text-search/?q=Divestment+or+%22sale+of+plants%22+or+%22business+unit+sale%22+or+%22sale+of+non-core%22+or+%22Ownership+Transfer%22+or+%22Asset+Disposal%22+or+%22asset+monetization%22&type=announcements"
#base_url = "https://www.screener.in/full-text-search/?q=%22management+change%22+or+%22resignation%22+or+%22appointment%22+or+%22new+leadership%22+&type=announcements"
#base_url = "https://www.screener.in/full-text-search/?q=%22Board+Meeting%22+AND+%22To+Consider%22+AND+%22PREFERENTIAL%22&type=announcements"
#base_url = "https://www.screener.in/full-text-search/?q=warrant&type=announcements"




# File to store the scraped data
output_file = "scraped_warrant"
for  url in urlOutputMapping:
    filename = urlOutputMapping[url]
    scrapedData = scrape_url(append_pagenum(url), filename)


print("Scraping completed. Data saved to", output_file)