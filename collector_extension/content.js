console.log("Data Collector Running");

var originalFetch = window.fetch;

window.fetch = function() {
    const [url, options] = arguments;
    console.log("Request made to:", url);
    console.log("Request options:", options);

    const data = {
        url : url,
        options : options
    }
    originalFetch("http://localhost:8000/record_fetch",{
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => console.log(data))
    .catch(error => console.error("Error:", error));
    return originalFetch.apply(this, arguments);
};