const riskWeights = {
    high: ["national_ids", "kra_pins", "passwords", "financial_info"],
    medium: ["phone_numbers", "emails"],
    low: ["personal_names"],
};

const findingLabels = {
    national_ids: "National ID",
    phone_numbers: "Phone Number",
    emails: "Email",
    kra_pins: "KRA PIN",
    passwords: "Password",
    financial_info: "Financial Data",
    personal_names: "Personal Name",
};

const screenTitles = {
    dashboard: "Dashboard",
    scan: "Scan Document",
    vault: "Secure Vault",
    reports: "Risk Reports",
    settings: "Settings",
};

const icons = {
    moon: '<svg viewBox="0 0 24 24"><path d="M12.2 2a8.98 8.98 0 0 0 0 18c3.87 0 7.15-2.45 8.42-5.87A8 8 0 0 1 12.2 2z"></path></svg>',
    sun: '<svg viewBox="0 0 24 24"><path d="M6.76 4.84 5.35 3.43 3.93 4.85l1.41 1.41 1.42-1.42zM1 13h3v-2H1v2zm10-9h2V1h-2v3zm7.66 2.26 1.41-1.41-1.41-1.42-1.42 1.42 1.42 1.41zM17.24 19.16l1.42 1.41 1.41-1.41-1.41-1.42-1.42 1.42zM20 11v2h3v-2h-3zM11 20h2v3h-2v-3zM4.84 17.24l-1.41 1.42 1.41 1.41 1.41-1.41-1.41-1.42zM12 6a6 6 0 1 0 0 12 6 6 0 0 0 0-12z"></path></svg>',
};

let workspaceState = { user: null };

