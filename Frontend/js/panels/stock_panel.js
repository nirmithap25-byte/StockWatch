// Frontend/js/panels/stock_panel.js

async function renderStockPanel(container) {
    const isManager = currentUser.role === 'Admin' || currentUser.role === 'Inventory Manager';

    container.innerHTML = `
        <div class="panel-header-section">
            <h2>Stock Movements & Transactions</h2>
        </div>

        <div class="charts-grid" style="grid-template-columns: 1fr 2fr; align-items: start;">
            <!-- Left Side: Transaction Forms -->
            <div class="chart-card">
                <div class="chart-header">
                    <span class="chart-title" style="color:var(--accent-blue);">Record Stock Transaction</span>
                </div>
                
                <div class="form-group">
                    <label>Transaction Type *</label>
                    <select id="stock-tx-type" onchange="toggleStockFields()">
                        <option value="IN">Stock IN (+)</option>
                        <option value="OUT">Stock OUT (-)</option>
                        <option value="TRANSFER">Internal Department Transfer</option>
                        ${isManager ? `<option value="ADJUSTMENT">Quantity Adjustment (Admin)</option>` : ''}
                    </select>
                </div>

                <div class="form-group">
                    <label>Select Item *</label>
                    <select id="stock-item-id" onchange="updateStockItemPreview()"></select>
                </div>

                <div id="stock-preview-status" style="font-size:12px; margin-bottom:15px; color:var(--text-secondary); padding: 8px; background: rgba(255,255,255,0.03); border-radius:6px; display:none;">
                    <!-- Stock preview description -->
                </div>

                <!-- Dynamic inputs based on type -->
                <div id="stock-qty-group" class="form-group">
                    <label id="stock-qty-label">Quantity *</label>
                    <input type="number" id="stock-quantity" min="1" value="1">
                </div>

                <div id="stock-dept-transfer-group" style="display:none; gap:10px;" class="form-grid">
                    <div class="form-group">
                        <label>From Department *</label>
                        <select id="stock-from-dept"></select>
                    </div>
                    <div class="form-group">
                        <label>To Department *</label>
                        <select id="stock-to-dept"></select>
                    </div>
                </div>

                <div class="form-group">
                    <label>Reason / Remark *</label>
                    <input type="text" id="stock-reason" placeholder="e.g. Inward batch / Issue to IT Dept">
                </div>

                <button class="btn-primary" style="width:100%; justify-content:center; margin-top:10px;" onclick="submitStockTransaction()">
                    <span class="material-symbols-outlined">send</span>
                    Execute Transaction
                </button>
            </div>

            <!-- Right Side: Movements History List -->
            <div class="table-card" style="margin-bottom: 0;">
                <div class="table-header">
                    <span class="table-title">Movements Transaction Log</span>
                </div>
                <div class="table-wrapper" style="max-height: 480px; overflow-y:auto;">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Date/Time</th>
                                <th>Item</th>
                                <th>Type</th>
                                <th>Qty</th>
                                <th>Stock Flow</th>
                                <th>Context</th>
                                <th>Operator</th>
                            </tr>
                        </thead>
                        <tbody id="stock-movements-tbody">
                            <tr><td colspan="7" align="center" style="color:var(--text-secondary);">Loading logs...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;

    // Populate active items dropdown and departments
    loadStockItemSelect();
    loadDepartmentsDropdown("stock-from-dept");
    loadDepartmentsDropdown("stock-to-dept");

    // Load logs
    loadStockMovementsHistory();
}

let activeItemsList = [];

async function loadStockItemSelect() {
    try {
        const res = await apiFetch("/api/inventory/items");
        const select = document.getElementById("stock-item-id");
        if (select && res.success) {
            activeItemsList = res.data;
            select.innerHTML = '<option value="">-- Select Inventory Item --</option>';
            res.data.forEach(item => {
                const opt = document.createElement("option");
                opt.value = item.item_id;
                opt.innerText = `[${item.item_code}] ${item.item_name}`;
                select.appendChild(opt);
            });
        }
    } catch (e) {
        console.error(e);
    }
}

function updateStockItemPreview() {
    const itemId = parseInt(document.getElementById("stock-item-id").value);
    const preview = document.getElementById("stock-preview-status");

    if (isNaN(itemId)) {
        preview.style.display = "none";
        return;
    }

    const item = activeItemsList.find(i => i.item_id === itemId);
    if (item) {
        preview.innerHTML = `
            <strong>Available Stock:</strong> ${item.quantity} ${item.unit} <br>
            <strong>Default Dept:</strong> ${item.department_name}
        `;
        preview.style.display = "block";

        // Pre-fill department defaults if it's a transfer
        const fromDeptSelect = document.getElementById("stock-from-dept");
        if (fromDeptSelect) {
            // Find option that matches item's department_id
            for (let opt of fromDeptSelect.options) {
                if (opt.text.trim() === item.department_name.trim()) {
                    opt.selected = true;
                    break;
                }
            }
        }
    }
}

function toggleStockFields() {
    const type = document.getElementById("stock-tx-type").value;
    const qtyLabel = document.getElementById("stock-qty-label");
    const qtyInput = document.getElementById("stock-quantity");
    const deptTransferGroup = document.getElementById("stock-dept-transfer-group");

    if (type === 'TRANSFER') {
        deptTransferGroup.style.display = "grid";
        qtyLabel.innerText = "Quantity *";
        qtyInput.placeholder = "";
    } else {
        deptTransferGroup.style.display = "none";
        if (type === 'ADJUSTMENT') {
            qtyLabel.innerText = "New Stock Balance Quantity *";
            qtyInput.placeholder = "Enter absolute new quantity";
        } else {
            qtyLabel.innerText = "Quantity *";
            qtyInput.placeholder = "";
        }
    }
}

async function submitStockTransaction() {
    const type = document.getElementById("stock-tx-type").value;
    const itemId = parseInt(document.getElementById("stock-item-id").value);
    const qty = parseInt(document.getElementById("stock-quantity").value);
    const reason = document.getElementById("stock-reason").value.trim();

    if (isNaN(itemId)) {
        Swal.fire("Validation Error", "Please select an inventory item", "error");
        return;
    }
    if (isNaN(qty) || qty < 0) {
        Swal.fire("Validation Error", "Quantity must be 0 or more", "error");
        return;
    }
    if (!reason) {
        Swal.fire("Validation Error", "Reason/Remark is required", "error");
        return;
    }

    const item = activeItemsList.find(i => i.item_id === itemId);

    // Validate quantities for OUT/TRANSFER
    if ((type === 'OUT' || type === 'TRANSFER') && qty > item.quantity) {
        Swal.fire("Insufficient Stock", `Cannot deduct ${qty} units. Only ${item.quantity} available.`, "error");
        return;
    }

    Swal.fire({
        title: 'Executing Transaction...',
        allowOutsideClick: false,
        didOpen: () => { Swal.showLoading(); }
    });

    try {
        let endpoint = "";
        let body = { item_id: itemId, reason };

        if (type === 'IN') {
            endpoint = "/api/stock/in";
            body.quantity = qty;
        } else if (type === 'OUT') {
            endpoint = "/api/stock/out";
            body.quantity = qty;
        } else if (type === 'ADJUSTMENT') {
            endpoint = "/api/stock/adjustment";
            body.new_quantity = qty;
        } else if (type === 'TRANSFER') {
            const fromDept = parseInt(document.getElementById("stock-from-dept").value);
            const toDept = parseInt(document.getElementById("stock-to-dept").value);

            if (isNaN(fromDept) || isNaN(toDept)) {
                Swal.fire("Validation Error", "Please select from/to departments", "error");
                return;
            }
            if (fromDept === toDept) {
                Swal.fire("Validation Error", "Source and destination departments must be different", "error");
                return;
            }

            endpoint = "/api/stock/transfer";
            body.quantity = qty;
            body.from_department_id = fromDept;
            body.to_department_id = toDept;
        }

        const res = await apiFetch(endpoint, {
            method: 'POST',
            body: body
        });

        Swal.fire("Success", res.message, "success").then(() => {
            navigate("stock");
            updateAlertBadge();
        });

    } catch (e) {
        Swal.fire("Transaction Failed", e.message, "error");
    }
}

async function loadStockMovementsHistory() {
    try {
        const res = await apiFetch("/api/stock/movements");
        const tbody = document.getElementById("stock-movements-tbody");
        if (tbody && res.success) {
            if (res.data.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" align="center" style="color:var(--text-secondary);">No movements history found.</td></tr>`;
                return;
            }

            tbody.innerHTML = "";
            res.data.forEach(log => {
                const tr = document.createElement("tr");

                let typeColor = "badge pending";
                if (log.movement_type === 'IN') typeColor = 'badge received';
                if (log.movement_type === 'OUT') typeColor = 'badge cancelled';
                if (log.movement_type === 'TRANSFER') typeColor = 'badge approved';
                if (log.movement_type === 'ADJUSTMENT') typeColor = 'badge ordered';

                // Stock Flow Display
                let flow = "";
                if (log.movement_type === 'IN') flow = `${log.previous_quantity} → ${log.new_quantity} (+${log.quantity})`;
                else if (log.movement_type === 'OUT') flow = `${log.previous_quantity} → ${log.new_quantity} (-${log.quantity})`;
                else if (log.movement_type === 'TRANSFER') flow = `Dept: ${log.from_department || 'N/A'} ➜ ${log.to_department || 'N/A'}`;
                else if (log.movement_type === 'ADJUSTMENT') {
                    const diff = log.new_quantity - log.previous_quantity;
                    flow = `${log.previous_quantity} → ${log.new_quantity} (${diff > 0 ? '+' : ''}${diff})`;
                }

                tr.innerHTML = `
                    <td style="color:var(--text-secondary); font-size:11px;">${new Date(log.movement_date).toLocaleString()}</td>
                    <td>
                        <div style="font-weight:600; color:var(--text-primary);">${log.item_name}</div>
                        <div style="font-size:10px; font-family:monospace; color:var(--text-secondary);">${log.item_code}</div>
                    </td>
                    <td><span class="${typeColor}">${log.movement_type}</span></td>
                    <td><strong>${log.quantity} ${log.unit}</strong></td>
                    <td style="font-size:12px; color:var(--text-secondary);">${flow}</td>
                    <td>
                        <div style="font-size:12px;">${log.reason}</div>
                        <div style="font-size:10px; color:var(--text-muted);">${log.reference_type} Ref #${log.reference_id || 'None'}</div>
                    </td>
                    <td>${log.performed_by}</td>
                `;
                tbody.appendChild(tr);
            });
        }
    } catch (e) {
        console.error(e);
        const tbody = document.getElementById("stock-movements-tbody");
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="7" align="center" style="color:var(--color-danger);">Error: ${e.message}</td></tr>`;
        }
    }
}
