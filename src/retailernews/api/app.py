"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

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
        max-width: 460px;
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
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
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

      .actions {
        display: flex;
        flex-direction: column;
        gap: 12px;
        margin-bottom: 20px;
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

      .digest-panel {
        margin-top: 24px;
        display: flex;
        flex-direction: column;
        gap: 12px;
      }

      .digest-panel h2 {
        margin: 0;
        font-size: 1.25rem;
        color: #1f2937;
      }

      .digest-box {
        width: 100%;
        min-height: 180px;
        padding: 16px;
        border-radius: 12px;
        border: 1px solid rgba(15, 23, 42, 0.1);
        background: #f8fafc;
        color: #0f172a;
        font-size: 1rem;
        line-height: 1.5;
        resize: vertical;
        box-shadow: inset 0 2px 8px rgba(15, 23, 42, 0.08);
      }
    </style>
  </head>
  <body>
    <main class=\"card\">
      <h1>Retailer News Toolkit</h1>
      <p>
        Use the controls below to fetch the latest retailer news articles and to
        create an executive-ready digest of stored content.
      </p>
      <div class=\"actions\">
        <button id=\"run-crawler\">
          <span aria-hidden=\"true\">🕷️</span>
          Run crawler
        </button>
        <button id=\"run-summarizer\">
          <span aria-hidden=\"true\">📝</span>
          Build summary
        </button>
      </div>
      <div class=\"status\" id=\"status\"></div>
      <pre id=\"results\" hidden></pre>
      <section class=\"digest-panel\" id=\"digest-panel\" hidden>
        <h2>Executive Digest</h2>
        <textarea class=\"digest-box\" id=\"digest-text\" readonly></textarea>
      </section>
    </main>
    <script>
      const crawlerButton = document.getElementById("run-crawler");
      const statusEl = document.getElementById("status");
      const resultsEl = document.getElementById("results");
      const digestPanel = document.getElementById("digest-panel");
      const digestText = document.getElementById("digest-text");

      async function callEndpoint(button, url, pendingMessage, onSuccess) {
        statusEl.textContent = pendingMessage;
        resultsEl.hidden = true;
        digestPanel.hidden = true;
        digestText.value = "";
        button.disabled = true;

        try {
          const response = await fetch(url, { method: "POST" });
          if (!response.ok) {
            const message = await response.text();
            throw new Error(message || `Request failed with ${response.status}`);
          }

          await response.json();
          statusEl.textContent = `Completed at ${new Date().toLocaleTimeString()}`;
        } catch (error) {
          statusEl.textContent = `Error: ${error.message}`;
          resultsEl.hidden = true;
          digestPanel.hidden = true;
        } finally {
          button.disabled = false;
        }
      }

      crawlerButton.addEventListener("click", () =>
        callEndpoint(crawlerButton, "/api/crawl", "Running crawler...")
      );

      summarizerButton.addEventListener("click", () =>
        callEndpoint(
          summarizerButton,
          "/api/summaries",
          "Building digest...",
          (payload) => {
            const digest = payload?.digest?.trim();
            if (digest) {
              digestText.value = digest;
              digestPanel.hidden = false;
            } else {
              resultsEl.hidden = false;
              resultsEl.textContent = "No digest content available.";
            }
          }
        )
      );
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
