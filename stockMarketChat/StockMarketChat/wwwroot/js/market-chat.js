window.marketChat = {
  scrollToBottom: function (element) {
    if (!element) return;
    element.scrollTop = element.scrollHeight;
  },

  /**
   * Browser-side ticker cache (localStorage). Survives app restarts and browser reloads.
   * Prefer localStorage over cookies: quote payloads exceed typical cookie size limits.
   */
  tickerCacheKey: "marketdesk.ticker.v1",

  getTickerCache: function () {
    try {
      var raw = localStorage.getItem(window.marketChat.tickerCacheKey);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      if (!parsed || !parsed.expiresAt || !parsed.items || !parsed.items.length) return null;
      if (Date.parse(parsed.expiresAt) <= Date.now()) {
        localStorage.removeItem(window.marketChat.tickerCacheKey);
        return null;
      }
      return parsed;
    } catch (e) {
      return null;
    }
  },

  setTickerCache: function (payload) {
    try {
      if (!payload || !payload.items || !payload.items.length) return false;
      localStorage.setItem(
        window.marketChat.tickerCacheKey,
        JSON.stringify({
          items: payload.items,
          cachedAt: payload.cachedAt,
          expiresAt: payload.expiresAt,
          source: payload.source || "browser"
        })
      );
      return true;
    } catch (e) {
      return false;
    }
  },

  clearTickerCache: function () {
    try {
      localStorage.removeItem(window.marketChat.tickerCacheKey);
    } catch (e) {
      /* ignore */
    }
  }
};
