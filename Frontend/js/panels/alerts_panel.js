// Frontend/js/panels/alerts_panel.js

async function renderAlertsPanel(container) {
    container.innerHTML = `
        <div class="panel-header-section">
            <h2>Notifications & System Alerts</h2>
            <button class="btn-secondary" onclick="markAllAlertsAsReadAction()">
                <span class="material-symbols-outlined">mark_email_read</span>
                Mark All as Read
            </button>
        </div>

        <div class="table-card">
            <div class="table-header">
                <span class="table-title">System Alerts Inbox</span>
                <div class="table-actions" style="gap:15px; flex-wrap:wrap;">
                    <!-- Filter alerts by type -->
                    <div class="form-group" style="margin:0; flex-direction:row; align-items:center; gap:8px;">
                        <label style="white-space:nowrap; margin:0;">Alert Type:</label>
                        <select id="alert-filter-type" onchange="loadAlertsList()" style="padding:6px; font-size:12px;">
                            <option value="">All Types</option>
                            <option value="Low Stock">Low Stock</option>
                            <option value="Reorder Required">Reorder Required</option>
                            <option value="Anomaly">Anomaly Alerts</option>
                            <option value="System">System Logs</option>
                        </select>
                    </div>

                    <!-- Filter by severity -->
                    <div class="form-group" style="margin:0; flex-direction:row; align-items:center; gap:8px;">
                        <label style="white-space:nowrap; margin:0;">Severity:</label>
                        <select id="alert-filter-severity" onchange="loadAlertsList()" style="padding:6px; font-size:12px;">
                            <option value="">All Severities</option>
                            <option value="High">High</option>
                            <option value="Medium">Medium</option>
                            <option value="Low">Low</option>
                        </select>
                    </div>
                    
                    <div class="form-group" style="margin:0; flex-direction:row; align-items:center; gap:8px;">
                        <label style="white-space:nowrap; margin:0;">Status:</label>
                        <select id="alert-filter-unread" onchange="loadAlertsList()" style="padding:6px; font-size:12px;">
                            <option value="true">Unread Only</option>
                            <option value="false">All Alerts</option>
                        </select>
                    </div>
                </div>
            </div>

            <div class="table-wrapper">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Received Time</th>
                            <th>Category</th>
                            <th>Severity</th>
                            <th>Alert Details</th>
                            <th>Status</th>
                            <th align="center">Action</th>
                        </tr>
                    </thead>
                    <tbody id="alerts-tbody">
                        <tr><td colspan="6" align="center" style="color:var(--text-secondary);">Loading alerts inbox...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    `;

    loadAlertsList();
}

async function loadAlertsList() {
    const unread = document.getElementById("alert-filter-unread").value;
    const type = document.getElementById("alert-filter-type").value;
    const severity = document.getElementById("alert-filter-severity").value;

    const tbody = document.getElementById("alerts-tbody");
    if (tbody) {
        tbody.innerHTML = `<tr><td colspan="6" align="center" style="color:var(--text-secondary);">Updating list...</td></tr>`;
    }

    try {
        let queryParams = [];
        queryParams.push(`unread=${unread}`);
        if (type) queryParams.push(`type=${encodeURIComponent(type)}`);
        if (severity) queryParams.push(`severity=${severity}`);

        const url = `/api/alerts/?${queryParams.join("&")}`;
        const res = await apiFetch(url);

        if (tbody && res.success) {
            if (res.data.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" align="center" style="color:var(--text-secondary);">No alerts matched the selected filters.</td></tr>`;
                return;
            }

            tbody.innerHTML = "";
            res.data.forEach(alert => {
                const tr = document.createElement("tr");

                let severityClass = "badge pending"; // Yellow
                if (alert.severity === 'High') severityClass = "badge critical"; // Red
                if (alert.severity === 'Low') severityClass = "badge approved"; // Blue/Indigo

                const isUnread = alert.status === 'Unread';

                tr.innerHTML = `
                    <td style="color:var(--text-secondary); font-size:11px; width:15%;">${new Date(alert.created_at).toLocaleString()}</td>
                    <td style="width:15%;"><strong>${alert.alert_type}</strong></td>
                    <td style="width:10%;"><span class="${severityClass}">${alert.severity}</span></td>
                    <td style="width:45%; ${isUnread ? 'font-weight:600; color:var(--text-primary);' : 'color:var(--text-secondary);'}">
                        ${alert.message}
                        ${alert.item_code ? `<br><span style="font-size:10px; font-family:monospace; color:var(--accent-blue);">Item: ${alert.item_code} | Warehouse Stock: ${alert.quantity}</span>` : ''}
                    </td>
                    <td style="width:10%;">
                        <span class="badge" style="background:${isUnread ? 'rgba(239, 68, 68, 0.1)' : 'rgba(255,255,255,0.05)'}; color:${isUnread ? 'var(--color-danger)' : 'var(--text-secondary)'};">
                            ${alert.status}
                        </span>
                    </td>
                    <td style="width:5%;" align="center">
                        ${isUnread ? `
                            <button class="btn-icon view" title="Mark as Read" onclick="markAlertAsReadAction(${alert.alert_id})">
                                <span class="material-symbols-outlined">drafts</span>
                            </button>
                        ` : '<span style="color:var(--text-muted); font-size:12px;">Opened</span>'}
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }
    } catch (e) {
        console.error("Failed to load alerts:", e);
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="6" align="center" style="color:var(--color-danger);">Error: ${e.message}</td></tr>`;
        }
    }
}

// ── ACTION: MARK SINGLE ALERT READ ───────────────────────────
async function markAlertAsReadAction(alertId) {
    try {
        await apiFetch(`/api/alerts/${alertId}/read`, {
            method: 'PUT'
        });
        loadAlertsList();
        updateAlertBadge();
    } catch (e) {
        console.error(e);
        Swal.fire("Error", e.message, "error");
    }
}

// ── ACTION: MARK ALL READ ────────────────────────────────────
async function markAllAlertsAsReadAction() {
    Swal.fire({
        title: 'Mark all as read?',
        text: "This will clear unread badges for all system notifications.",
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#3b82f6',
        confirmButtonText: 'Yes, Clear All'
    }).then(async (result) => {
        if (result.isConfirmed) {
            try {
                const res = await apiFetch("/api/alerts/read-all", {
                    method: 'PUT'
                });
                Swal.fire("Cleared", res.message, "success").then(() => {
                    loadAlertsList();
                    updateAlertBadge();
                });
            } catch (e) {
                Swal.fire("Error", e.message, "error");
            }
        }
    });
}
