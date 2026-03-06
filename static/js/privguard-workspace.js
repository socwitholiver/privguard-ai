const screenTitles = {
    dashboard: "Dashboard",
    watch: "Watch Folder",
    vault: "Secure Vault",
    reports: "Risk Reports",
    settings: "Settings",
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

const icons = {
    moon: '<svg viewBox="0 0 24 24"><path d="M12.2 2a8.98 8.98 0 0 0 0 18c3.87 0 7.15-2.45 8.42-5.87A8 8 0 0 1 12.2 2z"></path></svg>',
    sun: '<svg viewBox="0 0 24 24"><path d="M6.76 4.84 5.35 3.43 3.93 4.85l1.41 1.41 1.42-1.42zM1 13h3v-2H1v2zm10-9h2V1h-2v3zm7.66 2.26 1.41-1.41-1.41-1.42-1.42 1.42 1.42 1.41zM17.24 19.16l1.42 1.41 1.41-1.41-1.41-1.42-1.42 1.42zM20 11v2h3v-2h-3zM11 20h2v3h-2v-3zM4.84 17.24l-1.41 1.42 1.41 1.41 1.41-1.41-1.41-1.42zM12 6a6 6 0 1 0 0 12 6 6 0 0 0 0-12z"></path></svg>',
};

let workspaceState = { user: null, pendingScreen: null, pendingOpenUrl: null };

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
    if (response.status === 401) {
        window.location.href = "/login";
        return null;
    }
    if (response.status === 423) {
        const data = await response.json().catch(() => ({}));
        const error = new Error(data.error || "Vault locked");
        error.status = 423;
        throw error;
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
    const drawer = document.getElementById("previewDrawer");
    if (drawer && target !== "vault") drawer.classList.add("hidden");
    const title = document.getElementById("topSectionLabel");
    if (title) title.textContent = screenTitles[target] || "Workspace";
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

function updateVaultStatus(user) {
    const unlocked = !!(user && user.vault_unlocked);
    const pill = document.getElementById("vaultStatusPill");
    const text = document.getElementById("vaultStatusText");
    const settingsStatus = document.getElementById("settingsVaultStatus");
    if (pill) {
        pill.classList.toggle("pg-vault-pill-locked", !unlocked);
        pill.classList.toggle("pg-vault-pill-unlocked", unlocked);
    }
    if (text) text.textContent = unlocked ? "Vault Unlocked" : "Vault Locked";
    if (settingsStatus) settingsStatus.textContent = unlocked ? "Unlocked" : "Locked until master PIN is entered";
}

function openVaultUnlockModal(targetScreen = "vault", openUrl = null) {
    workspaceState.pendingScreen = targetScreen;
    workspaceState.pendingOpenUrl = openUrl;
    const modal = document.getElementById("vaultUnlockModal");
    const error = document.getElementById("vaultUnlockError");
    const input = document.getElementById("vaultPinInput");
    if (error) {
        error.textContent = "";
        error.classList.add("hidden");
    }
    if (input) input.value = "";
    if (modal) {
        modal.classList.remove("hidden");
        modal.setAttribute("aria-hidden", "false");
    }
    window.setTimeout(() => input && input.focus(), 20);
}

function closeVaultUnlockModal() {
    const modal = document.getElementById("vaultUnlockModal");
    if (!modal) return;
    modal.classList.add("hidden");
    modal.setAttribute("aria-hidden", "true");
}

async function unlockVaultWithPin() {
    const input = document.getElementById("vaultPinInput");
    const error = document.getElementById("vaultUnlockError");
    const pin = input ? input.value.trim() : "";
    if (!pin) {
        if (error) {
            error.textContent = "Enter the master PIN.";
            error.classList.remove("hidden");
        }
        return;
    }

    try {
        const data = await api("/api/vault/unlock", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ pin }),
        });
        if (!data) return;
        if (data.user) renderUser(data.user);
        closeVaultUnlockModal();
        await loadWorkspace();
        if (workspaceState.pendingOpenUrl) {
            const url = workspaceState.pendingOpenUrl;
            workspaceState.pendingOpenUrl = null;
            setActiveScreen("vault");
            await openDocument(url);
            return;
        }
        setActiveScreen(workspaceState.pendingScreen || "vault");
        workspaceState.pendingScreen = null;
    } catch (err) {
        if (error) {
            error.textContent = err.message;
            error.classList.remove("hidden");
        }
    }
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
    updateVaultStatus(user);
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

