# Retailer News

Retailer News is an experimental crawler intended to collect news and analysis about retail topics such as consumer behaviour, e-commerce trends and store design. The current iteration focuses on providing a Python backend that can be extended into a full web application with a separate frontend.

## Project structure

```
├── data/
│   └── sites.json        # Editable list of sources and their focus topics
├── src/
│   └── retailernews/
│       ├── api/          # FastAPI application and routes
│       ├── services/     # Crawler implementation
│       ├── config.py     # Configuration loading helpers
│       └── models.py     # Shared Pydantic models
├── requirements.txt      # Python dependencies
├── host.json, local.settings.json
└── README.md
```

## Getting started

1. **Install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run the API locally**

   ```bash
   uvicorn retailernews.api.app:app --reload
   ```

   The API exposes the following endpoints:

   - `GET /api/sites`: list configured sources
   - `POST /api/sites`: add a new source (payload must match `SiteConfig`)
   - `DELETE /api/sites/{url}`: remove a source using its URL identifier
   - `POST /api/crawl`: run the crawler across all configured sources

3. **Configure sources**

   Edit `data/sites.json` to add or remove sources. Each entry describes the site name, root URL and the topics you are interested in tracking. The backend can also be pointed to a different configuration file by setting the `RETAILERNEWS_SITES_PATH` environment variable.

## Next steps

- Persist crawl results to Azure storage tables or blobs (dependencies are already in place).
- Add authentication and scheduling for automatic crawls.
- Create a dedicated frontend (React, Vue, etc.) that consumes the FastAPI backend.
- Improve article extraction using site-specific rules or natural language processing.
