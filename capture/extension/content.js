console.log("Data Collector Running");

// Must match content_bridge.js (postMessage protocol).
const COLLECTOR_MSG = "data-collector-fetch";

/** postMessage uses structured clone — AbortSignal, ReadableStream, etc. are not cloneable. */
function sanitizeFetchInit(init, input) {
  let out = {};
  if (input instanceof Request) {
    out = {
      method: input.method,
      headers: Object.fromEntries(input.headers.entries()),
      mode: input.mode,
      credentials: input.credentials,
      cache: input.cache,
      redirect: input.redirect,
      referrer: input.referrer,
      integrity: input.integrity,
      keepalive: input.keepalive,
    };
  }
  if (init && typeof init === "object") {
    out = { ...out, ...init };
  }
  delete out.signal;

  if (out.headers instanceof Headers) {
    out.headers = Object.fromEntries(out.headers.entries());
  }

  if (out.body instanceof ReadableStream) {
    out.body = "[ReadableStream]";
  } else if (out.body instanceof FormData) {
    try {
      const obj = {};
      for (const [k, v] of out.body.entries()) {
        obj[k] = v instanceof Blob ? `[Blob: ${v.size} bytes]` : String(v);
      }
      out.body = obj;
    } catch {
      out.body = "[FormData]";
    }
  } else if (out.body instanceof Blob) {
    out.body = `[Blob: ${out.body.size} bytes]`;
  } else if (out.body instanceof URLSearchParams) {
    out.body = out.body.toString();
  }

  return Object.keys(out).length ? out : undefined;
}

function destinationUrlString(input) {
  if (typeof input === "string") {
    return input;
  }
  if (input instanceof Request) {
    return input.url;
  }
  return String(input);
}

function sendRecordFetch(body) {
  window.postMessage(
    { type: COLLECTOR_MSG, action: "recordFetch", body },
    "*"
  );
}

function sendPatchResponse(recordId, body) {
  window.postMessage(
    { type: COLLECTOR_MSG, action: "patchResponse", recordId, body },
    "*"
  );
}

var originalFetch = window.fetch;

window.fetch = async function () {
  const input = arguments[0];
  const init = arguments[1];
  const recordId = crypto.randomUUID();

  const data = {
    id: recordId,
    destination_url: destinationUrlString(input),
    request_timestamp: Date.now(),
    source_url: window.location.href,
    options: sanitizeFetchInit(init, input),
  };

  sendRecordFetch(data);

  const response = await originalFetch.apply(this, arguments);

  const resClone = response.clone();
  let resBody = null;
  try {
    resBody = await resClone.text();
  } catch (error) {
    console.error("Error getting response body:", error);
  }

  const responseData = {
    status: response.status,
    statusText: response.statusText,
    ok: response.ok,
    redirected: response.redirected,
    type: response.type,
    url: response.url,
    bodyUsed: response.bodyUsed,
    headers: Object.fromEntries(response.headers.entries()),
    body: resBody,
    timestamp: Date.now(),
  };

  sendPatchResponse(recordId, responseData);

  return response;
};
