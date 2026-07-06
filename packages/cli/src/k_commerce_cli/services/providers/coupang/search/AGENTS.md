# Coupang Search Knowledge Base

## OVERVIEW

Logged-in Coupang product search, result scraping, table/JSON payloads, and detail-price enrichment.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Search orchestration | `service.py` | URL build, readiness wait, scraping, detail prices. |
| Result types | `type.py` | `SearchResultItem`, `SearchProductResult`. |
| Provider exports | `__init__.py` | Re-exports service/types. |
| CLI wrapper | `../../../commands/search.py` | Sort choices, table/JSON output, save path. |

## CONVENTIONS

- Keep CLI `SUPPORTED_SORTS` aligned with service `SEARCH_SORT_MAP`.
- Search requires an existing session; missing login uses the shared Korean not-logged-in message.
- JSON output/save must preserve Korean text with `ensure_ascii=False`.

## ANTI-PATTERNS

- Do not duplicate scraping or price extraction in the CLI command.
