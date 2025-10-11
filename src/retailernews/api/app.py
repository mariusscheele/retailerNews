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
        color: #0f172a;
      }

      body {
        margin: 0;
        min-height: 100vh;
        background: radial-gradient(circle at top left, #eef2ff, #f5f5f5 55%);
      }

      .layout {
        display: grid;
        grid-template-columns: 280px 1fr;
        min-height: 100vh;
      }

      .sidebar {
        background: white;
        padding: 32px 28px;
        box-shadow: 8px 0 24px rgba(15, 23, 42, 0.08);
        display: flex;
        flex-direction: column;
        gap: 24px;
      }

      .sidebar h1 {
        margin: 0;
        font-size: 1.75rem;
        color: #1f2937;
      }

      .sidebar p {
        margin: 0;
        color: #475569;
        line-height: 1.5;
      }

      .actions {
        display: grid;
        gap: 16px;
      }

      button {
        appearance: none;
        border: none;
        border-radius: 16px;
        padding: 14px 22px;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        background: linear-gradient(135deg, #2563eb, #4f46e5);
        color: white;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        box-shadow: 0 12px 30px rgba(37, 99, 235, 0.25);
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
        transform: translateY(-2px);
        box-shadow: 0 16px 32px rgba(37, 99, 235, 0.3);
      }

      .status {
        min-height: 24px;
        font-weight: 600;
        color: #1f2937;
      }

      .content {
        padding: 48px 56px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: flex-start;
        gap: 24px;
      }

      .welcome {
        max-width: 720px;
        text-align: center;
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(6px);
        padding: 32px;
        border-radius: 24px;
        box-shadow: 0 20px 45px rgba(15, 23, 42, 0.12);
      }

      .welcome h2 {
        margin: 0 0 12px;
        font-size: 2rem;
        color: #111827;
      }

      .welcome p {
        margin: 0;
        color: #475569;
        line-height: 1.6;
      }

      .digest-panel {
        max-width: 760px;
        width: 100%;
        background: white;
        border-radius: 28px;
        padding: 36px;
        box-shadow: 0 24px 50px rgba(15, 23, 42, 0.12);
        display: none;
      }

      .digest-panel.visible {
        display: block;
      }

      .digest-panel h3 {
        margin-top: 0;
        font-size: 1.5rem;
        color: #111827;
      }

      .digest-article {
        margin: 0;
        padding: 0;
        color: #1f2937;
        line-height: 1.8;
        display: grid;
        gap: 16px;
      }

      .digest-article p {
        margin: 0;
      }

      .digest-article strong {
        color: #1d4ed8;
      }

      @media (max-width: 900px) {
        .layout {
          grid-template-columns: 1fr;
        }

        .sidebar {
          box-shadow: none;
          border-bottom: 1px solid rgba(15, 23, 42, 0.08);
        }

        .content {
          padding: 32px 20px 64px;
        }
      }
    </style>
  </head>
  <body>
    <div class=\"layout\">
      <aside class=\"sidebar\">
        <div>
          <h1>Retailer News Toolkit</h1>
          <p>
            Run the crawler to capture the newest updates and build a summary
            when you're ready to review the highlights.
          </p>
        </div>
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
      </aside>
      <main class=\"content\">
        <section class=\"welcome\">
          <h2>Welcome to our page for latest news within beauty industry</h2>
          <p>
            Explore curated updates and insights from across the beauty retail
            landscape. Build a fresh digest whenever you need an executive-ready
            overview of what matters most.
          </p>
        </section>
        <section class=\"digest-panel\" id=\"digest-panel\">
          <h3>Executive Digest</h3>
          <article class=\"digest-article\" id=\"digest-article\"></article>
        </section>
      </main>
    </div>
    <script>
      const crawlerButton = document.getElementById("run-crawler");
      const summarizerButton = document.getElementById("run-summarizer");
      const statusEl = document.getElementById("status");
      const digestPanel = document.getElementById("digest-panel");
      const digestArticle = document.getElementById("digest-article");

      function renderDigestArticle(text) {
        const paragraphs = text
          .replace(/\r/g, "")
          .split(/\n{2,}/)
          .map((paragraph) => paragraph.trim())
          .filter(Boolean);

        digestArticle.innerHTML = "";

        if (!paragraphs.length) {
          const fallback = document.createElement("p");
          fallback.textContent = "No digest content available.";
          digestArticle.appendChild(fallback);
          return;
        }

        paragraphs.forEach((paragraph) => {
          const p = document.createElement("p");
          p.textContent = paragraph;
          digestArticle.appendChild(p);
        });
      }

      async function callEndpoint(button, url, pendingMessage, onSuccess) {
        statusEl.textContent = pendingMessage;
        digestPanel.classList.remove("visible");
        digestArticle.innerHTML = "";
        button.disabled = true;

        try {
          const response = await fetch(url, { method: "POST" });
          if (!response.ok) {
            const message = await response.text();
            throw new Error(message || `Request failed with ${response.status}`);
          }

          const payload = await response.json();
          statusEl.textContent = `Completed at ${new Date().toLocaleTimeString()}`;

          if (onSuccess) {
            onSuccess(payload);
          }
        } catch (error) {
          statusEl.textContent = `Error: ${error.message}`;
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
              renderDigestArticle(digest);
              digestPanel.classList.add("visible");
            } else {
              renderDigestArticle("");
              digestPanel.classList.add("visible");
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
