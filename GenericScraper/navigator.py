from scraper import fetch_page, parse_content
import asyncio
from crawl4ai import *
def paginate_and_scrape(config, scrape_url):
    base_url = scrape_url
    headers = config.get("headers", {})
    selectors = config["selectors"]
    results = []
    pagination_rule = config.get("pagination")  # e.g., {"type": "param", "start": 1, "end": 5, "step": 1, "param": "page"}


    if not pagination_rule:
        html = fetch_page(base_url, headers)
        results.append(parse_content(html, selectors))
        return results

    appender = pagination_rule.get("appender", "?")
    param = pagination_rule["param"]

    for i in range(pagination_rule["start"], pagination_rule["end"] + 1, pagination_rule.get("step", 1)):
        if appender == "/":
            url = f"{base_url}/{param}/{i}"
        elif appender in ("?", "&"):
            connector = appender if "?" not in base_url else "&"
            url = f"{base_url}{connector}{param}={i}"
        else:
            # Custom appender logic (e.g., "page-2")
            url = f"{base_url}{appender}{i}"

        print(f"[INFO] Fetching page {i}: {url}")
        html = fetch_page(url, headers)
        results.append(parse_content(html, selectors))
        if pagination_rule["type"] == "param":
            url = f"{base_url}?{pagination_rule['param']}={i}"
        else:
            raise NotImplementedError("Pagination type not supported")
        print("Fetching HTML: " + url)

        html = fetch_page(url, headers)
        print("HTML Loaded: " + url)
        results.append(parse_content(html, selectors))
        asyncio.run(crawl4AIScrape(url))
    return results

async def crawl4AIScrape(url):
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url)
        print(result.markdown)