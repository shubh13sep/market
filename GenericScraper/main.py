from config_loader import load_config
from navigator import paginate_and_scrape
from output_generator import save_to_json
from scraper import login_via_form, login_via_playwright

def main():
    config = load_config("config.yaml")

    if config.get("login", {}).get("enabled"):
        login_type = config["login"]["type"]
        if login_type == "form":
            if not login_via_form(config):
                print("Exiting due to failed login.")
                return
        elif login_type == "javascript":
            html, cookies = login_via_playwright(config)
        else:
            print("Unknown login type.")
            return

    results = paginate_and_scrape(config)
    save_to_json(results)

if __name__ == "__main__":
    main()