function escapeHtml(value) {
    return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function badgeClass(value) {
    const normalized = String(value || "").toLowerCase();
    if (normalized.includes("high")) return "pg-badge-risk-high";
    if (normalized.includes("medium")) return "pg-badge-risk-medium";
    if (normalized.includes("encrypt") || normalized.includes("redact") || normalized.includes("low") || normalized.includes("protect")) return "pg-badge-risk-low";
    return "pg-badge-risk-safe";
}

function detectionRiskLevel(type) {
    if (riskWeights.high.includes(type)) return { label: "High Risk", css: "pg-badge-risk-high" };
    if (riskWeights.medium.includes(type)) return { label: "Medium Risk", css: "pg-badge-risk-medium" };
    return { label: "Low Risk", css: "pg-badge-risk-low" };
}

function displayStatusLabel(label) {
    return label === "Allowed" ? "Stored" : label;
}

function formatFindingType(type) {
    return findingLabels[type] || String(type || "unknown").replace(/_/g, " ");
}

function formatTimestamp(value) {
    if (!value) return "-";
    const normalized = String(value).replace(" ", "T");
    const date = new Date(normalized.endsWith("Z") ? normalized : `${normalized}Z`);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleString();
}

function getInitials(value) {
    const source = String(value || "U").trim();
    if (!source) return "U";
    const parts = source.split(/\s+/).filter(Boolean).slice(0, 2);
    return parts.map((part) => part[0].toUpperCase()).join("") || source[0].toUpperCase();
}

async function api(url, options = {}) {
    const response = await fetch(url, options);
    if (response.status === 401 || response.status === 423) {
        window.location.href = "/login";
        return null;
    }
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Request failed");
    return data;
}

function setActiveScreen(target) {
    document.querySelectorAll(".pg-screen").forEach((screen) => {
        screen.classList.toggle("active", screen.dataset.screen === target);
    });
    document.querySelectorAll(".pg-nav-btn").forEach((button) => {
        button.classList.toggle("active", button.dataset.screen === target);
    });
    const title = document.getElementById("topSectionLabel");
    if (title) title.textContent = screenTitles[target] || "Workspace";
}

function openPicker() {
    document.getElementById("fileInput").click();
}

function updateSelectedFile(file) {
    document.getElementById("selectedFileLabel").textContent = file ? `Selected file: ${file.name}` : "No document selected yet.";
}

function setAvatar(imageId, fallbackId, avatarUrl, displayName) {
    const image = document.getElementById(imageId);
    const fallback = document.getElementById(fallbackId);
    if (!image || !fallback) return;

    if (avatarUrl) {
        image.src = avatarUrl;
        image.alt = `${displayName} avatar`;
        image.classList.remove("hidden");
        fallback.classList.add("hidden");
        return;
    }

    image.classList.add("hidden");
    image.removeAttribute("src");
    fallback.classList.remove("hidden");
    fallback.textContent = getInitials(displayName);
}

function applyTheme(theme) {
    const normalized = theme === "light" ? "light" : "dark";
    document.body.dataset.theme = normalized;

    const themeToggleIcon = document.getElementById("themeToggleIcon");
    const themeToggleLabel = document.getElementById("themeToggleLabel");
    const settingsThemeLabel = document.getElementById("settingsThemeLabel");
    const settingsThemeStatus = document.getElementById("settingsThemeStatus");
    const settingsThemeToggle = document.getElementById("settingsThemeToggle");

    if (themeToggleIcon) themeToggleIcon.innerHTML = normalized === "light" ? icons.moon : icons.sun;
    if (themeToggleLabel) themeToggleLabel.textContent = normalized === "light" ? "Dark mode" : "Light mode";
    if (settingsThemeLabel) settingsThemeLabel.textContent = normalized === "light" ? "Light mode active" : "Dark mode active";
    if (settingsThemeStatus) settingsThemeStatus.textContent = normalized === "light" ? "Light mode active" : "Dark mode active";
    if (settingsThemeToggle) settingsThemeToggle.setAttribute("aria-pressed", String(normalized === "light"));
}

function renderUser(user) {
    if (!user) return;
    workspaceState.user = user;

    const displayName = user.display_name || user.username || "Local Operator";
    const username = user.username || "operator";
    const avatarUrl = user.avatar_url || "";
    const theme = user.theme || document.body.dataset.theme || "dark";

    const topUserDisplayName = document.getElementById("topUserDisplayName");
    const topUserSubtext = document.getElementById("topUserSubtext");
    const settingsProfileName = document.getElementById("settingsProfileName");
    const settingsProfileHandle = document.getElementById("settingsProfileHandle");
    const profileDisplayName = document.getElementById("profileDisplayName");

    if (topUserDisplayName) topUserDisplayName.textContent = displayName;
    if (topUserSubtext) topUserSubtext.textContent = `@${username}`;
    if (settingsProfileName) settingsProfileName.textContent = displayName;
    if (settingsProfileHandle) settingsProfileHandle.textContent = `@${username}`;
    if (profileDisplayName && document.activeElement !== profileDisplayName) profileDisplayName.value = displayName;

    setAvatar("topUserAvatarImage", "topUserAvatarFallback", avatarUrl, displayName);
    setAvatar("settingsAvatarImage", "settingsAvatarFallback", avatarUrl, displayName);
    applyTheme(theme);
}

function renderSummary(summary, files) {
    const scanned = Number(summary && summary.documents_scanned ? summary.documents_scanned : (files || []).length || 0);
    const highRisk = Number(summary && summary.risk_distribution && summary.risk_distribution.High ? summary.risk_distribution.High : 0);
    const protectedCount = (files || []).filter((file) => ["Encrypted", "Redacted", "Allowed"].includes(file.status_label)).length;
    const averageRisk = Number(summary && summary.average_risk_score ? summary.average_risk_score : 0);

    document.getElementById("metricScanned").textContent = scanned;
    document.getElementById("metricProtected").textContent = protectedCount;
    document.getElementById("metricHighRisk").textContent = highRisk;

    document.getElementById("reportDocsScanned").textContent = scanned;
    document.getElementById("reportHighRisk").textContent = highRisk;
    document.getElementById("reportAverageRisk").textContent = averageRisk.toFixed ? averageRisk.toFixed(1) : averageRisk;

    const entityTotals = (summary && summary.entity_totals) || {};
    const entityBody = document.getElementById("entityTotalsBody");
    const entityRows = Object.entries(entityTotals)
        .filter(([, count]) => Number(count) > 0)
        .map(([type, count]) => `
            <tr>
                <td>${escapeHtml(formatFindingType(type))}</td>
                <td>${escapeHtml(String(count))}</td>
            </tr>
        `)
        .join("");
    entityBody.innerHTML = entityRows || `<tr><td colspan="2">No recent detections.</td></tr>`;
}

function renderDashboardTable(files) {
    const body = document.getElementById("dashboardTableBody");
    if (!files.length) {
        body.innerHTML = `<tr><td colspan="3">No recent activity yet.</td></tr>`;
        return;
    }
    body.innerHTML = files.map((file) => `
        <tr>
            <td class="pg-cell-strong">${escapeHtml(file.filename)}</td>
            <td><span class="pg-badge ${badgeClass(file.risk_level)}">${escapeHtml(file.risk_level || "Safe")}</span></td>
            <td><span class="pg-badge ${badgeClass(file.status_label)}">${escapeHtml(displayStatusLabel(file.status_label || "Stored"))}</span></td>
        </tr>
    `).join("");
}

function renderVaultTable(files) {
    const body = document.getElementById("vaultTableBody");
    if (!files.length) {
        body.innerHTML = `<tr><td colspan="4">No protected vault items yet.</td></tr>`;
        return;
    }
    body.innerHTML = files.map((file) => {
        const actions = [];
        if (file.download_url) actions.push(`<button class="pg-button-ghost" type="button" data-download="${file.download_url}">Download</button>`);
        if (file.report_url) actions.push(`<button class="pg-button-secondary" type="button" data-download="${file.report_url}">Report</button>`);
        if (file.open_url) actions.push(`<button class="pg-button" type="button" data-open="${file.open_url}">Open</button>`);
        return `
            <tr>
                <td class="pg-cell-strong">${escapeHtml(file.document_id)}</td>
                <td><span class="pg-badge ${badgeClass(file.status_label)}">${escapeHtml(displayStatusLabel(file.status_label || "Stored"))}</span></td>
                <td>${escapeHtml(formatTimestamp(file.created_at))}</td>
                <td><div class="pg-table-actions">${actions.join("") || "-"}</div></td>
            </tr>
        `;
    }).join("");
}

function renderActivityTable(activity) {
    const body = document.getElementById("reportsActivityBody");
    if (!activity.length) {
        body.innerHTML = `<tr><td colspan="3">No audit events recorded yet.</td></tr>`;
        return;
    }
    body.innerHTML = activity.map((item) => `
        <tr>
            <td class="pg-cell-strong">${escapeHtml(item.event_type)}</td>
            <td>${escapeHtml(item.document_id || "System")}</td>
            <td>${escapeHtml(formatTimestamp(item.created_at))}</td>
        </tr>
    `).join("");
}

function riskBreakdown(findings) {
    const counts = { high: 0, medium: 0, low: 0 };
    Object.entries(findings || {}).forEach(([type, entries]) => {
        const amount = (entries || []).length;
        if (riskWeights.high.includes(type)) counts.high += amount;
        else if (riskWeights.medium.includes(type)) counts.medium += amount;
        else counts.low += amount;
    });
    return counts;
}

function renderRiskBreakdown(findings) {
    const breakdown = riskBreakdown(findings);
    document.getElementById("scanRiskBreakdown").innerHTML = `
        <div class="pg-metric-card"><span>High Risk</span><strong>${breakdown.high}</strong><p>IDs, secrets, and financial data.</p></div>
        <div class="pg-metric-card"><span>Medium Risk</span><strong>${breakdown.medium}</strong><p>Contacts and medium-risk personal data.</p></div>
        <div class="pg-metric-card"><span>Low Risk</span><strong>${breakdown.low}</strong><p>General personal context.</p></div>
    `;
}

function renderDetections(findings) {
    const rows = [];
    Object.entries(findings || {}).forEach(([type, entries]) => {
        (entries || []).forEach((item) => rows.push({ type, value: item.value || "" }));
    });
    const container = document.getElementById("scanDetections");
    if (!rows.length) {
        container.innerHTML = `<div class="pg-empty">No sensitive data detected in this document.</div>`;
        return;
    }
    container.innerHTML = rows.slice(0, 14).map((item) => {
        const risk = detectionRiskLevel(item.type);
        return `
            <div class="pg-detection-row">
                <div>
                    <div class="pg-cell-strong">${escapeHtml(formatFindingType(item.type))}</div>
                    <div class="pg-footer-note">${escapeHtml(item.value)}</div>
                </div>
                <span class="pg-badge ${risk.css}">${risk.label}</span>
            </div>
        `;
    }).join("");
}

function renderSteps(steps) {
    const container = document.getElementById("scanSteps");
    container.innerHTML = (steps || []).length
        ? (steps || []).map((step) => `
            <div class="pg-step-row">
                <div class="pg-cell-strong">Protection Update</div>
                <div>${escapeHtml(step)}</div>
            </div>
        `).join("")
        : `<div class="pg-empty">Waiting for a document.</div>`;
}

function renderResult(data) {
    document.getElementById("scanResultPanel").classList.remove("hidden");
    document.getElementById("scanRiskBadge").className = `pg-badge ${badgeClass(data.risk_level)}`;
    document.getElementById("scanRiskBadge").textContent = `${data.risk_level} Risk`;
    document.getElementById("scanSummary").innerHTML = `Document <strong>${escapeHtml(data.filename)}</strong> was processed as <strong>${escapeHtml(data.document_id)}</strong>. PrivGuard selected <strong>${escapeHtml(data.policy.label)}</strong>.`;
    document.getElementById("scanPolicyReason").textContent = data.policy.reason || "";
    renderRiskBreakdown(data.findings || {});
    renderDetections(data.findings || {});
    renderSteps(data.completed_steps || []);
    document.getElementById("scanPreview").textContent = data.preview || "";

    const actions = [];
    if (data.download && data.download.url) actions.push(`<button class="pg-button" type="button" data-download="${data.download.url}">Download Output</button>`);
    if (data.report && data.report.url) actions.push(`<button class="pg-button-secondary" type="button" data-download="${data.report.url}">Download Report</button>`);
    if (data.open_url) actions.push(`<button class="pg-button-ghost" type="button" data-open="${data.open_url}">Open Secure File</button>`);
    document.getElementById("scanResultActions").innerHTML = actions.join("");
}

function renderWatchFolder(state) {
    const badge = document.getElementById("watchBadge");
    const input = document.getElementById("watchFolderPath");
    const status = document.getElementById("watchFolderStatus");
    const enabled = !!(state && state.enabled);
    input.value = state && state.path ? state.path : "";
    badge.className = `pg-badge ${enabled ? "pg-badge-risk-low" : "pg-badge-risk-safe"}`;
    badge.textContent = enabled ? "Watch Active" : "Watch Off";

    if (!enabled) {
        status.textContent = "Watch Folder is off. Point PrivGuard at an inbound folder to secure new files automatically.";
        return;
    }

    const details = [
        `Watching: ${state.path || "Unknown folder"}`,
        state.running ? "Monitor active." : "Monitor paused until the vault is unlocked again.",
    ];
    if (state.last_file) details.push(`Last file: ${state.last_file}`);
    if (state.last_document_id) details.push(`Last document: ${state.last_document_id}`);
    if (state.last_error) details.push(`Issue: ${state.last_error}`);
    status.textContent = details.join(" ");
}

function renderPreviewDrawer(data) {
    const drawer = document.getElementById("previewDrawer");
    drawer.classList.remove("hidden");
    document.getElementById("previewMeta").innerHTML = `Opened <strong>${escapeHtml(data.filename)}</strong> as <strong>${escapeHtml(data.opened_as)}</strong>.`;
    document.getElementById("previewContent").textContent = data.content || "";
}

function renderWorkspace(workspace) {
    if (!workspace) return;
    renderSummary(workspace.summary || {}, workspace.recent_files || []);
    renderDashboardTable(workspace.recent_files || []);
    renderVaultTable(workspace.recent_files || []);
    renderActivityTable(workspace.activity || []);
    renderWatchFolder(workspace.watch_folder || {});
    renderUser(workspace.user || workspaceState.user);
}

async function loadWorkspace() {
    const data = await api("/api/workspace");
    if (!data) return;
    renderWorkspace(data);
}

async function processSelectedFile() {
    const file = document.getElementById("fileInput").files[0];
    if (!file) return;
    setActiveScreen("scan");
    document.getElementById("scanStatus").textContent = "PrivGuard is extracting text, detecting sensitive data, classifying risk, and securing the document now...";
    const form = new FormData();
    form.append("file", file);
    try {
        const data = await api("/automate", { method: "POST", body: form });
        if (!data) return;
        renderResult(data);
        document.getElementById("scanStatus").textContent = "Document protected successfully. Review the result below or open the secure file from the vault.";
        renderWorkspace(data.workspace || {});
    } catch (error) {
        document.getElementById("scanStatus").textContent = error.message;
    }
}

async function saveWatchFolder() {
    const path = document.getElementById("watchFolderPath").value.trim();
    if (!path) {
        document.getElementById("watchFolderStatus").textContent = "Enter a folder path first.";
        return;
    }
    try {
        const state = await api("/api/watch-folder", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path }),
        });
        if (!state) return;
        renderWatchFolder(state);
    } catch (error) {
        document.getElementById("watchFolderStatus").textContent = error.message;
    }
}

