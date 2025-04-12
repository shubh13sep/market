from config_loader import load_config
from navigator import paginate_and_scrape
from output_generator import save_to_json
from scraper import login_via_form, login_via_playwright

def main():
    url = "https://www.screener.in/full-text-search/?q=%22board+meeting%22+and+%22Qualified+Institutions+Placement%22+and+%22consider%22&type=announcements"
    output_file_path = "screener_qip.json"
    config = load_config("Configs/screener_config.yaml")

    if config.get("login", {}).get("enabled"):
        login_type = config["login"]["type"]
        if login_type == "form":
            if not login_via_form(config):
                print("Exiting due to failed login.")
                return
        elif login_type == "javascript":
            html, cookies = login_via_playwright(config, url)
        else:
            print("Unknown login type.")
            return

    results = paginate_and_scrape(config, url)
    save_to_json(results, output_file_path)

if __name__ == "__main__":
    main()