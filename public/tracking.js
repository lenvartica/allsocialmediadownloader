/* Loads Meta Pixel, GA4, TikTok Pixel and Clarity ONLY if an ID is set in config.js.
   Respects Do Not Track / Global Privacy Control. */
(function () {
  var c = window.SITE_CONFIG || {};
  var dnt = navigator.doNotTrack === "1" || window.doNotTrack === "1" || navigator.globalPrivacyControl === true;
  window.track = function () {};
  if (dnt) return;

  var queue = [];
  window.track = function (name, params) {
    params = params || {};
    try { if (window.fbq && c.META_PIXEL_ID) fbq("trackCustom", name, params); } catch (e) {}
    try { if (window.gtag && c.GA4_ID) gtag("event", name, params); } catch (e) {}
    try { if (window.ttq && c.TIKTOK_PIXEL_ID) ttq.track(name, params); } catch (e) {}
  };

  /* Meta Pixel */
  if (c.META_PIXEL_ID) {
    !function (f, b, e, v, n, t, s) {
      if (f.fbq) return; n = f.fbq = function () { n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments); };
      if (!f._fbq) f._fbq = n; n.push = n; n.loaded = !0; n.version = "2.0"; n.queue = [];
      t = b.createElement(e); t.async = !0; t.src = v; s = b.getElementsByTagName(e)[0]; s.parentNode.insertBefore(t, s);
    }(window, document, "script", "https://connect.facebook.net/en_US/fbevents.js");
    fbq("init", c.META_PIXEL_ID);
    fbq("track", "PageView");
  }

  /* Google Analytics 4 */
  if (c.GA4_ID) {
    var g = document.createElement("script"); g.async = true;
    g.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(c.GA4_ID);
    document.head.appendChild(g);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { dataLayer.push(arguments); };
    gtag("js", new Date()); gtag("config", c.GA4_ID, { anonymize_ip: true });
  }

  /* TikTok Pixel */
  if (c.TIKTOK_PIXEL_ID) {
    !function (w, d, t) {
      w.TiktokAnalyticsObject = t; var ttq = w[t] = w[t] || [];
      ttq.methods = ["page", "track", "identify", "instances", "debug", "on", "off", "once", "ready", "alias", "group", "enableCookie", "disableCookie"];
      ttq.setAndDefer = function (t, e) { t[e] = function () { t.push([e].concat(Array.prototype.slice.call(arguments, 0))); }; };
      for (var i = 0; i < ttq.methods.length; i++) ttq.setAndDefer(ttq, ttq.methods[i]);
      ttq.load = function (e) {
        var n = document.createElement("script"); n.async = !0; n.src = "https://analytics.tiktok.com/i18n/pixel/events.js?sdkid=" + e + "&lib=" + t;
        var s = document.getElementsByTagName("script")[0]; s.parentNode.insertBefore(n, s);
      };
      ttq.load(c.TIKTOK_PIXEL_ID); ttq.page();
    }(window, document, "ttq");
  }

  /* Microsoft Clarity */
  if (c.CLARITY_ID) {
    (function (c2, l, a, r, i, t, y) {
      c2[a] = c2[a] || function () { (c2[a].q = c2[a].q || []).push(arguments); };
      t = l.createElement(r); t.async = 1; t.src = "https://www.clarity.ms/tag/" + i;
      y = l.getElementsByTagName(r)[0]; y.parentNode.insertBefore(t, y);
    })(window, document, "clarity", "script", c.CLARITY_ID);
  }

  /* Auto events */
  document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("form");
    if (form) form.addEventListener("submit", function () {
      var tab = document.querySelector(".tab.active");
      window.track("FetchVideo", { platform: tab ? tab.dataset.id : "unknown" });
    });
    ["dlNormal", "dlHD"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener("click", function () {
        var tab = document.querySelector(".tab.active");
        window.track("DownloadClick", { quality: id === "dlHD" ? "hd" : "normal", platform: tab ? tab.dataset.id : "unknown" });
        try { if (window.fbq && c.META_PIXEL_ID) fbq("track", "Lead"); } catch (e) {}
      });
    });
  });
})();
