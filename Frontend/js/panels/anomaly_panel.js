// Frontend/js/panels/anomaly_panel.js

async function renderAnomalyPanel(container) {
    container.innerHTML = `
        <div class="panel-header-section">
            <h2>Isolation Forest Anomaly Detection</h2>
            <button class="btn-primary" onclick="runIsolationForestScan()" id="btn-run-anomaly-scan">
                <span class="material-symbols-outlined">security</span>
                Run Machine Learning Scan
            </button>
        </div>

        <!-- ── EXPLANATORY ALGORITHM INFO ───────────────────────── -->
        <div class="chart-card" style="margin-bottom: 30px; display: flex; gap: 20px; align-items: center; border-left: 4px solid var(--accent-orange);">
            <span class="material-symbols-outlined" style="font-size: 48px; color: var(--accent-orange);">insights</span>
            <div>
                <h4 style="font-family:var(--font-heading); font-size:15px; margin-bottom:5px; color:#f9fafb;">How it works: Isolation Forest Algorithm</h4>
                <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.5;">
                    The system runs a scikit-learn **Isolation Forest** model analyzing features of all historical stock movements: transacted quantity, previous vs. new stock levels, movement type (IN/OUT/TRANSFER/ADJUSTMENT), absolute quantity change, and percentage drop relative to available stock. The model isolates anomalies (outliers) that deviate from ordinary transaction patterns.
                </p>
            </div>
        </div>

        <!-- ── ANOMALY KPI SUMMARY ──────────────────────────────── -->
        <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));">
            <div class="stat-card">
                <div class="stat-info">
                    <h3>Total Outliers Found</h3>
                    <div class="stat-value" id="anomaly-stat-total">-</div>
                </div>
                <div class="stat-icon-wrapper orange">
                    <span class="material-symbols-outlined">analytics</span>
                </div>
            </div>
            
            <div class="stat-card">
                <div class="stat-info">
                    <h3>High Severity Alert</h3>
                    <div class="stat-value" id="anomaly-stat-high" style="color:var(--color-danger);">-</div>
                </div>
                <div class="stat-icon-wrapper red">
                    <span class="material-symbols-outlined">gpp_maybe</span>
                </div>
            </div>

            <div class="stat-card">
                <div class="stat-info">
                    <h3>Medium Severity Alert</h3>
                    <div class="stat-value" id="anomaly-stat-medium" style="color:var(--color-warning);">-</div>
                </div>
                <div class="stat-icon-wrapper yellow">
                    <span class="material-symbols-outlined">gpp_maybe</span>
                </div>
            </div>

            <div class="stat-card">
                <div class="stat-info">
                    <h3>Unread ML Alerts</h3>
                    <div class="stat-value" id="anomaly-stat-unread">-</div>
                </div>
                <div class="stat-icon-wrapper blue">
                    <span class="material-symbols-outlined">notification_important</span>
                </div>
            </div>
        </div>

        <!-- ── OUTLIERS LIST TABLE ──────────────────────────────── -->
        <div class="table-card">
            <div class="table-header">
                <span class="table-title">Detected Suspicious Activities</span>
            </div>
            <div class="table-wrapper">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Scan Time</th>
                            <th>Target Item</th>
                            <th>Severity</th>
                            <th>Flagged Description</th>
                            <th>Status</th>
                            <th align="center">Action</th>
                        </tr>
                    </thead>
                    <tbody id="anomaly-tbody">
                        <tr><td colspan="6" align="center" style="color:var(--text-secondary);">Loading anomaly alerts...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    `;

    loadAnomalySummary();
    loadAnomalyAlertsTable();
}

async function loadAnomalySummary() {
    try {
        const res = await apiFetch("/api/anomaly/summary");
        if (res.success && res.summary) {
            document.getElementById("anomaly-stat-total").innerText = res.summary.total_anomalies;
            document.getElementById("anomaly-stat-high").innerText = res.summary.high;
            document.getElementById("anomaly-stat-medium").innerText = res.summary.medium;
            document.getElementById("anomaly-stat-unread").innerText = res.summary.unread;
        }
    } catch (e) {
        console.error(e);
    }
}

