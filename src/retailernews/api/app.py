"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from retailernews.api.routes import router

INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Retailer News Crawler</title>
    <style>
      :root {
        color-scheme: light dark;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
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

      .extracted-urls {
        margin-top: 32px;
        padding-top: 24px;
        border-top: 1px solid rgba(148, 163, 184, 0.3);
        display: grid;
        gap: 12px;
      }

      .extracted-urls h4 {
        margin: 0;
        font-size: 1.1rem;
        color: #0f172a;
      }

      .extracted-urls ul {
        margin: 0;
        padding-left: 20px;
        display: grid;
        gap: 8px;
        color: #1f2937;
      }

      .extracted-urls li {
        word-break: break-word;
      }

      .extracted-urls a {
        color: inherit;
        text-decoration: none;
        border-bottom: 1px dashed rgba(148, 163, 184, 0.6);
      }

      .extracted-urls a:hover,
      .extracted-urls a:focus {
        color: #1d4ed8;
        border-bottom-color: #1d4ed8;
      }

      .extracted-urls-empty {
        margin: 0;
        color: #64748b;
      }

      .digest-status {
        padding: 12px 16px;
        border-radius: 16px;
        background: rgba(79, 70, 229, 0.08);
        color: #3730a3;
        font-weight: 600;
        text-align: center;
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
    <div class="layout">
      <aside class="sidebar">
        <div>
          <h1>Retailer News Toolkit</h1>
          <p>
            Run the crawler to capture the newest updates and build a summary
            when you're ready to review the highlights.
          </p>
        </div>
        <div class="actions">
          <button id="run-crawler" type="button">
            <span aria-hidden="true">🕷️</span>
            Run crawler
          </button>
          <button id="run-summarizer" type="button">
            <span aria-hidden="true">📝</span>
            Build summary
          </button>
          <button id="customer-experience" type="button">
            <span aria-hidden="true">💡</span>
            Customer Experience
          </button>
        </div>
        <div class="status" id="status"></div>
      </aside>
      <main class="content">
        <section class="welcome">
          <h2>Welcome to our page for latest news within beauty industry</h2>
          <p>
            Explore curated updates and insights from across the beauty retail
            landscape. Build a fresh digest whenever you need an executive-ready
            overview of what matters most.
          </p>
        </section>
        <section class="digest-panel" id="digest-panel">
          <h3>Executive Digest</h3>
          <article class="digest-article" id="digest-article"></article>
          <div class="extracted-urls" id="extracted-urls">
            <h4>Extracted URLs</h4>
            <p class="extracted-urls-empty" id="extracted-urls-empty">
              No URLs have been stored yet. Run the crawler to populate this list.
            </p>
            <ul id="extracted-urls-list"></ul>
          </div>
        </section>
      </main>
    </div>
    <script>
      window.addEventListener("DOMContentLoaded", () => {

        const crawlerButton = document.getElementById("run-crawler");
        const summarizerButton = document.getElementById("run-summarizer");
        const customerExperienceButton = document.getElementById("customer-experience");
        const statusEl = document.getElementById("status");
        const digestPanel = document.getElementById("digest-panel");
        const digestArticle = document.getElementById("digest-article");
        const extractedUrlsSection = document.getElementById("extracted-urls");
        const extractedUrlsList = document.getElementById("extracted-urls-list");
        const extractedUrlsEmpty = document.getElementById("extracted-urls-empty");

        if (
          !crawlerButton ||
          !summarizerButton ||
          !customerExperienceButton ||
          !statusEl ||
          !digestPanel ||
          !digestArticle ||
          !extractedUrlsSection ||
          !extractedUrlsList ||
          !extractedUrlsEmpty
        ) {
          return;
        }

        const ALLOWED_TAGS = new Set([
          "P",
          "H1",
          "H2",
          "H3",
          "H4",
          "H5",
          "H6",
          "UL",
          "OL",
          "LI",
          "STRONG",
          "EM",
          "B",
          "I",
          "U",
          "BLOCKQUOTE",
          "HR",
          "BR",
          "SPAN",
          "DIV",
          "A",
        ]);

        const sanitizeNode = (node) => {
          if (node.nodeType === Node.TEXT_NODE) {
            return document.createTextNode(node.textContent ?? "");
          }

          if (node.nodeType !== Node.ELEMENT_NODE) {
            return null;
          }

          if (!ALLOWED_TAGS.has(node.tagName)) {
            return document.createTextNode(node.textContent ?? "");
          }

          const sanitized = document.createElement(node.tagName.toLowerCase());

          if (node.tagName === "A") {
            const href = node.getAttribute("href");
            if (href) {
              sanitized.setAttribute("href", href);
              sanitized.setAttribute("target", "_blank");
              sanitized.setAttribute("rel", "noopener noreferrer");
            }
          }

          node.childNodes.forEach((child) => {
            const sanitizedChild = sanitizeNode(child);
            if (sanitizedChild) {
              sanitized.appendChild(sanitizedChild);
            }
          });

          return sanitized;
        };

        const renderDigestArticle = (text) => {
          const normalized = (text ?? "").replace(/\\r/g, "");
          const containsMarkup = /<\\s*[a-z][^>]*>/i.test(normalized);

          digestArticle.innerHTML = "";

          if (containsMarkup) {
            const parser = new DOMParser();
            const parsed = parser.parseFromString(`<div>${normalized}</div>`, "text/html");
            const container = parsed.body.firstElementChild ?? parsed.body;
            const fragment = document.createDocumentFragment();

            container.childNodes.forEach((node) => {
              const sanitized = sanitizeNode(node);
              if (sanitized) {
                fragment.appendChild(sanitized);
              }
            });

            if (fragment.childNodes.length) {
              digestArticle.appendChild(fragment);
              return;
            }
          }

          const paragraphs = normalized
            .split(/\\n{2,}/)
            .map((paragraph) => paragraph.trim())
            .filter(Boolean);

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
        };

        const showDigestMessage = (message) => {
          digestPanel.classList.add("visible");
          digestArticle.innerHTML = "";
          const statusParagraph = document.createElement("p");
          statusParagraph.className = "digest-status";
          statusParagraph.textContent = message;
          digestArticle.appendChild(statusParagraph);
        };

        const renderExtractedUrls = (urls) => {
          extractedUrlsList.innerHTML = "";

          const urlEntries = Array.isArray(urls) ? urls : [];
          const uniqueUrls = Array.from(
            new Set(
              urlEntries
                .map((url) => (typeof url === "string" ? url.trim() : ""))
                .filter(Boolean),
            ),
          );

          if (!uniqueUrls.length) {
            extractedUrlsEmpty.hidden = false;
            return;
          }

          extractedUrlsEmpty.hidden = true;

          uniqueUrls.forEach((trimmedUrl) => {
            const listItem = document.createElement("li");
            const link = document.createElement("a");
            link.href = trimmedUrl;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            link.textContent = trimmedUrl;
            listItem.appendChild(link);
            extractedUrlsList.appendChild(listItem);
          });

          if (extractedUrlsList.children.length) {
            digestPanel.classList.add("visible");
          } else {
            extractedUrlsEmpty.hidden = false;
          }
        };

        const loadStoredDigest = async () => {
          try {
            const response = await fetch("/api/summaries/latest");
            if (!response.ok) {
              throw new Error(`Failed to load stored digest (${response.status})`);
            }

            const payload = await response.json();
            const digest =
              payload && typeof payload.digest === "string"
                ? payload.digest.trim()
                : "";

            if (digest) {
              renderDigestArticle(digest);
              digestPanel.classList.add("visible");
            }
          } catch (error) {
            console.error(error);
          }
        };

        const loadStoredUrls = async () => {
          try {
            const response = await fetch("/api/crawl/urls");
            if (!response.ok) {
              throw new Error(`Failed to load stored URLs (${response.status})`);
            }

            const payload = await response.json();
            renderExtractedUrls(payload && Array.isArray(payload.urls) ? payload.urls : []);
          } catch (error) {
            console.error(error);
          }
        };

        const callEndpoint = async (button, url, options) => {
          const statusMessage = options.statusMessage;
          const digestMessage = options.digestMessage;
          const completionDigestMessage = options.completionDigestMessage;
          const onSuccess = options.onSuccess;

          statusEl.textContent = statusMessage;
          showDigestMessage(digestMessage || statusMessage);
          button.disabled = true;

          try {
            const response = await fetch(url, { method: "POST" });
            if (!response.ok) {
              const message = await response.text();
              throw new Error(message || `Request failed with ${response.status}`);
            }

            const payload = await response.json();
            const completionMessage = `Completed at ${new Date().toLocaleTimeString()}`;
            statusEl.textContent = completionMessage;

            if (completionDigestMessage) {
              showDigestMessage(completionDigestMessage);
            }

            if (typeof onSuccess === "function") {
              onSuccess(payload);
            }
          } catch (error) {
            const errorMessage = `Error: ${error.message}`;
            statusEl.textContent = errorMessage;
            showDigestMessage(errorMessage);
          } finally {
            button.disabled = false;
          }
        };

        crawlerButton.addEventListener("click", () => {
          callEndpoint(crawlerButton, "/api/crawl", {
            statusMessage: "Running crawler...",
            digestMessage: "Crawler started. Gathering the latest updates...",
            completionDigestMessage: "Crawler completed.",
            onSuccess: (payload) => {
              const urls = payload && Array.isArray(payload.stored_urls)
                ? payload.stored_urls
                : [];
              renderExtractedUrls(urls);
            },
          });
        });

        summarizerButton.addEventListener("click", () => {
          callEndpoint(summarizerButton, "/api/summaries", {
            statusMessage: "Building digest...",
            digestMessage: "Building your executive digest...",
            onSuccess: (payload) => {
              const digest = payload && payload.digest ? payload.digest.trim() : "";
              renderDigestArticle(digest);
              digestPanel.classList.add("visible");
            },
          });
        });

        customerExperienceButton.addEventListener("click", () => {
          window.location.href = "/customer-experience";
        });

        loadStoredDigest();
        loadStoredUrls();
      });
    </script>
  </body>
</html>
"""


CUSTOMER_EXPERIENCE_HTML = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Retailer News | Customer Experience</title>
    <style>
      :root {
        color-scheme: light;
        font-family: "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
        background: #0f172a;
        color: #0f172a;
      }

      body {
        margin: 0;
        min-height: 100vh;
        background: linear-gradient(160deg, #fef3c7, #dbeafe 45%, #f8fafc 90%);
        display: flex;
        flex-direction: column;
      }

      header {
        padding: 48px 24px 32px;
        text-align: center;
        color: #0f172a;
      }

      header h1 {
        margin: 0 0 16px;
        font-size: clamp(2.5rem, 5vw, 3.25rem);
        letter-spacing: -0.02em;
      }

      header p {
        margin: 0;
        font-size: 1.1rem;
        color: #1e293b;
      }

      main {
        flex: 1;
        display: flex;
        justify-content: center;
        padding: 0 24px 48px;
      }

      .summary-card {
        width: min(900px, 100%);
        background: rgba(255, 255, 255, 0.9);
        border-radius: 28px;
        padding: 40px;
        box-shadow: 0 35px 80px rgba(15, 23, 42, 0.18);
        backdrop-filter: blur(12px);
      }

      .summary-card h2 {
        margin-top: 0;
        font-size: 1.75rem;
        color: #1d4ed8;
      }

      .summary-content {
        margin-top: 24px;
        display: grid;
        gap: 16px;
        color: #0f172a;
        line-height: 1.75;
        font-size: 1.05rem;
      }

      .summary-content p {
        margin: 0;
      }

      nav {
        position: fixed;
        top: 24px;
        left: 24px;
      }

      nav a {
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 10px 16px;
        border-radius: 9999px;
        background: rgba(15, 23, 42, 0.08);
        color: #0f172a;
        font-weight: 600;
        transition: background 0.2s ease, transform 0.2s ease;
      }

      nav a:hover,
      nav a:focus {
        background: rgba(37, 99, 235, 0.2);
        transform: translateY(-1px);
      }

      .status-message {
        margin-top: 16px;
        padding: 12px 16px;
        border-radius: 16px;
        background: rgba(37, 99, 235, 0.08);
        color: #1e3a8a;
        font-weight: 600;
      }

      @media (max-width: 720px) {
        header {
          padding: 32px 16px 24px;
        }

        .summary-card {
          padding: 28px 20px;
        }
      }
    </style>
  </head>
  <body>
    <nav>
      <a href="/">⬅️ Back to dashboard</a>
    </nav>
    <header>
      <h1>Welcome to the Customer Experience hub</h1>
      <p>Your spotlight on the most impactful CX developments across retail.</p>
    </header>
    <main>
      <section class="summary-card" aria-live="polite">
        <h2>Category Summary</h2>
        <div class="summary-content" id="summary-content">
          <p class="status-message">Loading the latest insights...</p>
        </div>
      </section>
    </main>
    <script>
      window.addEventListener("DOMContentLoaded", () => {
        const content = document.getElementById("summary-content");

        if (!content) {
          return;
        }

        const ALLOWED_TAGS = new Set([
          "P",
          "UL",
          "OL",
          "LI",
          "STRONG",
          "EM",
          "B",
          "I",
          "H1",
          "H2",
          "H3",
          "H4",
          "H5",
          "H6",
        ]);

        const sanitizeNode = (node) => {
          if (node.nodeType === Node.TEXT_NODE) {
            return document.createTextNode(node.textContent ?? "");
          }

          if (node.nodeType !== Node.ELEMENT_NODE) {
            return null;
          }

          if (!ALLOWED_TAGS.has(node.tagName)) {
            return document.createTextNode(node.textContent ?? "");
          }

          const sanitized = document.createElement(node.tagName.toLowerCase());

          node.childNodes.forEach((child) => {
            const sanitizedChild = sanitizeNode(child);
            if (sanitizedChild) {
              sanitized.appendChild(sanitizedChild);
            }
          });

          return sanitized;
        };

        const renderSummary = (summary) => {
          content.innerHTML = "";

          const normalized = (summary ?? "").trim();

          if (!normalized) {
            const fallback = document.createElement("p");
            fallback.textContent = "We don't have Customer Experience insights yet. Generate a summary to view fresh updates.";
            content.appendChild(fallback);
            return;
          }

          const parser = new DOMParser();
          const parsed = parser.parseFromString(`<div>${normalized}</div>`, "text/html");
          const container = parsed.body.firstElementChild ?? parsed.body;
          const fragment = document.createDocumentFragment();

          container.childNodes.forEach((node) => {
            const sanitized = sanitizeNode(node);
            if (sanitized) {
              fragment.appendChild(sanitized);
            }
          });

          if (!fragment.childNodes.length) {
            const fallback = document.createElement("p");
            fallback.textContent = normalized;
            fragment.appendChild(fallback);
          }

          content.appendChild(fragment);
        };

        const loadCustomerExperienceSummary = async () => {
          try {
            const response = await fetch("/api/summaries/latest");
            if (!response.ok) {
              throw new Error(`Failed to retrieve summary (${response.status})`);
            }

            const payload = await response.json();
            const categories = Array.isArray(payload?.categories) ? payload.categories : [];

            const target =
              categories.find((entry) =>
                typeof entry?.slug === "string" && entry.slug.toLowerCase() === "customer-experience",
              ) ||
              categories.find((entry) =>
                typeof entry?.name === "string" && entry.name.toLowerCase().includes("customer experience"),
              );

            renderSummary(target?.summary ?? "");
          } catch (error) {
            content.innerHTML = "";
            const failure = document.createElement("p");
            failure.className = "status-message";
            failure.textContent = error.message || "Unable to load Customer Experience insights right now.";
            content.appendChild(failure);
          }
        };

        loadCustomerExperienceSummary();
      });
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

    @app.get("/customer-experience", response_class=HTMLResponse)
    async def customer_experience() -> str:
        return CUSTOMER_EXPERIENCE_HTML

    return app


app = create_app()