async function stopWatchFolder() {
    try {
        const state = await api("/api/watch-folder", { method: "DELETE" });
        if (!state) return;
        renderWatchFolder(state);
    } catch (error) {
        document.getElementById("watchFolderStatus").textContent = error.message;
    }
}

async function openDocument(url) {
    try {
        const data = await api(url, { method: "POST" });
        if (!data) return;
        setActiveScreen("vault");
        renderPreviewDrawer(data);
    } catch (error) {
        document.getElementById("scanStatus").textContent = error.message;
    }
}

function downloadUrl(url) {
    window.location.href = url;
}

async function persistProfile(payload, statusMessage) {
    const data = await api("/api/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    if (!data) return null;
    renderUser(data);
    document.getElementById("profileStatus").textContent = statusMessage;
    return data;
}

async function saveProfile() {
    const displayName = document.getElementById("profileDisplayName").value.trim();
    const theme = document.body.dataset.theme || "dark";
    try {
        await persistProfile({ display_name: displayName, theme }, "Profile updated successfully.");
    } catch (error) {
        document.getElementById("profileStatus").textContent = error.message;
    }
}

async function uploadAvatar() {
    const input = document.getElementById("profileAvatarInput");
    const file = input.files[0];
    if (!file) return;

    const form = new FormData();
    form.append("avatar", file);
    document.getElementById("profileStatus").textContent = "Uploading avatar...";

    try {
        const data = await api("/api/profile/avatar", { method: "POST", body: form });
        if (!data) return;
        renderUser(data);
        document.getElementById("profileStatus").textContent = "Avatar updated successfully.";
    } catch (error) {
        document.getElementById("profileStatus").textContent = error.message;
    } finally {
        input.value = "";
    }
}

async function toggleTheme() {
    const previousTheme = document.body.dataset.theme === "light" ? "light" : "dark";
    const nextTheme = previousTheme === "light" ? "dark" : "light";
    applyTheme(nextTheme);

    try {
        await persistProfile(
            {
                display_name: document.getElementById("profileDisplayName").value.trim(),
                theme: nextTheme,
            },
            nextTheme === "light" ? "Light mode enabled." : "Dark mode enabled.",
        );
    } catch (error) {
        applyTheme(previousTheme);
        document.getElementById("profileStatus").textContent = error.message;
    }
}

async function logout() {
    await fetch("/logout", { method: "POST" });
    window.location.href = "/login";
}

function attachTableActions() {
    document.body.addEventListener("click", (event) => {
        const downloadButton = event.target.closest("[data-download]");
        const openButton = event.target.closest("[data-open]");
        const navButton = event.target.closest(".pg-nav-btn");

        if (downloadButton) {
            downloadUrl(downloadButton.dataset.download);
            return;
        }
        if (openButton) {
            openDocument(openButton.dataset.open);
            return;
        }
        if (navButton) {
            setActiveScreen(navButton.dataset.screen);
        }
    });
}

window.addEventListener("DOMContentLoaded", async () => {
    applyTheme(document.body.dataset.theme || "dark");

    document.getElementById("protectDocumentBtn").addEventListener("click", () => {
        setActiveScreen("scan");
        openPicker();
    });
    document.getElementById("scanProtectBtn").addEventListener("click", openPicker);
    document.getElementById("logoutBtn").addEventListener("click", logout);
    document.getElementById("saveWatchFolderBtn").addEventListener("click", saveWatchFolder);
    document.getElementById("stopWatchFolderBtn").addEventListener("click", stopWatchFolder);
    document.getElementById("saveProfileBtn").addEventListener("click", saveProfile);
    document.getElementById("profileAvatarInput").addEventListener("change", uploadAvatar);
    document.getElementById("themeToggleBtn").addEventListener("click", toggleTheme);
    document.getElementById("settingsThemeToggle").addEventListener("click", toggleTheme);
    document.getElementById("fileInput").addEventListener("change", async () => {
        const file = document.getElementById("fileInput").files[0];
        updateSelectedFile(file);
        await processSelectedFile();
    });

    const dropzone = document.getElementById("dropzone");
    dropzone.addEventListener("click", openPicker);
    ["dragenter", "dragover"].forEach((eventName) => {
        dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.add("dragover");
        });
    });
    ["dragleave", "drop"].forEach((eventName) => {
        dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.remove("dragover");
        });
    });
    dropzone.addEventListener("drop", async (event) => {
        const files = event.dataTransfer.files;
        if (!files || !files.length) return;
        const dt = new DataTransfer();
        dt.items.add(files[0]);
        document.getElementById("fileInput").files = dt.files;
        updateSelectedFile(files[0]);
        await processSelectedFile();
    });

    attachTableActions();
    setActiveScreen("dashboard");
    await loadWorkspace();
    window.setInterval(loadWorkspace, 5000);
});
