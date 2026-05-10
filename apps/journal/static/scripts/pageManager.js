/**
 * Page Manager - Handles loading and navigation of paired pages
 * Pages always come in pairs (left and right) that change together
 */

class PageManager {
  constructor(
    leftPageSelector = "#left-page",
    rightPageSelector = "#right-page",
  ) {
    this.leftPageEl = document.querySelector(leftPageSelector);
    this.rightPageEl = document.querySelector(rightPageSelector);
    this.currentPageIndex = 0;
    this.pages = [];
    this.isTransitioning = false;
    this.pageCache = new Map();

    // Animation config
    this.fadeOutDuration = 300;
    this.fadeInDuration = 400;
  }

  /**
   * Load pages from an array of page pair definitions
   * Each page pair can be defined in two ways:
   * 1. Static: { left: 'page-name', right: 'page-name' } - loads from /static/pages/
   * 2. Dynamic (Django templates): { leftUrl: '/api/page/left', rightUrl: '/api/page/right' }
   * 3. Mixed: Combine static paths with dynamic URLs as needed
   */
  async loadPages(pagePairs, basePath = "/static/pages/") {
    this.pages = pagePairs.map((pair, index) => {
      const pageData = {
        index,
        leftContent: null,
        rightContent: null,
      };

      // Determine how to load left page
      if (pair.leftUrl) {
        pageData.leftUrl = pair.leftUrl;
        pageData.left = pair.left || "dynamic";
      } else {
        pageData.left = pair.left;
        pageData.leftPath = `${basePath}${pair.left}.html`;
      }

      // Determine how to load right page
      if (pair.rightUrl) {
        pageData.rightUrl = pair.rightUrl;
        pageData.right = pair.right || "dynamic";
      } else {
        pageData.right = pair.right;
        pageData.rightPath = `${basePath}${pair.right}.html`;
      }

      return pageData;
    });

    // Preload only static pages (skip dynamic pages for lazy loading)
    for (const page of this.pages) {
      if (page.leftPath) {
        page.leftContent = await this._fetchPage(page.leftPath);
      }

      if (page.rightPath) {
        page.rightContent = await this._fetchPage(page.rightPath);
      }
    }

    // Render the first page pair
    await this.goToPage(0);
  }

  /**
   * Fetch a static page HTML file
   */
  async _fetchPage(path) {
    if (this.pageCache.has(path)) {
      return this.pageCache.get(path);
    }

    try {
      const response = await fetch(path);
      if (!response.ok) {
        throw new Error(`Failed to load page: ${path}`);
      }
      const html = await response.text();
      this.pageCache.set(path, html);
      return html;
    } catch (error) {
      console.error(`Error loading page ${path}:`, error);
      return `<div class="page-error"><p>Error loading page</p></div>`;
    }
  }

