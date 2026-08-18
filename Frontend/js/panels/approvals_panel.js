// Frontend/js/panels/approvals_panel.js

async function renderApprovalsPanel(container) {
    const isManager = currentUser.role === 'Admin' || currentUser.role === 'Inventory Manager';

    container.innerHTML = `
        <div class="panel-header-section">
            <h2>Stock Requests & Approvals</h2>
            <button class="btn-primary" onclick="openRaiseRequestModal()">
                <span class="material-symbols-outlined">add_task</span>
                Raise Stock Request
            </button>
        </div>

        <div class="table-card">
            <div class="table-header">
                <span class="table-title">Stock Issues & Requests Queue</span>
            </div>
            <div class="table-wrapper">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Req ID</th>
                            <th>Item Requested</th>
                            <th>Available Stock</th>
                            <th>Qty Requested</th>
                            <th>Purpose / Department</th>
                            <th>Status</th>
                            <th>Requested By</th>
                            <th>Approved By</th>
                            <th align="center">Actions</th>
                        </tr>
                    </thead>
                    <tbody id="approvals-tbody">
                        <tr><td colspan="9" align="center" style="color:var(--text-secondary);">Loading requests queue...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    `;

    loadApprovalsQueue();
}

let approvalsQueueList = [];

async function loadApprovalsQueue() {
    try {
        const res = await apiFetch("/api/approvals/");
        const tbody = document.getElementById("approvals-tbody");
        if (tbody && res.success) {
            approvalsQueueList = res.approvals;
            renderApprovalsTableRows(approvalsQueueList);
        }
    } catch (e) {
        console.error("Failed to load approvals queue:", e);
        const tbody = document.getElementById("approvals-tbody");
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="9" align="center" style="color:var(--color-danger);">Error: ${e.message}</td></tr>`;
        }
    }
}

function renderApprovalsTableRows(reqs) {
    const tbody = document.getElementById("approvals-tbody");
    if (!tbody) return;

    if (reqs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" align="center" style="color:var(--text-secondary);">No stock requests found.</td></tr>`;
        return;
    }

    const isManager = currentUser.role === 'Admin' || currentUser.role === 'Inventory Manager';

    tbody.innerHTML = "";
    reqs.forEach(req => {
        const tr = document.createElement("tr");

        let statusClass = "badge pending";
        if (req.status === 'Approved') statusClass = "badge received";
        if (req.status === 'Rejected') statusClass = "badge cancelled";

        tr.innerHTML = `
            <td style="font-family:monospace; font-weight:700;">REQ-${req.approval_id}</td>
            <td>
                <div style="font-weight:600; color:var(--text-primary);">${req.item_name}</div>
                <div style="font-size:10px; font-family:monospace; color:var(--text-secondary);">${req.item_code}</div>
            </td>
            <td style="font-weight:500;">${req.available_stock}</td>
            <td style="font-weight:700; color:var(--accent-blue);">${req.requested_quantity}</td>
            <td>
                <div><strong>${req.purpose}</strong></div>
                <div style="font-size:11px; color:var(--text-secondary);">Date: ${new Date(req.request_date).toLocaleDateString()}</div>
            </td>
            <td><span class="${statusClass}">${req.status}</span></td>
            <td>${req.requested_by}</td>
            <td>
                ${req.approved_by || '<span style="color:var(--text-muted);">Awaiting</span>'}
                ${req.comments ? `<div style="font-size:10px; color:var(--text-secondary); font-style:italic;">"${req.comments}"</div>` : ''}
            </td>
            <td>
                <div class="action-btns" style="justify-content:center;">
                    ${(req.status === 'Pending' && isManager) ? `
                        <button class="btn-icon view" title="Approve Request" onclick="approveRequestAction(${req.approval_id})">
                            <span class="material-symbols-outlined">check_circle</span>
                        </button>
                        <button class="btn-icon delete" title="Reject Request" onclick="rejectRequestAction(${req.approval_id})">
                            <span class="material-symbols-outlined">cancel</span>
                        </button>
                    ` : `
                        <span style="color:var(--text-muted); font-size:12px;">Closed</span>
                    `}
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// ── RAISE REQUEST MODAL ──────────────────────────────────────
async function openRaiseRequestModal() {
    let itemsOptions = '<option value="">-- Choose Item --</option>';
    try {
        const res = await apiFetch("/api/inventory/items");
        if (res.success) {
            res.data.forEach(item => {
                itemsOptions += `<option value="${item.item_id}" data-stock="${item.quantity}">[${item.item_code}] ${item.item_name} (Stock: ${item.quantity} ${item.unit})</option>`;
            });
        }
    } catch (e) {
        console.error(e);
    }

    const bodyHtml = `
        <form id="request-form">
            <div class="form-group">
                <label>Select Item *</label>
                <select id="req-item-id" onchange="updateRequestStockPreview()" required>
                    ${itemsOptions}
                </select>
            </div>
            
            <div id="req-stock-preview" style="font-size:12px; margin-bottom:15px; color:var(--accent-blue); font-weight:600; display:none;"></div>

            <div class="form-group">
                <label>Quantity Required *</label>
                <input type="number" id="req-quantity" min="1" value="1" required>
            </div>

            <div class="form-group">
                <label>Purpose / Justification *</label>
                <input type="text" id="req-purpose" placeholder="e.g. Project development lab / Class supplies" required>
            </div>
        </form>
    `;

    showModal("Raise Stock Issue Request", bodyHtml, "Submit Request", async () => {
        const item_id = parseInt(document.getElementById("req-item-id").value);
        const quantity = parseInt(document.getElementById("req-quantity").value);
        const purpose = document.getElementById("req-purpose").value.trim();

        if (isNaN(item_id) || isNaN(quantity) || quantity <= 0 || !purpose) {
            Swal.fire("Validation Error", "All fields are required.", "error");
            return;
        }

        const selectedOption = document.getElementById("req-item-id").options[document.getElementById("req-item-id").selectedIndex];
        const stockAvailable = parseInt(selectedOption.dataset.stock) || 0;

        if (quantity > stockAvailable) {
            Swal.fire("Validation Error", `Requested quantity (${quantity}) exceeds current warehouse stock (${stockAvailable}).`, "error");
            return;
        }

        try {
            await apiFetch("/api/approvals/request", {
                method: 'POST',
                body: {
                    item_id,
                    requested_by: currentUser.user_id,
                    quantity,
                    purpose
                }
            });

            closeModal();
            Swal.fire("Request Submitted", "Your stock request has been submitted for approval.", "success").then(() => {
                loadApprovalsQueue();
                updateAlertBadge();
            });

        } catch (e) {
            Swal.fire("Submission Failed", e.message, "error");
        }
    });
}

function updateRequestStockPreview() {
    const select = document.getElementById("req-item-id");
    const preview = document.getElementById("req-stock-preview");
    if (!select || !preview) return;

    const opt = select.options[select.selectedIndex];
    if (opt && opt.dataset.stock) {
        preview.innerText = `Current Warehouse Balance: ${opt.dataset.stock} units.`;
        preview.style.display = "block";
        document.getElementById("req-quantity").setAttribute("max", opt.dataset.stock);
    } else {
        preview.style.display = "none";
    }
}

// ── APPROVE STOCK REQUEST ────────────────────────────────────
function approveRequestAction(approvalId) {
    Swal.fire({
        title: 'Approve Stock Request?',
        input: 'text',
        inputLabel: 'Manager Remarks / Comments',
        inputValue: 'Approved',
        showCancelButton: true,
        confirmButtonColor: '#10b981',
        confirmButtonText: 'Approve & Issue Stock',
        preConfirm: (comments) => {
            return comments || 'Approved';
        }
    }).then(async (result) => {
        if (result.isConfirmed) {
            Swal.fire({
                title: 'Executing Stock Issue...',
                allowOutsideClick: false,
                didOpen: () => { Swal.showLoading(); }
            });

            try {
                await apiFetch(`/api/approvals/${approvalId}/approve`, {
                    method: 'PUT',
                    body: {
                        approved_by: currentUser.user_id,
                        comments: result.value
                    }
                });

                Swal.fire("Success", "Request approved! Stock issued and database counts updated.", "success").then(() => {
                    loadApprovalsQueue();
                    updateAlertBadge();
                });
            } catch (e) {
                Swal.fire("Failed to Approve", e.message, "error");
            }
        }
    });
}

// ── REJECT STOCK REQUEST ────────────────────────────────────
function rejectRequestAction(approvalId) {
    Swal.fire({
        title: 'Reject Stock Request?',
        input: 'text',
        inputLabel: 'Reason for Rejection',
        inputValue: 'Rejected due to insufficient details',
        inputPlaceholder: 'Enter brief comment...',
        showCancelButton: true,
        confirmButtonColor: '#ef4444',
        confirmButtonText: 'Reject Request',
        preConfirm: (comments) => {
            if (!comments) {
                Swal.showValidationMessage('Reason is required');
                return false;
            }
            return comments;
        }
    }).then(async (result) => {
        if (result.isConfirmed) {
            Swal.fire({
                title: 'Updating status...',
                allowOutsideClick: false,
                didOpen: () => { Swal.showLoading(); }
            });

            try {
                await apiFetch(`/api/approvals/${approvalId}/reject`, {
                    method: 'PUT',
                    body: {
                        approved_by: currentUser.user_id,
                        comments: result.value
                    }
                });

                Swal.fire("Rejected", "Stock request has been marked as rejected.", "success").then(() => {
                    loadApprovalsQueue();
                });
            } catch (e) {
                Swal.fire("Failed", e.message, "error");
            }
        }
    });
}
