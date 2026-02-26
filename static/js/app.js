const form = document.getElementById("uploadForm");
const progressContainer = document.getElementById("progressContainer");
const progressBar = document.getElementById("progressBar");
const resultsSection = document.getElementById("resultsSection");
const resultsContainer = document.getElementById("resultsContainer");

form.addEventListener("submit", async function(e) {
    e.preventDefault();

    const formData = new FormData(form);

    progressContainer.classList.remove("hidden");
    progressBar.style.width = "100%";

    const response = await fetch("/analyze", {
        method: "POST",
        body: formData
    });

    const data = await response.json();

    progressContainer.classList.add("hidden");
    progressBar.style.width = "0%";

    displayResults(data);
});

function displayResults(data) {
    document.getElementById("fieldsCount").innerText = data.findings.length;
    document.getElementById("docType").innerText = data.document_type;

    const riskElement = document.getElementById("riskLevel");
    riskElement.innerText = data.risk_level;
    riskElement.className = "risk-" + data.risk_level.toLowerCase();

    resultsSection.classList.remove("hidden");
    resultsContainer.innerHTML = "";

    data.findings.forEach(field => {
        const div = document.createElement("div");
        div.innerHTML = `<strong>${field.type}:</strong> ${field.value}`;
        resultsContainer.appendChild(div);
    });
}