function renderSystemSettings(settings, lifecycleEngine) {
    const safe = settings || {};
    const retention = safe.retention_defaults || {};
    const setValue = (id, value) => {
        const node = document.getElementById(id);
        if (node && document.activeElement !== node) node.value = value ?? "";
    };
    setValue("highRetentionDays", retention.high || 90);
    setValue("mediumRetentionDays", retention.medium || 180);
    setValue("lowRetentionDays", retention.low || 365);
    setValue("expiringSoonDays", safe.expiring_soon_days || 10);
    setValue("lifecycleScanSeconds", safe.scan_seconds || 60);
    const autoArchive = document.getElementById("autoArchiveExpiredToggle");
    const autoDelete = document.getElementById("autoDeleteArchivedToggle");
    if (autoArchive) autoArchive.checked = !!safe.auto_archive_expired;
    if (autoDelete) autoDelete.checked = !!safe.auto_delete_archived;
    const lifecycleEngineNode = document.getElementById("settingsLifecycleEngine");
    if (lifecycleEngineNode) {
        const mode = lifecycleEngine && lifecycleEngine.running ? "Running" : "Idle";
        const lastRun = lifecycleEngine && lifecycleEngine.last_run_at ? formatTimestamp(lifecycleEngine.last_run_at) : "No run yet";
        lifecycleEngineNode.textContent = `${mode} | Last run: ${lastRun}`;
    }
}