  /**
   * Fetch a dynamic page from a Django template endpoint
   */
  async _fetchDynamicPage(url) {
    if (this.pageCache.has(url)) {
      return this.pageCache.get(url);
    }

    try {
      const response = await fetch(url, {
        method: "GET",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "Content-Type": "application/json",
        },
        credentials: "same-origin", // Include CSRF token in cookies
      });

      if (!response.ok) {
        throw new Error(`Failed to load dynamic page: ${url}`);
      }

      const html = await response.text();
      this.pageCache.set(url, html);
      return html;
    } catch (error) {
      console.error(`Error loading dynamic page ${url}:`, error);
      return `<div class="page-error"><p>Error loading page</p></div>`;
    }
  }

  /**
   * Navigate to a specific page pair by index
   */
  async goToPage(index) {
    if (index < 0 || index >= this.pages.length) {
      console.warn(`Page index ${index} out of bounds`);
      return;
    }

    if (this.isTransitioning) {
      console.warn("Page transition in progress");
      return;
    }

    this.isTransitioning = true;
    const page = this.pages[index];

    // Fetch dynamic pages if they haven't been loaded yet (lazy loading)
    if (page.leftUrl && page.leftContent === null) {
      page.leftContent = await this._fetchDynamicPage(page.leftUrl);
    }
    if (page.rightUrl && page.rightContent === null) {
      page.rightContent = await this._fetchDynamicPage(page.rightUrl);
    }

    // Fade out
    await this._fadeOut();

    // Update content
    const leftContent = this.leftPageEl.querySelector(".page-content");
    const rightContent = this.rightPageEl.querySelector(".page-content");

    if (leftContent) {
      leftContent.innerHTML = page.leftContent;
    }
    if (rightContent) {
      rightContent.innerHTML = page.rightContent;
    }

    this.currentPageIndex = index;

    // Trigger any scripts in the loaded pages
    this._executeScripts();

    // Fade in
    await this._fadeIn();

    this.isTransitioning = false;

    // Dispatch event
    this._dispatchPageChangeEvent(index);
  }

  /**
   * Navigate to the next page pair
   */
  async nextPage() {
    const nextIndex = this.currentPageIndex + 1;
    if (nextIndex < this.pages.length) {
      await this.goToPage(nextIndex);
      return true;
    }
    return false;
  }

  /**
   * Navigate to the previous page pair
   */
  async previousPage() {
    const prevIndex = this.currentPageIndex - 1;
    if (prevIndex >= 0) {
      await this.goToPage(prevIndex);
      return true;
    }
    return false;
  }

  /**
   * Fade out current page content only
   */
  async _fadeOut() {
    return new Promise((resolve) => {
      const leftContent = this.leftPageEl.querySelector(".page-content");
      const rightContent = this.rightPageEl.querySelector(".page-content");

      if (leftContent) {
        leftContent.style.opacity = "0";
        leftContent.style.transition = `opacity ${this.fadeOutDuration}ms ease-out`;
      }
      if (rightContent) {
        rightContent.style.opacity = "0";
        rightContent.style.transition = `opacity ${this.fadeOutDuration}ms ease-out`;
      }

      setTimeout(resolve, this.fadeOutDuration);
    });
  }

  /**
   * Fade in new page content
   */
  async _fadeIn() {
    return new Promise((resolve) => {
      const leftContent = this.leftPageEl.querySelector(".page-content");
      const rightContent = this.rightPageEl.querySelector(".page-content");

      if (leftContent) {
        leftContent.style.opacity = "1";
        leftContent.style.transition = `opacity ${this.fadeInDuration}ms ease-in`;
      }
      if (rightContent) {
        rightContent.style.opacity = "1";
        rightContent.style.transition = `opacity ${this.fadeInDuration}ms ease-in`;
      }

      setTimeout(resolve, this.fadeInDuration);
    });
  }

  /**
   * Execute any scripts in the loaded content
   */
  _executeScripts() {
    const leftContent = this.leftPageEl.querySelector(".page-content");
    const rightContent = this.rightPageEl.querySelector(".page-content");

    const scripts = [];
    if (leftContent) {
      scripts.push(...leftContent.querySelectorAll("script"));
    }
    if (rightContent) {
      scripts.push(...rightContent.querySelectorAll("script"));
    }

    scripts.forEach((oldScript) => {
      const newScript = document.createElement("script");
      Array.from(oldScript.attributes).forEach((attr) => {
        newScript.setAttribute(attr.name, attr.value);
      });
      newScript.textContent = oldScript.textContent;
      oldScript.parentNode.replaceChild(newScript, oldScript);
    });
  }

  /**
   * Dispatch custom event when page changes
   */
  _dispatchPageChangeEvent(index) {
    const event = new CustomEvent("pagechange", {
      detail: {
        currentIndex: index,
        totalPages: this.pages.length,
        currentPagePair: this.pages[index],
      },
    });
    document.dispatchEvent(event);
  }

  /**
   * Get the current page index
   */
  getCurrentPageIndex() {
    return this.currentPageIndex;
  }

  /**
   * Get the total number of page pairs
   */
  getTotalPages() {
    return this.pages.length;
  }

  /**
   * Check if there's a next page
   */
  hasNextPage() {
    return this.currentPageIndex + 1 < this.pages.length;
  }

  /**
   * Check if there's a previous page
   */
  hasPreviousPage() {
    return this.currentPageIndex > 0;
  }

  /**
   * Set animation durations (in milliseconds)
   */
  setAnimationDurations(fadeOutDuration, fadeInDuration) {
    this.fadeOutDuration = fadeOutDuration;
    this.fadeInDuration = fadeInDuration;
  }

  /**
   * Refresh a specific page pair's content (useful for dynamic content)
   * Pass the page index to reload its content
   */
  async refreshPage(index) {
    if (index < 0 || index >= this.pages.length) {
      console.warn(`Page index ${index} out of bounds`);
      return;
    }

    const page = this.pages[index];

    // Refresh left page
    if (page.leftPath) {
      page.leftContent = await this._fetchPage(page.leftPath);
    } else if (page.leftUrl) {
      page.leftContent = await this._fetchDynamicPage(page.leftUrl);
    }

    // Refresh right page
    if (page.rightPath) {
      page.rightContent = await this._fetchPage(page.rightPath);
    } else if (page.rightUrl) {
      page.rightContent = await this._fetchDynamicPage(page.rightUrl);
    }

    // If this is the current page, re-render it
    if (index === this.currentPageIndex) {
      const leftContent = this.leftPageEl.querySelector(".page-content");
      const rightContent = this.rightPageEl.querySelector(".page-content");

      if (leftContent) {
        leftContent.innerHTML = page.leftContent;
      }
      if (rightContent) {
        rightContent.innerHTML = page.rightContent;
      }

      // Re-execute scripts
      this._executeScripts();
    }
  }

  /**
   * Clear the page cache (useful when you need to force refresh)
   */
  clearCache() {
    this.pageCache.clear();
  }

  /**
   * Reload all pages from their sources
   */
  async reloadAllPages() {
    for (let i = 0; i < this.pages.length; i++) {
      const page = this.pages[i];

      if (page.leftPath) {
        page.leftContent = await this._fetchPage(page.leftPath);
      } else if (page.leftUrl) {
        page.leftContent = await this._fetchDynamicPage(page.leftUrl);
      }

      if (page.rightPath) {
        page.rightContent = await this._fetchPage(page.rightPath);
      } else if (page.rightUrl) {
        page.rightContent = await this._fetchDynamicPage(page.rightUrl);
      }
    }

    // Re-render current page
    await this.goToPage(this.currentPageIndex);
  }
}

// Export for use in modules
if (typeof module !== "undefined" && module.exports) {
  module.exports = PageManager;
}
