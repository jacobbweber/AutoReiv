---
id: CARD-719
title: "Web Search and URL Fetch Skill with Settings Provider Config"
type: feature
status: Done
priority: P1
milestone: M31
needs_decision: none
proof:
  journeys: [card-719-web-search-and-url-fetch-skill]
  checks:
    - tests/unit/skills/test_card719_web_tools.py
    - tests/unit/frontend/card_719_web_search_settings.test.js
branch: feat/card-719-web-search-and-url-fetch-skill
log: {minutes: 20, qa_runs: 3, findings: 0}
created: 2026-10-18
completed: 2026-10-18
---

# CARD-719 Web Search and URL Fetch Skill with Settings Provider Config

## Intent
Give `AutoReiv` hands to the internet with zero new Python dependencies (`httpx` + standard library HTML parsing):
1. A direct URL reader (`fetch_url`) so the operator can paste any link and `AutoReiv` can scrape and read the page content without needing a search engine.
2. A web search tool (`web_search`) that works out of the box with zero-key DuckDuckGo Lite HTML search and lets the operator pick **Tavily** or **Brave Search** with a Vault-encrypted API token in **Settings -> Connections**.

## Goal
- `platform/skills/web-search/SKILL.md` ships with `tools: [fetch_url, web_search]` and is ticked on `AutoReiv` (including automatic reconciliation onto existing `autoreiv.md` user copies).
- Calling `fetch_url(url)` fetches an HTTP/HTTPS page via `httpx`, extracts clean readable text/Markdown (title, headings, links, body text) with SSRF protection against loopback/private IPs by default (configurable for homelab LAN URLs).
- Calling `web_search(query, max_results=5)` searches via the configured provider in `web_search_settings` (`duckduckgo` zero-key default, `tavily`, or `brave`) and returns normalized `{title, url, snippet}` results.
- In **Settings -> Connections -> Web Search & Fetch**, the operator can select the search provider (`DuckDuckGo Lite (Free, No API Key)`, `Tavily Search (API Key)`, `Brave Search (API Key)`), pick an existing Vault credential or paste a new API key (auto-encrypted into the Credential Vault), toggle LAN/private URL fetching for `fetch_url`, and save.

## Change
- `platform/skills/web-search/SKILL.md`: New shipped platform skill binding `fetch_url` and `web_search`.
- `platform/agents/autoreiv.md` & `src/infrastructure/content/store.py`: Tick `web-search` on `AutoReiv` and include `web-search` in `_reconcile_user_agent` so existing user copies of `autoreiv.md` gain the skill automatically.
- `src/application/skills/web_tools.py`: Implement `WebTools` (`fetch_url` and `web_search`), HTML-to-text/markdown extractor (`extract_html_text`), SSRF host validation (`validate_fetch_url`), and DuckDuckGo Lite / Tavily / Brave Search HTTP clients over `httpx`.
- `src/application/kernel/tool_access.py` & `src/application/bootstrap/ecosystem.py`: Register `fetch_url` and `web_search` in `READ_TOOLS` and bootstrap `WebTools(state_store=store)`.
- `src/web/routers/settings_web_search.py` & `src/web/routers/settings.py`: Add `GET /api/settings/web-search` and `PUT /api/settings/web-search` with Credential Vault encryption for inline API tokens.
- `src/web/templates/partials/settings_preferences.html`, `src/web/static/modules/studios/settings_web_search.js`, `src/web/static/modules/studios/settings.js`: Add the **Web Search & URL Fetch** card in **Settings -> Connections** and wire its load/save lifecycle.

## What dies
- Nothing (net-new `web-search` platform skill and Settings -> Connections provider config).

## Proof
- Journey `card-719-web-search-and-url-fetch-skill`:
  1. Open **Settings -> Connections**, verify the **Web Search & URL Fetch** card defaults to `DuckDuckGo Lite (Free, No API Key)`, switch provider to `Tavily Search (API Key)` with an inline API token, save, and verify the token is encrypted in the Credential Vault (`web-search-tavily`) without leaking plaintext in settings.
  2. Switch back to `DuckDuckGo Lite` with private/local URL fetching enabled for local verification, and verify `AutoReiv` has `fetch_url` and `web_search` allowed via `web-search`.
  3. In Chat with `AutoReiv`, prompt `AutoReiv` to read a live HTTP page URL using `fetch_url` and verify the tool executes and returns the extracted page content.
- Checks:
  - `tests/unit/skills/test_card719_web_tools.py`
  - `tests/unit/frontend/card_719_web_search_settings.test.js`

## Plan and decisions
- **D1 (Web search & URL fetch architecture):** Approved by Jacob (`1. I like your recommended`): Ship both `fetch_url` and `web_search` with zero new dependencies (`httpx` + stdlib HTML parser), defaulting to zero-key DuckDuckGo Lite out of the box with a Settings -> Connections provider & Vault token picker for Tavily and Brave Search.

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-719-web-search-and-url-fetch-skill` | desktop | PASS | Verified Settings -> Connections Web Search & URL Fetch card, Vault-encrypted Tavily token save, switch back to DuckDuckGo Lite, `web-search` skill in Capabilities Studio + `autoreiv` profile, and live `fetch_url` execution in Chat (`1280px <= 1280px`). |
| `card-719-web-search-and-url-fetch-skill` | phone | PASS | Same on phone (`390px <= 390px`) with zero horizontal overflow. |

Screenshots:
- `/tmp/autoreiv-qa/card-719/card-719-web-search-and-url-fetch-skill-desktop-01-open-settings-connections-and-configure-web-sear.png`
- `/tmp/autoreiv-qa/card-719/card-719-web-search-and-url-fetch-skill-desktop-03-use-fetch-url-in-chat-to-read-a-live-http-url-an.png`
- `/tmp/autoreiv-qa/card-719/card-719-web-search-and-url-fetch-skill-phone-01-open-settings-connections-and-configure-web-sear.png`

## Release note
- Added the `web-search` platform skill (`fetch_url` and `web_search` tools) and a **Web Search & URL Fetch** configuration card in **Settings -> Connections** supporting zero-key DuckDuckGo Lite search, Vault-encrypted Tavily and Brave Search API keys, and direct webpage text extraction.