async function loadAnomalyAlertsTable() {
    try {
        const res = await apiFetch("/api/anomaly/alerts");
        const tbody = document.getElementById("anomaly-tbody");
        if (tbody && res.success) {
            if (res.anomaly_alerts.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" align="center" style="color:var(--color-success); font-weight:600; padding:30px;">No anomalies detected. All transactions look secure and normal.</td></tr>`;
                return;
            }

            tbody.innerHTML = "";
            res.anomaly_alerts.forEach(alert => {
                const tr = document.createElement("tr");

                let severityClass = "badge pending"; // Yellow
                if (alert.severity === 'High') severityClass = "badge critical"; // Red

                const isUnread = alert.status === 'Unread';

                tr.innerHTML = `
                    <td style="color:var(--text-secondary); font-size:11px; width:15%;">${new Date(alert.created_at).toLocaleString()}</td>
                    <td style="width:20%;">
                        <div style="font-weight:600; color:var(--text-primary);">${alert.item_name}</div>
                        <div style="font-size:10px; font-family:monospace; color:var(--text-secondary);">${alert.item_code}</div>
                    </td>
                    <td style="width:10%;"><span class="${severityClass}">${alert.severity}</span></td>
                    <td style="width:40%; ${isUnread ? 'font-weight:600; color:var(--text-primary);' : 'color:var(--text-secondary);'}">${alert.message}</td>
                    <td style="width:10%;">
                        <span class="badge" style="background:${isUnread ? 'rgba(234, 88, 12, 0.15)' : 'rgba(255,255,255,0.05)'}; color:${isUnread ? 'var(--accent-orange)' : 'var(--text-secondary)'};">
                            ${alert.status}
                        </span>
                    </td>
                    <td style="width:5%;" align="center">
                        ${isUnread ? `
                            <button class="btn-icon view" title="Mark as Read" onclick="markAnomalyAlertReadAction(${alert.alert_id})">
                                <span class="material-symbols-outlined">drafts</span>
                            </button>
                        ` : '<span style="color:var(--text-muted); font-size:12px;">Opened</span>'}
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }
    } catch (e) {
        console.error(e);
        const tbody = document.getElementById("anomaly-tbody");
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="6" align="center" style="color:var(--color-danger);">Error: ${e.message}</td></tr>`;
        }
    }
}

// ── TRIGGER ISOLATION FOREST SCAN ─────────────────────────────
async function runIsolationForestScan() {
    const scanBtn = document.getElementById("btn-run-anomaly-scan");
    if (scanBtn) {
        scanBtn.disabled = true;
        scanBtn.innerHTML = `<span class="material-symbols-outlined" style="animation: spin 1s linear infinite;">rotate_right</span> Scanning records...`;
    }

    Swal.fire({
        title: 'Running Machine Learning Scan...',
        html: `
            <div style="margin: 20px 0;">
                <div class="loader-spinner"></div>
                <p style="font-size:13px; color:#555; margin-top:15px; font-weight:600;">Fitting scikit-learn Isolation Forest model...<br>Evaluating stock movement clusters and isolating outliers...</p>
            </div>
        `,
        showConfirmButton: false,
        allowOutsideClick: false
    });

    try {
        const res = await apiFetch("/api/anomaly/detect", {
            method: 'POST'
        });

        Swal.close();

        let successText = `Analyzed ${res.total_movements_analyzed} transaction movements. Found ${res.anomalies_found} anomalous patterns.`;
        if (res.new_alerts_inserted > 0) {
            successText += `\n\n${res.new_alerts_inserted} new unread warning alerts have been logged and highlighted in orange.`;
        } else {
            successText += `\n\nAll detected anomalies were already registered.`;
        }

        Swal.fire({
            icon: res.anomalies_found > 0 ? 'warning' : 'success',
            title: 'Scan Completed',
            text: successText,
            confirmButtonColor: '#3b82f6'
        }).then(() => {
            navigate("anomaly");
            updateAlertBadge();
        });

    } catch (e) {
        Swal.close();
        Swal.fire({
            icon: 'error',
            title: 'Scan Failed',
            text: e.message || 'Not enough stock movements records to run Isolation Forest (minimum 5 required).',
            confirmButtonColor: '#ef4444'
        });
    } finally {
        if (scanBtn) {
            scanBtn.disabled = false;
            scanBtn.innerHTML = `<span class="material-symbols-outlined">security</span> Run Machine Learning Scan`;
        }
    }
}

// ── MARK SINGLE ANOMALY READ ─────────────────────────────────
async function markAnomalyAlertReadAction(alertId) {
    try {
        await apiFetch(`/api/alerts/${alertId}/read`, {
            method: 'PUT'
        });
        loadAnomalySummary();
        loadAnomalyAlertsTable();
        updateAlertBadge();
    } catch (e) {
        console.error(e);
        Swal.fire("Error", e.message, "error");
    }
}
