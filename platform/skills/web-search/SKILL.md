---
name: Web Search & URL Fetch
description: Read web pages directly from a URL or search the internet for documentation, facts, and links.
tools:
- fetch_url
- web_search
---

# Web Search & URL Fetch

Give agents direct hands to the internet: scrape and read a specific web page when you already have a URL (`fetch_url`), or run a web search (`web_search`) to discover links and current facts.

## Order

1. **Direct link provided (`fetch_url`)**:
   - When the user gives you an `http://` or `https://` URL (or when a prior `web_search` returned a promising URL), call `fetch_url(url="...")` directly.
   - Do **not** call `web_search` just to read a URL you already have.
2. **Broad search (`web_search`)**:
   - When you need current facts, external documentation, or links you do not have yet, call `web_search(query="...", max_results=5)`.
   - Keep search queries focused and stop after 1–2 searches per turn.
   - If a search snippet is too brief, call `fetch_url` on the top result URL to read the full page.

## Pitfalls

- Private/loopback URLs (`127.0.0.1`, `localhost`, `192.168.x.x`) are blocked by `fetch_url` unless the operator enables **Allow private/LAN URLs** in **Settings -> Connections -> Web Search & Fetch**.
- If `web_search` reports that the selected provider requires an API key, tell the operator to add the token (or switch to **DuckDuckGo Lite (Free)**) in **Settings -> Connections -> Web Search & Fetch**.
- Cite the source `url` and `title` returned by `fetch_url` or `web_search`; never invent URLs or page contents.

## Done-when

- The user's question is answered with grounded facts and source URLs from `fetch_url` or `web_search`.
