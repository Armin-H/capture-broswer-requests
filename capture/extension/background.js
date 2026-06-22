const API_BASE = "http://localhost:8000";

chrome.runtime.onMessage.addListener((message, _sender, _sendResponse) => {
  if (!message || message.collector !== true) {
    return;
  }

  if (message.action === "recordFetch") {
    fetch(`${API_BASE}/record_fetch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(message.body),
    })
      .then((response) => response.json())
      .then((data) => console.log("Request ID:", data.id))
      .catch((error) => console.error("Error:", error));
    return;
  }

  if (message.action === "patchResponse") {
    fetch(`${API_BASE}/record_fetch/${message.recordId}/response`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(message.body),
    }).catch((error) => console.error("Error:", error));
  }
});
