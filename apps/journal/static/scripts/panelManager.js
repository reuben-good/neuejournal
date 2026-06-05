class PanelManager {
  constructor() {
    this.openPanel = null; // currently open panel name
    this.panelCache = new Map(); // cache fetched HTML by URL
    this.isTransitioning = false;

    this.slideDuration = 320; // ms

    // Build the DOM scaffold once
    this._buildScaffold();
    this._bindGlobalEvents();
  }

  /** Creates the backdrop + panel shell in the DOM */
  _buildScaffold() {
    // Backdrop
    this.backdrop = document.createElement("div");
    this.backdrop.id = "panel-backdrop";
    Object.assign(this.backdrop.style, {
      position: "fixed",
      inset: "0",
      background: "rgba(0,0,0,0.35)",
      opacity: "0",
      transition: `opacity ${this.slideDuration}ms ease`,
      zIndex: "200",
      display: "none",
      backdropFilter: "blur(2px)",
    });

    // Panel shell
    this.panelEl = document.createElement("aside");
    this.panelEl.id = "slide-panel";
    this.panelEl.setAttribute("role", "dialog");
    this.panelEl.setAttribute("aria-modal", "true");

    // Content wrapper (what you inject into)
    this.contentEl = document.createElement("div");
    this.contentEl.id = "panel-content";
    this.panelEl.appendChild(this.contentEl);

    document.body.appendChild(this.backdrop);
    document.body.appendChild(this.panelEl);

    this._applyPanelStyles();

    // Re-apply styles on resize (desktop <-> mobile switch)
    window.addEventListener("resize", () => this._applyPanelStyles());
  }

  _isDesktop() {
    return window.innerWidth >= 768;
  }

  /** Sets position/size based on viewport */
  _applyPanelStyles() {
    const desktop = this._isDesktop();
    Object.assign(this.panelEl.style, {
      position: "fixed",
      zIndex: "201",
      background: "#fff",
      boxShadow: desktop
        ? "-4px 0 24px rgba(0,0,0,0.12)"
        : "0 -4px 24px rgba(0,0,0,0.12)",
      transition: `transform ${this.slideDuration}ms cubic-bezier(0.4,0,0.2,1)`,
      overflowY: "auto",

      // Desktop: right-side drawer
      ...(desktop
        ? {
            top: "0",
            right: "0",
            bottom: "0",
            left: "auto",
            width: "380px",
            height: "100dvh",
            borderRadius: "0",
            transform: "translateX(100%)",
          }
        : {
            // Mobile: bottom sheet
            bottom: "0",
            left: "0",
            right: "0",
            top: "auto",
            width: "100%",
            height: "auto",
            maxHeight: "85dvh",
            borderRadius: "16px 16px 0 0",
            transform: "translateY(100%)",
          }),
    });
  }

  _bindGlobalEvents() {
    // Close on backdrop click
    this.backdrop.addEventListener("click", () => this.close());

    // Close on ESC
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && this.openPanel) this.close();
    });
  }

  /** Open a panel by fetching `url` (unless already open) */
  async open(panelName, url) {
    if (this.isTransitioning) return;

    // Toggle: clicking the same button again closes it
    if (this.openPanel === panelName) {
      return this.close();
    }

    this.isTransitioning = true;
    this.openPanel = panelName;

    // Fetch (or use cache)
    const html = await this._fetch(url);
    this.contentEl.innerHTML = html;
    this._executeScripts();

    // Show backdrop
    this.backdrop.style.display = "block";
    requestAnimationFrame(() => {
      this.backdrop.style.opacity = "1";
    });

    // Slide in
    this._applyPanelStyles(); // ensure correct axis for current viewport
    requestAnimationFrame(() => {
      this.panelEl.style.transform = "translate(0, 0)";
    });

    await this._wait(this.slideDuration);
    this.isTransitioning = false;
  }

  /** Close the currently open panel */
  async close() {
    if (!this.openPanel || this.isTransitioning) return;
    this.isTransitioning = true;

    // Slide out
    const desktop = this._isDesktop();
    this.panelEl.style.transform = desktop
      ? "translateX(100%)"
      : "translateY(100%)";
    this.backdrop.style.opacity = "0";

    await this._wait(this.slideDuration);

    this.backdrop.style.display = "none";
    this.contentEl.innerHTML = "";
    this.openPanel = null;
    this.isTransitioning = false;
  }

  async _fetch(url) {
    if (this.panelCache.has(url)) return this.panelCache.get(url);
    try {
      const res = await fetch(url, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      });
      if (!res.ok) throw new Error(`Panel fetch failed: ${url}`);
      const html = await res.text();
      this.panelCache.set(url, html);
      return html;
    } catch (err) {
      console.error(err);
      return `<div class="panel-error">Failed to load panel.</div>`;
    }
  }

  /** Same script-execution pattern as your PageManager */
  _executeScripts() {
    this.contentEl.querySelectorAll("script").forEach((old) => {
      const script = document.createElement("script");
      script.textContent = old.textContent;
      document.body.appendChild(script);
      document.body.removeChild(script);
      old.remove();
    });
  }

  _wait(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  /** Bust cache for a panel URL (e.g. after a form submit) */
  invalidate(url) {
    this.panelCache.delete(url);
  }

  hideBackdropForDrag() {
    this.backdrop.style.display = "none";
    const desktop = this._isDesktop();
    this.panelEl.style.transition = "none"; // instant, no animation
    this.panelEl.style.transform = desktop
      ? "translateX(100%)"
      : "translateY(100%)";
  }

  showAfterDrag() {
    this.backdrop.style.display = "block";
    this.backdrop.style.opacity = "1";
    this.panelEl.style.transition = `transform ${this.slideDuration}ms cubic-bezier(0.4,0,0.2,1)`;
    this.panelEl.style.transform = "translate(0, 0)";
  }
}

// Singleton
const panelManager = new PanelManager();
window.panelManager = panelManager;
