(function () {
  "use strict";
  var TAG = "@@TAG@@";
  var VERSION = "@@VERSION@@";
  var BUNDLE = "@@BUNDLE_URL@@";
  var LOG = "[High School Sports Scores]";

  console.info(LOG + " loader " + VERSION);

  function retryUrl() {
    var join = BUNDLE.indexOf("?") === -1 ? "?" : "&";
    return BUNDLE + join + "r=" + Date.now();
  }

  function loadScript(url) {
    return new Promise(function (resolve, reject) {
      var script = document.createElement("script");
      script.src = url;
      script.async = false;
      script.onload = function () {
        resolve();
      };
      script.onerror = function () {
        reject(new Error("failed to load " + url));
      };
      (document.head || document.documentElement).appendChild(script);
    });
  }

  function defineFallback(reason) {
    console.error(LOG + " " + VERSION + ": " + reason);
    if (customElements.get(TAG)) {
      return;
    }
    class HsssCardLoadError extends HTMLElement {
      setConfig() {}
      getCardSize() {
        return 2;
      }
      connectedCallback() {
        if (this._hsssShown) {
          return;
        }
        this._hsssShown = true;
        this.style.display = "block";
        var card = document.createElement("ha-card");
        var body = document.createElement("div");
        body.style.padding = "16px";
        body.style.whiteSpace = "normal";
        body.style.color = "var(--primary-text-color)";
        var title = document.createElement("div");
        title.style.fontWeight = "700";
        title.style.marginBottom = "8px";
        title.textContent = "High School Sports Scores " + VERSION + " did not load";
        var detail = document.createElement("div");
        detail.textContent = reason;
        var hint = document.createElement("div");
        hint.style.marginTop = "8px";
        hint.textContent =
          "Reload this page. If this message stays, clear the browser cache for Home Assistant once.";
        body.appendChild(title);
        body.appendChild(detail);
        body.appendChild(hint);
        card.appendChild(body);
        this.appendChild(card);
      }
    }
    customElements.define(TAG, HsssCardLoadError);
  }

  function afterLoad(url) {
    return loadScript(url).then(function () {
      if (!customElements.get(TAG)) {
        throw new Error("card script ran but did not register " + TAG);
      }
      console.info(LOG + " defined " + TAG + " (" + VERSION + ")");
    });
  }

  function start() {
    return afterLoad(BUNDLE).catch(function (err) {
      console.error(LOG + " " + VERSION + ": " + (err && err.message ? err.message : err));
      return afterLoad(retryUrl()).catch(function (retryErr) {
        defineFallback(
          retryErr && retryErr.message ? retryErr.message : "card script did not load"
        );
      });
    });
  }

  var pending = window.__hsssLoaderPromise;
  if (pending && pending.tag === TAG) {
    pending.promise.then(
      function () {
        if (!customElements.get(TAG)) {
          defineFallback("card script did not register " + TAG);
        }
      },
      function () {
        if (!customElements.get(TAG)) {
          defineFallback("card script did not load");
        }
      }
    );
    return;
  }
  window.__hsssLoaderPromise = { tag: TAG, promise: start() };
})();
