"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from starlette.responses import HTMLResponse

from retailernews.api.routes import router

INDEX_HTML = """
<!DOCTYPE html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Retailer News Crawler</title>
    <style>
      :root {
        color-scheme: light dark;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif;
        background: #f4f4f5;
        color: #111827;
      }

      body {
        margin: 0;
        display: flex;
        min-height: 100vh;
        justify-content: center;
        align-items: center;
      }

      .card {
        background: white;
        border-radius: 12px;
        padding: 32px;
        box-shadow: 0 20px 45px rgba(15, 23, 42, 0.12);
        max-width: 420px;
        width: 100%;
      }

      h1 {
        margin-top: 0;
        margin-bottom: 16px;
        font-size: 1.75rem;
        color: #1e293b;
      }

      p {
        margin-top: 0;
        margin-bottom: 24px;
        color: #475569;
      }

      button {
        appearance: none;
        border: none;
        border-radius: 9999px;
        padding: 12px 28px;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        background: linear-gradient(135deg, #2563eb, #4f46e5);
        color: white;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        box-shadow: 0 10px 25px rgba(37, 99, 235, 0.25);
      }

      button:disabled {
        opacity: 0.6;
        cursor: wait;
        box-shadow: none;
      }

      button:not(:disabled):hover {
        transform: translateY(-1px);
        box-shadow: 0 14px 28px rgba(37, 99, 235, 0.3);
      }

      pre {
        background: #0f172a;
        color: #f8fafc;
        padding: 16px;
        border-radius: 8px;
        font-size: 0.9rem;
        max-height: 200px;
        overflow: auto;
      }

      .status {
        margin-top: 16px;
        font-weight: 600;
      }
    </style>
  </head>
  <body>
    <main class=\"card\">
      <h1>Retailer News Crawler</h1>
      <p>
        Press the button below to fetch the latest articles from all configured
        retailer news sources.
      </p>
      <button id=\"run-crawler\">Run crawler</button>
      <div class=\"status\" id=\"status\"></div>
      <pre id=\"results\" hidden></pre>
    </main>
    <script>
      const button = document.getElementById("run-crawler");
      const statusEl = document.getElementById("status");
      const resultsEl = document.getElementById("results");

      async function runCrawler() {
        statusEl.textContent = "Running crawler...";
        resultsEl.hidden = true;
        button.disabled = true;

        try {
          const response = await fetch("/api/crawl", { method: "POST" });
          if (!response.ok) {
            const message = await response.text();
            throw new Error(message || `Request failed with ${response.status}`);
          }

          const payload = await response.json();
          statusEl.textContent = `Completed at ${new Date().toLocaleTimeString()}`;
          resultsEl.hidden = false;
          resultsEl.textContent = JSON.stringify(payload, null, 2);
        } catch (error) {
          statusEl.textContent = `Error: ${error.message}`;
          resultsEl.hidden = true;
        } finally {
          button.disabled = false;
        }
      }

      button.addEventListener("click", runCrawler);
    </script>
  </body>
</html>
"""


def create_app() -> FastAPI:
    app = FastAPI(title="Retailer News", description="Retail insights crawler API")
    app.include_router(router, prefix="/api")

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return INDEX_HTML

    return app


app = create_app()
