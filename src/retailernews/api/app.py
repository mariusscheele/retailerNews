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
        color-scheme: only light;
        font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: #eef2f7;
        color: #0f172a;
      }

      *,
      *::before,
      *::after {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        background: linear-gradient(145deg, #f8fafc 0%, #e2e8f0 100%);
        min-height: 100vh;
        display: flex;
      }

      .app-shell {
        display: grid;
        grid-template-columns: minmax(240px, 300px) 1fr;
        width: 100%;
        min-height: 100vh;
      }

      .sidebar {
        background: #111827;
        color: #f8fafc;
        padding: 48px 36px;
        display: flex;
        flex-direction: column;
        gap: 32px;
        box-shadow: 8px 0 32px rgba(15, 23, 42, 0.18);
      }

      .sidebar h1 {
        font-size: 1.75rem;
        margin: 0;
        letter-spacing: -0.02em;
      }

      .sidebar p {
        margin: 0;
        color: rgba(248, 250, 252, 0.72);
        line-height: 1.6;
      }

      .sidebar-actions {
        display: flex;
        flex-direction: column;
        gap: 14px;
      }

      button {
        appearance: none;
        border: none;
        border-radius: 999px;
        padding: 14px 22px;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
      }

      .button-primary {
        background: linear-gradient(135deg, #6366f1, #4338ca);
        color: white;
        box-shadow: 0 16px 30px rgba(99, 102, 241, 0.35);
      }

      .button-primary:not(:disabled):hover {
        transform: translateY(-1px);
        box-shadow: 0 20px 36px rgba(99, 102, 241, 0.4);
      }

      .button-secondary {
        background: rgba(248, 250, 252, 0.08);
        color: #f8fafc;
        border: 1px solid rgba(248, 250, 252, 0.16);
      }

      .button-secondary:not(:disabled):hover {
        background: rgba(248, 250, 252, 0.18);
      }

      button:disabled {
        opacity: 0.6;
        cursor: wait;
        box-shadow: none;
      }

      .status {
        font-size: 0.95rem;
        font-weight: 500;
        color: rgba(248, 250, 252, 0.72);
        min-height: 1.4em;
      }

      .content {
        padding: 64px clamp(32px, 5vw, 80px);
        display: flex;
        flex-direction: column;
        gap: 32px;
      }

      .hero {
        max-width: 720px;
      }

      .hero h2 {
        font-size: clamp(2rem, 4vw, 2.75rem);
        margin: 0 0 16px;
        color: #0f172a;
        letter-spacing: -0.03em;
      }

      .hero p {
        margin: 0;
        color: #475569;
        line-height: 1.7;
        font-size: 1.05rem;
      }

      .summary-section {
        display: flex;
        flex-direction: column;
        gap: 20px;
        align-items: center;
      }

      .summary-card {
        background: white;
        border-radius: 24px;
        padding: clamp(24px, 4vw, 40px);
        box-shadow: 0 24px 60px rgba(15, 23, 42, 0.12);
        border: 1px solid rgba(148, 163, 184, 0.15);
        width: min(75%, 880px);
        margin: 0 auto;
      }

      .summary-header {
        display: flex;
        flex-direction: column;
        gap: 18px;
      }

      .summary-header h3 {
        margin: 0;
        font-size: 1.5rem;
        color: #1e293b;
      }

      .category-buttons {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
      }

      .category-buttons button {
        background: #f1f5f9;
        color: #1e293b;
        border-radius: 999px;
        padding: 10px 20px;
        font-weight: 600;
        border: 1px solid transparent;
      }

      .category-buttons button:hover {
        background: #e2e8f0;
      }

      .category-buttons button.is-active {
        background: #0f172a;
        color: #f8fafc;
        border-color: #0f172a;
        box-shadow: 0 12px 24px rgba(15, 23, 42, 0.18);
      }

      .summary-content {
        display: flex;
        flex-direction: column;
        gap: 28px;
      }

      .digest-overview {
        display: flex;
        flex-direction: column;
        gap: 1em;
        font-size: 1.05rem;
        line-height: 1.8;
        color: #1f2937;
      }

      .digest-overview p {
        margin: 0;
      }

      .digest-article {
        margin: 0;
        display: flex;
        flex-direction: column;
        gap: 16px;
        color: #334155;
      }

      .digest-article h4 {
        margin: 0;
        font-size: 1.25rem;
        color: #0f172a;
        letter-spacing: -0.01em;
      }

      .digest-body {
        display: flex;
        flex-direction: column;
        gap: 1em;
        font-size: 1.05rem;
        line-height: 1.8;
      }

      .digest-body p {
        margin: 0;
      }

      @media (max-width: 900px) {
        .app-shell {
          grid-template-columns: 1fr;
        }

        .sidebar {
          flex-direction: row;
          align-items: center;
          justify-content: space-between;
          padding: 28px 24px;
        }

        .sidebar-actions {
          flex-direction: row;
        }

        .content {
          padding: 32px 24px 48px;
        }

        .summary-card {
          width: 100%;
        }
      }

      @media (max-width: 640px) {
        .sidebar {
          flex-direction: column;
          align-items: flex-start;
          gap: 20px;
        }

        .sidebar-actions {
          width: 100%;
          flex-direction: column;
        }

        .hero h2 {
          font-size: 2rem;
        }
      }
    </style>
  </head>
  <body>
    <div class=\"app-shell\">
      <aside class=\"sidebar\">
        <div>
          <h1>Retailer News Toolkit</h1>
          <p>Keep your leadership team informed with curated daily insights.</p>
        </div>
        <div class=\"sidebar-actions\">
          <button class=\"button-primary\" id=\"run-crawler\">
            <span aria-hidden=\"true\">🕷️</span>
            Run crawler
          </button>
          <button class=\"button-secondary\" id=\"run-summarizer\">
            <span aria-hidden=\"true\">📝</span>
            Build summary
          </button>
        </div>
        <div class=\"status\" id=\"status\"></div>
      </aside>
      <main class=\"content\">
        <section class=\"hero\">
          <h2>Welcome to our page for latest news within beauty industry</h2>
          <p>
            Explore curated highlights from the worlds of e-commerce, store operations,
            and customer experience, powered by our automated retailer news crawler.
          </p>
        </section>
        <section class=\"summary-section\" id=\"summary-section\" hidden>
          <div class=\"summary-card\">
            <header class=\"summary-header\">
              <h3>Discover the latest insights</h3>
              <div class=\"category-buttons\" id=\"category-buttons\"></div>
            </header>
            <div class=\"summary-content\">
              <section class=\"digest-overview\" id=\"digest-overview\" hidden></section>
              <article class=\"digest-article\">
                <h4 id=\"article-title\">Latest highlights</h4>
                <div class=\"digest-body\" id=\"article-body\"></div>
              </article>
            </div>
          </div>
        </section>
      </main>
    </div>
    <script>
      const crawlerButton = document.getElementById("run-crawler");
      const summarizerButton = document.getElementById("run-summarizer");
      const statusEl = document.getElementById("status");
      const summarySection = document.getElementById("summary-section");
      const categoryButtonsContainer = document.getElementById("category-buttons");
      const articleTitle = document.getElementById("article-title");
      const articleBody = document.getElementById("article-body");
      const digestOverview = document.getElementById("digest-overview");

      const categoryDigestCache = new Map();
      let categoryButtons = [];

      function renderParagraphs(target, text) {
        target.innerHTML = "";

        const trimmed = (text || "").trim();
        if (!trimmed) {
          target.hidden = true;
          return;
        }

        const sanitized = trimmed.replace(/^[\t ]*[-•*][\t ]+/gm, "");
        const paragraphs = sanitized
          .split(/\n{2,}/)
          .map((block) => block.replace(/\n+/g, " ").trim())
          .filter(Boolean);

        if (paragraphs.length === 0) {
          target.hidden = true;
          return;
        }

        paragraphs.forEach((paragraph) => {
          const p = document.createElement("p");
          p.textContent = paragraph;
          target.appendChild(p);
        });

        target.hidden = false;
      }

      function showMessage(target, message) {
        target.hidden = false;
        target.innerHTML = "";
        const p = document.createElement("p");
        p.textContent = message;
        target.appendChild(p);
      }

      function setActiveCategory(category) {
        const entry = categoryDigestCache.get(category);

        categoryButtons.forEach((button) => {
          const isActive = button.dataset.category === category;
          button.classList.toggle("is-active", isActive);
        });

        if (!entry) {
          articleTitle.textContent = "Latest highlights";
          showMessage(articleBody, "Select a category to view its summary.");
          return;
        }

        articleTitle.textContent = `${entry.name} highlights`;
        const summaryText = (entry.summary || "").trim();
        renderParagraphs(articleBody, summaryText);
        if (articleBody.hidden) {
          showMessage(articleBody, "No updates available for this category yet.");
        }
      }

      function renderCategoryButtons(categories) {
        categoryDigestCache.clear();
        categoryButtonsContainer.innerHTML = "";
        categoryButtons = [];
        articleBody.innerHTML = "";
        articleBody.hidden = true;

        categories.forEach((category) => {
          categoryDigestCache.set(category.slug, {
            name: category.name,
            summary: category.summary,
          });

          const button = document.createElement("button");
          button.type = "button";
          button.dataset.category = category.slug;
          button.textContent = category.name;
          button.addEventListener("click", () => setActiveCategory(category.slug));
          categoryButtonsContainer.appendChild(button);
          categoryButtons.push(button);
        });

        if (categoryButtons.length > 0) {
          setActiveCategory(categories[0].slug);
        } else {
          articleTitle.textContent = "Latest highlights";
          showMessage(articleBody, "No category summaries available yet.");
        }
      }

      async function callEndpoint(button, url, pendingMessage, onSuccess) {
        statusEl.textContent = pendingMessage;
        summarySection.hidden = true;
        categoryButtonsContainer.innerHTML = "";
        categoryDigestCache.clear();
        categoryButtons = [];
        articleTitle.textContent = "Latest highlights";
        articleBody.innerHTML = "";
        articleBody.hidden = true;
        digestOverview.innerHTML = "";
        digestOverview.hidden = true;
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
          summarySection.hidden = true;
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
            const categories = Array.isArray(payload?.categories)
              ? payload.categories
              : [];

            if (digest) {
              renderParagraphs(digestOverview, digest);
              if (digestOverview.hidden) {
                showMessage(digestOverview, "Digest content unavailable.");
              }
            } else {
              showMessage(digestOverview, "Digest content unavailable.");
            }

            summarySection.hidden = false;
            renderCategoryButtons(categories);
            summarySection.scrollIntoView({ behavior: "smooth", block: "start" });
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
