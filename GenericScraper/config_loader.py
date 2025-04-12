import json
import yaml

'''
Config Usage Guide:
🔍 Supported Selector Types

✅ 1. CSS Selector
Use when the structure is simple and consistent.

YAML
title:
  type: css
  query: "h1.article-title"

HTML
<h1 class="article-title">This is a heading</h1>

✅ 2. XPath Selector

Use when CSS isn’t sufficient or for precise targeting.
YAML
price:
  type: xpath
  query: "//div[@class='price']/text()"

HTML
<div class="price">$199</div>

✅ 3. Attribute Selector

Use this when you need data from attributes like href, src, data-*.

image:
  type: css
  query: "img.thumbnail"
  attribute: src

HTML
<img class="thumbnail" src="https://example.com/image.jpg">
✳️ Optional field attribute can be used with CSS or XPath.

✅ 4. XPath with Attribute Extraction
YAML
document_link:
  type: xpath
  query: "//a[contains(text(),'Download')]/@href"

HTML
<a href="/docs/file.pdf">Download</a>

✅ 5. List of Items (Loop/Multiple matches)
 multiple: true tells the parser to return a list of values instead of one.

YAML
comments:
  type: css
  query: "div.comment-text"
  multiple: true

HTML
<div class="comment-text">Great post!</div>
<div class="comment-text">Very helpful.</div>

✅ 6. Nested Selectors (Optional - Advanced Feature)
If you plan to support structured or nested fields:

YAML
article:
  type: group
  fields:
    title:
      type: css
      query: "h2.title"
    link:
      type: css
      query: "a"
      attribute: href

HTML
<div class="article">
  <h2 class="title">Hello World</h2>
  <a href="/read-more">Read More</a>
</div>
'''

def load_config(file_path):
    if file_path.endswith(".json"):
        with open(file_path) as f:
            return json.load(f)
    elif file_path.endswith(".yaml") or file_path.endswith(".yml"):
        with open(file_path) as f:
            return yaml.safe_load(f)
    else:
        raise ValueError("Unsupported config format")

# Example config structure
# {
#   "url": "https://example.com",
#   "headers": {"User-Agent": "Mozilla"},
#   "selectors": {
#     "title": {"type": "css", "query": "h1.title"},
#     "price": {"type": "xpath", "query": "//span[@class='price']"}
#   }
# }


# # Target page to scrape
# url: https://example.com/data
#
# # Optional request headers (used for API or browser-like headers)
# headers:
#   User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)
#   Accept-Language: en-US,en;q=0.9

# Login configuration
# login:
#   enabled: true
#   type: form                   # options: form / javascript
#   url: https://example.com/login
#   username_field: username
#   password_field: password
#   csrf_field: csrfmiddlewaretoken     # optional, only needed if site requires it
#   csrf_source: html                   # options: html / cookie / header
#   credentials:
#     username: my_username
#     password: my_password
#
# # Selectors to extract data
# selectors:
#   title:
#     type: css                       # options: css / xpath
#     query: "h1.article-title"
#   date:
#     type: xpath
#     query: "//span[@class='publish-date']/text()"
#   author:
#     type: css
#     query: ".author-name"
#   content:
#     type: css
#     query: "div.content-body"
#
# # Pagination config (optional)
# pagination:
#   type: param                      # options: param (e.g., ?page=2), can extend to link or JS click
#   param: page
#   start: 1
#   end: 5
#   step: 1
#
# # Output format
# output:
#   format: json                    # options: json / csv (if extended)
#   path: scraped_output.json



