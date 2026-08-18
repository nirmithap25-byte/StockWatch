// Frontend/js/panels/audit_panel.js

async function renderAuditPanel(container) {
    container.innerHTML = `
        <div class="panel-header-section">
            <h2>Security Audit Logs</h2>
        </div>

        <div class="table-card">
            <div class="table-header">
                <span class="table-title">System-wide Activity Trail</span>
                <div class="table-actions">
                    <div class="search-wrapper">
                        <span class="material-symbols-outlined">search</span>
                        <input type="text" id="audit-search-input" placeholder="Search by module, operator, or description..." onkeyup="filterAuditTable()">
                    </div>
                </div>
            </div>
            <div class="table-wrapper">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Log ID</th>
                            <th>Timestamp</th>
                            <th>Module</th>
                            <th>Action</th>
                            <th>Flagged Description</th>
                            <th>Operator (Role)</th>
                            <th>IP Address</th>
                        </tr>
                    </thead>
                    <tbody id="audit-tbody">
                        <tr><td colspan="7" align="center" style="color:var(--text-secondary);">Loading security audit trail...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    `;

    loadAuditTrailLogs();
}

let auditTrailLogsList = [];

async function loadAuditTrailLogs() {
    try {
        const res = await apiFetch("/api/auth/audit-logs");
        const tbody = document.getElementById("audit-tbody");
        if (tbody && res.success) {
            auditTrailLogsList = res.data;
            renderAuditTableRows(auditTrailLogsList);
        }
    } catch (e) {
        console.error("Failed to load audit logs:", e);
        const tbody = document.getElementById("audit-tbody");
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="7" align="center" style="color:var(--color-danger);">Error: ${e.message}</td></tr>`;
        }
    }
}

function renderAuditTableRows(logs) {
    const tbody = document.getElementById("audit-tbody");
    if (!tbody) return;

    if (logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" align="center" style="color:var(--text-secondary);">No activities recorded in audit logs.</td></tr>`;
        return;
    }

    tbody.innerHTML = "";
    logs.forEach(log => {
        const tr = document.createElement("tr");

        let actionColor = "badge pending"; // Yellow default
        if (log.action.includes("DELETE") || log.action.includes("CANCEL") || log.action.includes("VOID") || log.action.includes("REJECT")) {
            actionColor = "badge cancelled"; // Red
        } else if (log.action.includes("INSERT") || log.action.includes("CREATE") || log.action.includes("REGISTER") || log.action.includes("IN") || log.action.includes("APPROVE")) {
            actionColor = "badge received"; // Emerald
        } else if (log.action.includes("LOGIN")) {
            actionColor = "badge ordered"; // Blue
        }

        tr.innerHTML = `
            <td style="font-family:monospace; font-weight:700;">#${log.log_id}</td>
            <td style="color:var(--text-secondary); font-size:11px;">${new Date(log.log_time).toLocaleString()}</td>
            <td><strong style="color:var(--text-primary);">${log.module}</strong></td>
            <td><span class="${actionColor}">${log.action}</span></td>
            <td style="color:var(--text-secondary); font-size:12px;">${log.description} <span style="font-size:10px; color:var(--text-muted); font-family:monospace;">(Rec ID: ${log.record_id || 'N/A'}, Table: ${log.table_name})</span></td>
            <td>
                <div style="font-weight:600;">${log.performed_by || 'System Automatic'}</div>
                <div style="font-size:10px; color:var(--text-secondary);">${log.user_role || 'System Service'}</div>
            </td>
            <td style="font-family:monospace; font-size:11px; color:var(--text-secondary);">${log.ip_address}</td>
        `;
        tbody.appendChild(tr);
    });
}

function filterAuditTable() {
    const query = document.getElementById("audit-search-input").value.toLowerCase().trim();
    if (!query) {
        renderAuditTableRows(auditTrailLogsList);
        return;
    }

    const filtered = auditTrailLogsList.filter(log => 
        log.module.toLowerCase().includes(query) || 
        log.action.toLowerCase().includes(query) || 
        log.description.toLowerCase().includes(query) ||
        (log.performed_by && log.performed_by.toLowerCase().includes(query)) ||
        (log.user_role && log.user_role.toLowerCase().includes(query))
    );
    renderAuditTableRows(filtered);
}
