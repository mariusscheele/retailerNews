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
        width: min(75%, 960px);
        margin: 0 auto;
        display: flex;
        flex-direction: column;
        gap: 32px;
      }

      .summary-header {
        display: flex;
        flex-direction: column;
        gap: 12px;
      }

      .summary-header h3 {
        margin: 0;
        font-size: 1.6rem;
        color: #1e293b;
      }

      .category-grid {
        display: grid;
        gap: 20px;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      }

      .category-card {
        background: #f8fafc;
        border: 1px solid rgba(148, 163, 184, 0.25);
        border-radius: 18px;
        padding: 24px;
        display: flex;
        flex-direction: column;
        gap: 16px;
        box-shadow: 0 16px 36px rgba(15, 23, 42, 0.08);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
      }

      .category-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 20px 40px rgba(15, 23, 42, 0.12);
      }

      .category-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 12px;
      }

      .category-header h4 {
        margin: 0;
        font-size: 1.2rem;
        color: #0f172a;
      }

      .category-description {
        margin: 0;
        color: #475569;
        font-size: 0.95rem;
        line-height: 1.6;
      }

      .category-action {
        background: #0f172a;
        color: #f8fafc;
        border-radius: 999px;
        padding: 10px 20px;
        font-weight: 600;
        border: 1px solid transparent;
      }

      .category-action:hover {
        background: #1e293b;
      }

      .category-action:disabled {
        opacity: 0.6;
        cursor: wait;
      }

      .category-message {
        margin: 0;
        font-size: 0.95rem;
        color: #475569;
      }

      .digest-body {
        display: flex;
        flex-direction: column;
        gap: 1em;
        font-size: 1.05rem;
        line-height: 1.8;
        color: #1f2937;
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
        <section class=\"summary-section\" id=\"summary-section\">
          <div class=\"summary-card\">
            <header class=\"summary-header\">
              <h3>Executive digests by focus area</h3>
              <p class=\"category-description\">
                Build targeted summaries for Economy, E-commerce, Customer Experience, and Store Operations.
              </p>
            </header>
            <div class=\"category-card\">
              <div class=\"category-header\">
                <div>
                  <h4>Overall retail digest</h4>
                  <p class=\"category-description\">Blend updates across every focus area into a single briefing.</p>
                </div>
                <button class=\"category-action\" id=\"build-overall\">
                  <span aria-hidden=\"true\">📝</span>
                  Build summary
                </button>
              </div>
              <p class=\"category-message\" id=\"overall-status\">No digest generated yet.</p>
              <div class=\"digest-body\" id=\"overall-digest\" hidden></div>
            </div>
            <div class=\"category-grid\" id=\"category-grid\"></div>
          </div>
        </section>
      </main>
    </div>
    <script>
      const crawlerButton = document.getElementById("run-crawler");
      const statusEl = document.getElementById("status");
      const summarySection = document.getElementById("summary-section");
      const overallButton = document.getElementById("build-overall");
      const overallDigest = document.getElementById("overall-digest");
      const overallStatus = document.getElementById("overall-status");
      const categoryGrid = document.getElementById("category-grid");

      const CATEGORY_METADATA = [
        {
          name: "Economy",
          slug: "economy",
          description: "M&A activity, funding moves, and macroeconomic forces shaping retail.",
        },
        {
          name: "E-commerce",
          slug: "e-commerce",
          description: "Digital sales strategies, marketplace moves, and omnichannel performance.",
        },
        {
          name: "Customer Experience",
          slug: "customer-experience",
          description: "Loyalty, personalization, and service innovations impacting shoppers.",
        },
        {
          name: "Store Operations",
          slug: "store-operations",
          description: "Supply chain, in-store technology, and operational excellence initiatives.",
        },
      ];

      const categoryState = new Map();

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

      async function callEndpoint(button, url, pendingMessage) {
        statusEl.textContent = pendingMessage;
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
        } finally {
          button.disabled = false;
        }
      }

      crawlerButton.addEventListener("click", () =>
        callEndpoint(crawlerButton, "/api/crawl", "Running crawler...")
      );

      function ensureSummarySectionVisible() {
        summarySection.hidden = false;
        summarySection.scrollIntoView({ behavior: "smooth", block: "start" });
      }

      function updateCategoryCard(slug, summaryText) {
        const state = categoryState.get(slug);
        if (!state) {
          return;
        }

        renderParagraphs(state.summaryEl, summaryText || "");
        if (state.summaryEl.hidden) {
          state.messageEl.textContent = "No updates available for this category yet.";
          state.messageEl.hidden = false;
        } else {
          state.messageEl.hidden = true;
        }
      }

      async function buildOverallDigest() {
        ensureSummarySectionVisible();
        overallButton.disabled = true;
        overallStatus.textContent = "Building summary...";
        overallStatus.hidden = false;
        overallDigest.hidden = true;
        statusEl.textContent = "Building overall digest...";

        try {
          const response = await fetch("/api/summaries", { method: "POST" });
          if (!response.ok) {
            const message = await response.text();
            throw new Error(message || `Request failed with ${response.status}`);
          }

          const payload = await response.json();
          const digest = payload?.digest?.trim();
          const categories = Array.isArray(payload?.categories)
            ? payload.categories
            : [];

          if (digest) {
            renderParagraphs(overallDigest, digest);
            overallStatus.hidden = !overallDigest.hidden;
            if (!overallDigest.hidden) {
              overallStatus.hidden = true;
            }
          } else {
            overallDigest.hidden = true;
            overallStatus.textContent = "Digest content unavailable.";
            overallStatus.hidden = false;
          }

          categories.forEach((category) => {
            updateCategoryCard(category.slug, category.summary);
          });

          statusEl.textContent = `Completed at ${new Date().toLocaleTimeString()}`;
        } catch (error) {
          overallDigest.hidden = true;
          overallStatus.textContent = `Error: ${error.message}`;
          overallStatus.hidden = false;
          statusEl.textContent = `Error: ${error.message}`;
        } finally {
          overallButton.disabled = false;
        }
      }

      async function buildCategorySummary(slug) {
        const state = categoryState.get(slug);
        if (!state) {
          return;
        }

        ensureSummarySectionVisible();
        state.button.disabled = true;
        state.messageEl.textContent = "Building summary...";
        state.messageEl.hidden = false;
        state.summaryEl.hidden = true;
        statusEl.textContent = `Building ${state.name} digest...`;

        try {
          const response = await fetch(`/api/summaries?category=${encodeURIComponent(slug)}`, {
            method: "POST",
          });
          if (!response.ok) {
            const message = await response.text();
            throw new Error(message || `Request failed with ${response.status}`);
          }

          const payload = await response.json();
          const categories = Array.isArray(payload?.categories)
            ? payload.categories
            : [];
          const category = categories.find((entry) => entry.slug === slug);
          updateCategoryCard(slug, category?.summary || "");
          statusEl.textContent = `Completed at ${new Date().toLocaleTimeString()}`;
        } catch (error) {
          state.summaryEl.hidden = true;
          state.messageEl.textContent = `Error: ${error.message}`;
          state.messageEl.hidden = false;
          statusEl.textContent = `Error: ${error.message}`;
        } finally {
          state.button.disabled = false;
        }
      }

      function renderCategoryCards() {
        categoryGrid.innerHTML = "";
        categoryState.clear();

        CATEGORY_METADATA.forEach((category) => {
          const card = document.createElement("article");
          card.className = "category-card";

          const header = document.createElement("div");
          header.className = "category-header";

          const titleGroup = document.createElement("div");

          const title = document.createElement("h4");
          title.textContent = category.name;
          titleGroup.appendChild(title);

          const description = document.createElement("p");
          description.className = "category-description";
          description.textContent = category.description;
          titleGroup.appendChild(description);

          const button = document.createElement("button");
          button.type = "button";
          button.className = "category-action";
          button.innerHTML = '<span aria-hidden="true">📝</span> Build summary';
          button.addEventListener("click", () => buildCategorySummary(category.slug));

          header.appendChild(titleGroup);
          header.appendChild(button);

          const message = document.createElement("p");
          message.className = "category-message";
          message.textContent = "No digest generated yet.";

          const summary = document.createElement("div");
          summary.className = "digest-body";
          summary.hidden = true;

          card.appendChild(header);
          card.appendChild(message);
          card.appendChild(summary);

          categoryGrid.appendChild(card);
          categoryState.set(category.slug, {
            name: category.name,
            button,
            messageEl: message,
            summaryEl: summary,
          });
        });
      }

      overallButton.addEventListener("click", buildOverallDigest);
      renderCategoryCards();
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
