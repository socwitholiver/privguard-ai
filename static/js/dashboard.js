async function loadDashboard() {
    const res = await fetch("/dashboard-data");
    const data = await res.json();

    document.getElementById("documentsScanned").innerText = data.documents_scanned;
    document.getElementById("sensitiveEntities").innerText = data.sensitive_entities;
    document.getElementById("complianceScore").innerText = data.compliance_score + "%";

    const ctx = document.getElementById("riskChart").getContext("2d");

    new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["High", "Medium", "Low"],
            datasets: [{
                data: [
                    data.risk_distribution.High,
                    data.risk_distribution.Medium,
                    data.risk_distribution.Low
                ]
            }]
        }
    });

    const tableBody = document.querySelector("#scanTable tbody");
    tableBody.innerHTML = "";

    data.recent_scans.forEach(scan => {
        tableBody.innerHTML += `
            <tr>
                <td>${scan.file}</td>
                <td>${scan.risk}</td>
                <td>${scan.entities}</td>
                <td>${scan.timestamp}</td>
            </tr>
        `;
    });
}

setInterval(loadDashboard, 3000);
loadDashboard();