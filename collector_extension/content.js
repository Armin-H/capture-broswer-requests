console.log("Data Collector Running");

var originalFetch = window.fetch;

window.fetch = async function() {
    const [url, options] = arguments;
    const recordId = crypto.randomUUID();

    const data = {
        id: recordId,
        destination_url: url,
        request_timestamp: Date.now(),
        source_url: window.location.href,
        options: options
    };
    
    originalFetch("http://localhost:8000/record_fetch", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => console.log("Request ID:", data.id))
    .catch(error => console.error("Error:", error));

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
        timestamp: Date.now()
    };

    originalFetch(`http://localhost:8000/record_fetch/${recordId}/response`, {
        method: "PATCH",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(responseData)
    }).catch(error => console.error("Error:", error));

    return response;
};