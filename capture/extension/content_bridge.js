// Isolated world: forwards payloads from MAIN-world fetch hook to the service worker
// so localhost requests are not subject to the page CSP.
const COLLECTOR_MSG = "data-collector-fetch";

window.addEventListener("message", (ev) => {
  if (ev.source !== window) {
    return;
  }
  const d = ev.data;
  if (!d || d.type !== COLLECTOR_MSG) {
    return;
  }

  if (d.action === "recordFetch") {
    chrome.runtime.sendMessage({
      collector: true,
      action: "recordFetch",
      body: d.body,
    });
    return;
  }

  if (d.action === "patchResponse") {
    chrome.runtime.sendMessage({
      collector: true,
      action: "patchResponse",
      recordId: d.recordId,
      body: d.body,
    });
  }
});