function renderVaultLifecycleSummary(summary) {
    const lifecycle = summary || {};
    document.getElementById("vaultActiveCount").textContent = Number(lifecycle.active || 0);
    document.getElementById("vaultExpiringCount").textContent = Number(lifecycle.expiring || 0) + Number(lifecycle.expired || 0);
    document.getElementById("vaultArchivedCount").textContent = Number(lifecycle.archived || 0) + Number(lifecycle.deleted || 0);
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
        body.innerHTML = `<tr><td colspan="5">No protected vault items yet.</td></tr>`;
        return;
    }
    body.innerHTML = files.map((file) => {
        const actions = [];
        if (file.download_url) actions.push(`<button class="pg-button-ghost" type="button" data-download="${file.download_url}">Download</button>`);
        if (file.report_url) actions.push(`<button class="pg-button-secondary" type="button" data-download="${file.report_url}">Report</button>`);
        if (file.open_url) actions.push(`<button class="pg-button" type="button" data-open="${file.open_url}">Open</button>`);
        if ((file.lifecycle_actions || []).includes("archive")) actions.push(`<button class="pg-button-secondary" type="button" data-lifecycle-action="archive" data-document-id="${file.document_id}">Archive</button>`);
        if ((file.lifecycle_actions || []).includes("secure_delete")) actions.push(`<button class="pg-button-danger" type="button" data-lifecycle-action="secure_delete" data-document-id="${file.document_id}">Secure Delete</button>`);
        return `
            <tr>
                <td>
                    <div class="pg-cell-strong">${escapeHtml(file.document_id)}</div>
                    <div class="pg-footer-note">${escapeHtml(file.owner || "Operations")} | ${escapeHtml(file.department || "Operations")}</div>
                </td>
                <td>
                    <div><span class="pg-badge ${badgeClass(file.status_label)}">${escapeHtml(displayStatusLabel(file.status_label || "Stored"))}</span></div>
                    <div class="pg-footer-note">${escapeHtml(file.lifecycle_status || "Active")}</div>
                </td>
                <td>
                    <div>${escapeHtml(file.retention_label || "Not set")}</div>
                    <div class="pg-footer-note">Until ${escapeHtml(formatTimestamp(file.retention_until))}</div>
                </td>
                <td>
                    <div>${escapeHtml(file.next_action || "Monitor lifecycle")}</div>
                    <div class="pg-footer-note">${escapeHtml(file.policy_name || "Retention policy")}</div>
                </td>
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

function renderPreviewDrawer(data) {
    setActiveScreen("vault");
    const drawer = document.getElementById("previewDrawer");
    drawer.classList.remove("hidden");
    document.getElementById("previewMeta").innerHTML = `Opened <strong>${escapeHtml(data.filename)}</strong> as <strong>${escapeHtml(data.opened_as)}</strong>.`;
    document.getElementById("previewContent").textContent = data.content || "";
}

function renderWatchFolder(state) {
    const input = document.getElementById("watchFolderPath");
    const display = document.getElementById("watchFolderPathDisplay");
    const status = document.getElementById("watchFolderStatus");
    const watchBadge = document.getElementById("watchBadge");
    const dashboardWatchBadge = document.getElementById("dashboardWatchBadge");
    const enabled = !!(state && state.enabled);
    const badgeClassName = enabled ? "pg-badge-risk-low" : "pg-badge-risk-safe";
    const badgeText = enabled ? "Watch Active" : "Watch Off";

    if (input) input.value = state && state.path ? state.path : "";
    if (display) display.textContent = state && state.path ? state.path : "No folder selected";
    if (watchBadge) {
        watchBadge.className = `pg-badge ${badgeClassName}`;
        watchBadge.textContent = badgeText;
    }
    if (dashboardWatchBadge) {
        dashboardWatchBadge.className = `pg-badge ${badgeClassName}`;
        dashboardWatchBadge.textContent = badgeText;
    }

    const currentFolder = state && state.path ? state.path : "Not configured";
    const engineState = !enabled
        ? "Idle"
        : state.running
            ? (state.mode === "event" ? "Watching instantly (event-driven)" : "Watching for new files")
            : "Paused until the vault is unlocked again";
    const statusParts = [];
    if (!enabled) {
        statusParts.push("Watch Folder is off. Point PrivGuard at an inbound folder to secure new files automatically.");
    } else {
        statusParts.push(`Watching: ${currentFolder}`);
        statusParts.push(state.running ? "Monitor active." : "Monitor paused until the vault is unlocked again.");
        if (state.last_file) statusParts.push(`Last file: ${state.last_file}`);
        if (state.last_document_id) statusParts.push(`Last document: ${state.last_document_id}`);
        if (state.last_error) statusParts.push(`Issue: ${state.last_error}`);
    }

    if (status) status.textContent = statusParts.join(" ");
    document.getElementById("dashboardWatchPath").textContent = currentFolder;
    document.getElementById("dashboardWatchLastScan").textContent = state && state.last_scan_at ? formatTimestamp(state.last_scan_at) : "No activity yet";
    document.getElementById("watchEngineState").textContent = engineState;
    document.getElementById("watchLastProcessedFile").textContent = state && state.last_file ? state.last_file : "No file processed yet";
    document.getElementById("watchLastDocumentId").textContent = state && state.last_document_id ? state.last_document_id : "No document ID yet";
    document.getElementById("watchLastProcessedAt").textContent = state && state.last_processed_at ? formatTimestamp(state.last_processed_at) : "No processing timestamp yet";
}

function renderLatestDocument(files) {
    const latest = (files || [])[0];
    document.getElementById("dashboardLatestFile").textContent = latest ? latest.filename : "Waiting for watch-folder input";
    document.getElementById("dashboardLatestOutcome").textContent = latest ? `${latest.risk_level || "Safe"} risk | ${displayStatusLabel(latest.status_label || "Stored")}` : "No protected output yet";
    document.getElementById("watchLatestName").textContent = latest ? latest.filename : "Waiting for watched files";
    document.getElementById("watchLatestRisk").textContent = latest ? `${latest.risk_level || "Safe"} risk` : "-";
    document.getElementById("watchLatestStatus").textContent = latest ? displayStatusLabel(latest.status_label || "Stored") : "-";
    document.getElementById("watchLatestTime").textContent = latest ? formatTimestamp(latest.created_at) : "-";
}

function renderWorkspace(workspace) {
    if (!workspace) return;
    renderSummary(workspace.summary || {}, workspace.recent_files || []);
    renderDashboardTable(workspace.recent_files || []);
    renderVaultLifecycleSummary(workspace.lifecycle_summary || {});
    renderVaultTable(workspace.recent_files || []);
    renderActivityTable(workspace.activity || []);
    renderWatchFolder(workspace.watch_folder || {});
    renderLatestDocument(workspace.recent_files || []);
    renderUser(workspace.user || workspaceState.user);
    renderSystemSettings(workspace.settings || {}, workspace.lifecycle_engine || {});
}

async function loadWorkspace() {
    const data = await api("/api/workspace");
    if (!data) return;
    renderWorkspace(data);
}

async function pickWatchFolder() {
    try {
        const data = await api("/api/watch-folder/pick", { method: "POST" });
        if (!data) return;
        document.getElementById("watchFolderPath").value = data.path || "";
        document.getElementById("watchFolderStatus").textContent = data.path
            ? `Selected folder: ${data.path}. Starting watch mode...`
            : "No folder selected.";
        if (data.path) {
            await saveWatchFolder();
        }
    } catch (error) {
        document.getElementById("watchFolderStatus").textContent = error.message;
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
        setActiveScreen("watch");
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

async function runLifecycleAction(documentId, action) {
    const statusNode = document.getElementById("watchFolderStatus");
    const url = action === "archive"
        ? `/api/documents/${documentId}/lifecycle/archive`
        : `/api/documents/${documentId}/lifecycle/delete`;
    try {
        const data = await api(url, { method: "POST" });
        if (!data) return;
        if (statusNode) {
            statusNode.textContent = action === "archive"
                ? `Document ${documentId} archived successfully.`
                : `Document ${documentId} securely deleted.`;
        }
        await loadWorkspace();
        setActiveScreen("vault");
    } catch (error) {
        if (statusNode) statusNode.textContent = error.message;
    }
}

async function openDocument(url) {
    try {
        const data = await api(url, { method: "POST" });
        if (!data) return;
        renderPreviewDrawer(data);
    } catch (error) {
        document.getElementById("watchFolderStatus").textContent = error.message;
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

async function saveLifecycleSettings() {
    const payload = {
        high_retention_days: Number(document.getElementById("highRetentionDays").value || 90),
        medium_retention_days: Number(document.getElementById("mediumRetentionDays").value || 180),
        low_retention_days: Number(document.getElementById("lowRetentionDays").value || 365),
        expiring_soon_days: Number(document.getElementById("expiringSoonDays").value || 10),
        scan_seconds: Number(document.getElementById("lifecycleScanSeconds").value || 60),
        auto_archive_expired: document.getElementById("autoArchiveExpiredToggle").checked,
        auto_delete_archived: document.getElementById("autoDeleteArchivedToggle").checked,
    };
    try {
        await api("/api/system-settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        document.getElementById("lifecycleSettingsStatus").textContent = "Lifecycle policies updated.";
        await loadWorkspace();
    } catch (error) {
        document.getElementById("lifecycleSettingsStatus").textContent = error.message;
    }
}

async function changeVaultPin() {
    const currentPin = document.getElementById("currentVaultPin").value.trim();
    const newPin = document.getElementById("newVaultPin").value.trim();
    try {
        const data = await api("/api/vault/pin", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ current_pin: currentPin, new_pin: newPin }),
        });
        if (!data) return;
        document.getElementById("vaultPinStatus").textContent = data.message || "Vault PIN updated.";
        document.getElementById("currentVaultPin").value = "";
        document.getElementById("newVaultPin").value = "";
    } catch (error) {
        document.getElementById("vaultPinStatus").textContent = error.message;
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
        const lifecycleButton = event.target.closest("[data-lifecycle-action]");
        const navButton = event.target.closest(".pg-nav-btn");

        if (downloadButton) {
            if (!(workspaceState.user && workspaceState.user.vault_unlocked)) {
                openVaultUnlockModal("vault");
                return;
            }
            downloadUrl(downloadButton.dataset.download);
            return;
        }
        if (lifecycleButton) {
            if (!(workspaceState.user && workspaceState.user.vault_unlocked)) {
                openVaultUnlockModal("vault");
                return;
            }
            runLifecycleAction(lifecycleButton.dataset.documentId, lifecycleButton.dataset.lifecycleAction);
            return;
        }
        if (openButton) {
            if (!(workspaceState.user && workspaceState.user.vault_unlocked)) {
                openVaultUnlockModal("vault", openButton.dataset.open);
                return;
            }
            openDocument(openButton.dataset.open);
            return;
        }
        if (navButton) {
            if (navButton.dataset.screen === "vault" && !(workspaceState.user && workspaceState.user.vault_unlocked)) {
                openVaultUnlockModal("vault");
                return;
            }
            setActiveScreen(navButton.dataset.screen);
        }
    });
}

window.addEventListener("DOMContentLoaded", async () => {
    applyTheme(document.body.dataset.theme || "dark");

    document.getElementById("openWatchFolderBtn").addEventListener("click", () => setActiveScreen("watch"));
    document.getElementById("logoutBtn").addEventListener("click", logout);
    document.getElementById("pickWatchFolderBtn").addEventListener("click", pickWatchFolder);
    document.getElementById("stopWatchFolderBtn").addEventListener("click", stopWatchFolder);
    document.getElementById("saveProfileBtn").addEventListener("click", saveProfile);
    document.getElementById("saveLifecycleSettingsBtn").addEventListener("click", saveLifecycleSettings);
    document.getElementById("changeVaultPinBtn").addEventListener("click", changeVaultPin);
    document.getElementById("profileAvatarInput").addEventListener("change", uploadAvatar);
    document.getElementById("themeToggleBtn").addEventListener("click", toggleTheme);
    document.getElementById("settingsThemeToggle").addEventListener("click", toggleTheme);
    document.getElementById("vaultUnlockBtn").addEventListener("click", unlockVaultWithPin);
    document.getElementById("vaultUnlockCancelBtn").addEventListener("click", closeVaultUnlockModal);
    document.querySelectorAll("[data-close-vault-modal]").forEach((node) => node.addEventListener("click", closeVaultUnlockModal));
    document.getElementById("vaultPinInput").addEventListener("keydown", (event) => { if (event.key === "Enter") unlockVaultWithPin(); });

    attachTableActions();
    setActiveScreen("dashboard");
    await loadWorkspace();
    window.setInterval(loadWorkspace, 5000);
});
