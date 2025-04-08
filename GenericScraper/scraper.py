import requests
import os
import json
from lxml import etree
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

COOKIE_FILE = "session_cookies.json"
session = requests.Session()

def save_cookies():
    with open(COOKIE_FILE, "w") as f:
        cookies = session.cookies.get_dict()
        json.dump(cookies, f)

def load_cookies():
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r") as f:
            cookies = json.load(f)
            session.cookies.update(cookies)

def login_via_form(config):
    login_url = config["login"]["url"]
    username = config["login"]["credentials"]["username"]
    password = config["login"]["credentials"]["password"]
    csrf_field = config["login"].get("csrf_field", "csrfmiddlewaretoken")  # default for Django apps
    csrf_source = config["login"].get("csrf_source", "html")  # html / cookie / header

    # Fetch CSRF token first
    pre_response = session.get(login_url)
    soup = BeautifulSoup(pre_response.text, "html.parser")

    csrf_token = None
    if csrf_source == "html":
        csrf_input = soup.find("input", {"name": csrf_field})
        csrf_token = csrf_input["value"] if csrf_input else None
    elif csrf_source == "cookie":
        csrf_token = pre_response.cookies.get(csrf_field)
    elif csrf_source == "header":
        csrf_token = pre_response.headers.get(csrf_field)

    payload = {
        config["login"]["username_field"]: username,
        config["login"]["password_field"]: password,
    }

    if csrf_token:
        payload[csrf_field] = csrf_token
        print(f"[DEBUG] CSRF token added: {csrf_token}")
    else:
        print("⚠️ Warning: CSRF token not found, proceeding without it")

    headers = config.get("headers", {})
    if csrf_source == "header" and csrf_token:
        headers[f"X-{csrf_field}"] = csrf_token

    response = session.post(login_url, data=payload, headers=headers)
    print(response.text)
    if response.status_code == 200 and ("Logout" in response.text or "Dashboard" in response.text):
        save_cookies()
        print("Login successful, cookies saved.")
        return True
    else:
        print("Login failed.")
        return False

def login_via_playwright(config):
    COOKIE_FILE = "playwright_cookies.json"

    def save_cookies(context):
        cookies = context.cookies()
        with open(COOKIE_FILE, "w") as f:
            json.dump(cookies, f)

    def load_cookies(context):
        if os.path.exists(COOKIE_FILE):
            with open(COOKIE_FILE, "r") as f:
                cookies = json.load(f)
                context.add_cookies(cookies)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        load_cookies(context)

        page = context.new_page()
        page.goto(config["url"])
        if "Logout" in page.content() or "Dashboard" in page.content():
            print("Reusing existing Playwright cookies.")
            html = page.content()
            browser.close()
            return html, context.cookies()

        # Not logged in, proceed with login
        page.goto(config["login"]["url"])
        page.fill(f'input[name="{config["login"]["username_field"]}"]', config["login"]["credentials"]["username"])
        page.fill(f'input[name="{config["login"]["password_field"]}"]', config["login"]["credentials"]["password"])
        page.click('button[type="submit"]')
        page.wait_for_timeout(2000)

        save_cookies(context)
        html = page.content()
        browser.close()
        return html, context.cookies()

def fetch_page(url, headers=None):
    response = session.get(url, headers=headers)
    return response.text

def run_js_page(url, headers=None):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        if headers:
            page.set_extra_http_headers(headers)
        page.goto(url)
        content = page.content()
        browser.close()
        return content

from bs4 import BeautifulSoup
from lxml import etree

def extract_value(soup, tree, rule, context=None):
    selector_type = rule.get("type")
    query = rule.get("query")
    attr = rule.get("attribute", None)
    multiple = rule.get("multiple", False)

    if selector_type == "css":
        if multiple:
            elements = (context or soup).select(query)
            if attr:
                return [e.get(attr) for e in elements if e and e.get(attr)]
            else:
                return [e.get_text(strip=True) for e in elements if e]
        else:
            elem = (context or soup).select_one(query)
            if elem:
                return elem.get(attr) if attr else elem.get_text(strip=True)
            return None

    elif selector_type == "xpath":
        results = (context or tree).xpath(query)
        if not results:
            return None
        if multiple:
            if attr or isinstance(results[0], str):
                return [r.strip() if isinstance(r, str) else r for r in results]
            else:
                return [r.text.strip() for r in results if hasattr(r, 'text')]
        else:
            r = results[0]
            return r.strip() if isinstance(r, str) else getattr(r, "text", "").strip()

    return None


def parse_content(content, selectors):
    soup = BeautifulSoup(content, "html.parser")
    tree = etree.HTML(content)
    extracted = {}
    for key, rule in selectors.items():
        selector_type = rule.get("type")

        if selector_type == "group":
            container_selector = rule.get("container")
            multiple = rule.get("multiple", False)
            fields = rule.get("fields", {})
            containers = soup.select(container_selector)
            group_data = []
            for container in containers:
                item_data = {}
                for field_key, sub_rule in fields.items():
                    item_data[field_key] = extract_value(soup, tree, sub_rule, context=container)
                group_data.append(item_data)

            extracted[key] = group_data if multiple else (group_data[0] if group_data else None)

        else:
            extracted[key] = extract_value(soup, tree, rule)

    return extracted