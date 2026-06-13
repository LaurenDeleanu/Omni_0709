(function () {
  var config = window.SuccessCoreWidget || {};
  var appUrl = config.appUrl || "http://localhost:3000";
  var tenantId = config.tenantId || "default";
  var theme = config.theme || "dark";
  var position = config.position || "bottom-right";
  var locale = config.locale || "en";

  var container = document.createElement("div");
  container.id = "successcore-embed-root";
  container.setAttribute("data-sc-theme", theme);

  var btn = document.createElement("div");
  btn.id = "successcore-embed-btn";
  btn.innerHTML = '\uD83D\uDCAC';
  btn.title = "SuccessCore AI Assistant";

  var iframe = document.createElement("iframe");
  iframe.id = "successcore-embed-iframe";
  iframe.src =
    appUrl +
    "/" +
    locale +
    "/embed/chat?tenant=" +
    encodeURIComponent(tenantId) +
    "&theme=" +
    encodeURIComponent(theme);
  iframe.allow = "microphone";
  iframe.style.border = "none";
  iframe.style.display = "none";

  var style = document.createElement("style");
  style.textContent =
    "#successcore-embed-root{position:fixed;z-index:2147483647;font-family:Inter,system-ui,-apple-system,sans-serif}" +
    '#successcore-embed-btn{position:fixed;z-index:2147483647;width:56px;height:56px;border-radius:50%;background:linear-gradient(135deg,#7c3aed,#6366f1,#d946ef);box-shadow:0 4px 24px rgba(124,58,237,0.5);display:flex;align-items:center;justify-content:center;font-size:24px;cursor:pointer;transition:transform .2s,box-shadow .2s;user-select:none}' +
    "#successcore-embed-btn:hover{transform:scale(1.1);box-shadow:0 6px 32px rgba(124,58,237,0.6)}" +
    "#successcore-embed-iframe{position:fixed;z-index:2147483646;width:400px;height:560px;max-height:calc(100vh - 100px);border-radius:16px;overflow:hidden;box-shadow:0 12px 48px rgba(0,0,0,0.4);transition:opacity .25s,transform .25s}" +
    '#successcore-embed-iframe[data-visible="true"]{display:block;opacity:1;transform:translateY(0)}' +
    '#successcore-embed-iframe[data-visible="false"]{display:block;opacity:0;transform:translateY(12px);pointer-events:none}' +
    "[data-sc-position=bottom-right] #successcore-embed-btn{bottom:24px;right:24px}" +
    "[data-sc-position=bottom-right] #successcore-embed-iframe{bottom:96px;right:24px}" +
    "[data-sc-position=bottom-left] #successcore-embed-btn{bottom:24px;left:24px}" +
    "[data-sc-position=bottom-left] #successcore-embed-iframe{bottom:96px;left:24px}";

  document.head.appendChild(style);

  var isOpen = false;

  function openChat() {
    isOpen = true;
    iframe.setAttribute("data-visible", "true");
    iframe.style.display = "block";
    btn.style.display = "none";
  }

  function closeChat() {
    isOpen = false;
    iframe.setAttribute("data-visible", "false");
    var onTransitionEnd = function () {
      if (!isOpen) {
        iframe.style.display = "none";
        btn.style.display = "flex";
      }
      iframe.removeEventListener("transitionend", onTransitionEnd);
    };
    iframe.addEventListener("transitionend", onTransitionEnd);
  }

  btn.addEventListener("click", openChat);

  window.addEventListener("message", function (event) {
    if (event.data && event.data.type === "successcore-close") {
      closeChat();
    }
  });

  container.setAttribute("data-sc-position", position);
  container.appendChild(btn);
  container.appendChild(iframe);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      document.body.appendChild(container);
    });
  } else {
    document.body.appendChild(container);
  }
})();
