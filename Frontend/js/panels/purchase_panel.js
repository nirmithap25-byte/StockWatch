// Frontend/js/panels/purchase_panel.js

async function renderPurchasePanel(container) {
    container.innerHTML = `
        <div class="panel-header-section" id="purchase-header-section">
            <h2>Procurement & Purchase Orders</h2>
            <button class="btn-primary" onclick="showCreatePoForm()">
                <span class="material-symbols-outlined">add_shopping_cart</span>
                New Purchase Order
            </button>
        </div>

        <div id="purchase-content-area">
            <div class="table-card">
                <div class="table-header">
                    <span class="table-title">Purchase Orders Registry</span>
                    <div class="table-actions">
                        <div class="search-wrapper">
                            <span class="material-symbols-outlined">search</span>
                            <input type="text" id="po-search-input" placeholder="Search by PO number or supplier..." onkeyup="filterPoTable()">
                        </div>
                    </div>
                </div>
                <div class="table-wrapper">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>PO Number</th>
                                <th>Supplier</th>
                                <th>Order Date</th>
                                <th>Expected Delivery</th>
                                <th>Total Amount</th>
                                <th>Status</th>
                                <th>Created By</th>
                                <th>Approved By</th>
                                <th align="center">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="po-tbody">
                            <tr><td colspan="9" align="center" style="color:var(--text-secondary);">Loading purchase orders...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;

    loadPurchaseOrders();
}

let purchaseOrdersList = [];

async function loadPurchaseOrders() {
    try {
        const res = await apiFetch("/api/purchase/");
        const tbody = document.getElementById("po-tbody");
        if (tbody && res.success) {
            purchaseOrdersList = res.data;
            renderPoTableRows(purchaseOrdersList);
        }
    } catch (e) {
        console.error("Failed to load POs:", e);
        const tbody = document.getElementById("po-tbody");
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="9" align="center" style="color:var(--color-danger);">Error: ${e.message}</td></tr>`;
        }
    }
}

function renderPoTableRows(pos) {
    const tbody = document.getElementById("po-tbody");
    if (!tbody) return;

    if (pos.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" align="center" style="color:var(--text-secondary);">No purchase orders found.</td></tr>`;
        return;
    }

    tbody.innerHTML = "";
    pos.forEach(po => {
        const tr = document.createElement("tr");

        let statusClass = "badge pending";
        if (po.status === 'Approved') statusClass = "badge approved";
        if (po.status === 'Ordered') statusClass = "badge ordered";
        if (po.status === 'Partially Received') statusClass = "badge partially-received";
        if (po.status === 'Received') statusClass = "badge received";
        if (po.status === 'Cancelled') statusClass = "badge cancelled";

        const formattedTotal = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(po.total_amount || 0);

        tr.innerHTML = `
            <td style="font-family:monospace; font-weight:700; color:var(--accent-blue);">${po.po_number}</td>
            <td><strong>${po.supplier_name}</strong></td>
            <td>${po.order_date}</td>
            <td>${po.expected_delivery || 'N/A'}</td>
            <td style="font-weight:600;">${formattedTotal}</td>
            <td><span class="${statusClass}">${po.status}</span></td>
            <td>${po.ordered_by}</td>
            <td>${po.approved_by || '<span style="color:var(--text-muted);">Awaiting</span>'}</td>
            <td>
                <div class="action-btns" style="justify-content:center;">
                    <button class="btn-icon view" title="View Details" onclick="viewPurchaseOrderDetail(${po.po_id})">
                        <span class="material-symbols-outlined">visibility</span>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function filterPoTable() {
    const query = document.getElementById("po-search-input").value.toLowerCase().trim();
    if (!query) {
        renderPoTableRows(purchaseOrdersList);
        return;
    }

    const filtered = purchaseOrdersList.filter(po => 
        po.po_number.toLowerCase().includes(query) || 
        po.supplier_name.toLowerCase().includes(query) ||
        po.status.toLowerCase().includes(query)
    );
    renderPoTableRows(filtered);
}

// ── CREATE PURCHASE ORDER FORM ───────────────────────────────
let poItemRowsCount = 0;

async function showCreatePoForm() {
    // Fetch active items list for item select row dropdowns
    let itemsOptionsHtml = '<option value="">-- Choose Item --</option>';
    try {
        const itemsRes = await apiFetch("/api/inventory/items");
        if (itemsRes.success) {
            itemsRes.data.forEach(item => {
                itemsOptionsHtml += `<option value="${item.item_id}" data-price="${item.unit_price}">[${item.item_code}] ${item.item_name} (₹${item.unit_price})</option>`;
            });
        }
    } catch (e) {
        console.error("Failed to load select options:", e);
    }

    poItemRowsCount = 0;

    const area = document.getElementById("purchase-content-area");
    const header = document.getElementById("purchase-header-section");

    header.innerHTML = `
        <h2>Create Purchase Order</h2>
        <button class="btn-secondary" onclick="navigate('purchase')">
            <span class="material-symbols-outlined">arrow_back</span>
            Back to Registry
        </button>
    `;

    area.innerHTML = `
        <div class="chart-card" style="margin-bottom:30px;">
            <div class="form-grid" style="grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); margin-bottom:20px;">
                <div class="form-group">
                    <label>Select Supplier *</label>
                    <select id="po-supplier-id" required>
                        <option value="">Loading suppliers...</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Order Date *</label>
                    <input type="date" id="po-order-date" value="${new Date().toISOString().split('T')[0]}" required>
                </div>
                <div class="form-group">
                    <label>Expected Delivery Date</label>
                    <input type="date" id="po-expected-delivery">
                </div>
                <div class="form-group" style="grid-column: span 3;">
                    <label>Remarks / Instructions</label>
                    <input type="text" id="po-remarks" placeholder="Enter special delivery instructions or references">
                </div>
            </div>

            <h3 style="font-family:var(--font-heading); margin-bottom:15px; border-bottom:1px solid var(--border-color); padding-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
                Order Line Items
                <button class="btn-secondary" style="padding:6px 12px; font-size:12px;" onclick="addPoItemRow('${escapeHtml(itemsOptionsHtml)}')">
                    <span class="material-symbols-outlined" style="font-size:16px;">add</span> Add Row
                </button>
            </h3>

            <table class="po-items-table">
                <thead>
                    <tr style="text-align:left; font-size:12px; color:var(--text-secondary);">
                        <th style="width:50%;">Item Description *</th>
                        <th style="width:15%;">Quantity *</th>
                        <th style="width:15%;">Unit Price (₹) *</th>
                        <th style="width:15%;">Subtotal (₹)</th>
                        <th style="width:5%;">Action</th>
                    </tr>
                </thead>
                <tbody id="po-items-rows-tbody">
                    <!-- Dynamic row items go here -->
                </tbody>
            </table>

            <div style="display:flex; justify-content:flex-end; align-items:center; margin-top:20px; font-size:18px; font-weight:700;">
                <span style="margin-right:15px; font-family:var(--font-heading); font-size:15px; color:var(--text-secondary);">ESTIMATED TOTAL:</span>
                <span id="po-estimated-total" style="color:var(--accent-blue);">₹0.00</span>
            </div>

            <div style="margin-top:30px; display:flex; justify-content:flex-end; gap:12px;">
                <button class="btn-secondary" onclick="navigate('purchase')">Cancel</button>
                <button class="btn-primary" onclick="submitNewPurchaseOrder()">
                    <span class="material-symbols-outlined">shopping_cart_checkout</span>
                    Submit Purchase Order
                </button>
            </div>
        </div>
    `;

    // Populate suppliers dropdown
    loadSuppliersDropdown("po-supplier-id");

    // Add first item row automatically
    addPoItemRow(itemsOptionsHtml);
}

function escapeHtml(string) {
    return string.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

function unescapeHtml(safe) {
    return safe.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#039;/g, "'");
}

function addPoItemRow(optionsHtmlUnescaped) {
    poItemRowsCount++;
    const tbody = document.getElementById("po-items-rows-tbody");
    if (!tbody) return;

    const rowId = `po-row-${poItemRowsCount}`;
    const tr = document.createElement("tr");
    tr.id = rowId;

    tr.innerHTML = `
        <td>
            <select class="po-row-item-select" onchange="autoFillPoRowPrice('${rowId}')" style="width:100%;">
                ${unescapeHtml(optionsHtmlUnescaped)}
            </select>
        </td>
        <td>
            <input type="number" class="po-row-qty" min="1" value="1" oninput="calculatePoRowTotal('${rowId}')" style="width:100%;">
        </td>
        <td>
            <input type="number" step="0.01" class="po-row-price" min="0.01" value="0.00" oninput="calculatePoRowTotal('${rowId}')" style="width:100%;">
        </td>
        <td style="font-weight:600; color:var(--text-primary); padding-left:10px;">
            ₹<span class="po-row-subtotal">0.00</span>
        </td>
        <td>
            <button class="btn-icon delete" onclick="removePoItemRow('${rowId}')" style="margin:0 auto;">
                <span class="material-symbols-outlined">delete</span>
            </button>
        </td>
    `;
    tbody.appendChild(tr);
}

function removePoItemRow(rowId) {
    const row = document.getElementById(rowId);
    if (row) {
        row.parentNode.removeChild(row);
        calculatePoOrderTotal();
    }
}

function autoFillPoRowPrice(rowId) {
    const row = document.getElementById(rowId);
    if (row) {
        const select = row.querySelector(".po-row-item-select");
        const priceInput = row.querySelector(".po-row-price");
        const selectedOption = select.options[select.selectedIndex];
        
        if (selectedOption && selectedOption.dataset.price) {
            priceInput.value = parseFloat(selectedOption.dataset.price).toFixed(2);
        }
        calculatePoRowTotal(rowId);
    }
}

function calculatePoRowTotal(rowId) {
    const row = document.getElementById(rowId);
    if (row) {
        const qty = parseInt(row.querySelector(".po-row-qty").value) || 0;
        const price = parseFloat(row.querySelector(".po-row-price").value) || 0;
        const subtotalEl = row.querySelector(".po-row-subtotal");
        
        const total = qty * price;
        subtotalEl.innerText = total.toFixed(2);
        
        calculatePoOrderTotal();
    }
}

function calculatePoOrderTotal() {
    let grandTotal = 0;
    const subtotals = document.querySelectorAll(".po-row-subtotal");
    subtotals.forEach(span => {
        grandTotal += parseFloat(span.innerText) || 0;
    });

    const totalEl = document.getElementById("po-estimated-total");
    if (totalEl) {
        totalEl.innerText = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(grandTotal);
    }
}

async function submitNewPurchaseOrder() {
    const supplier_id = parseInt(document.getElementById("po-supplier-id").value);
    const order_date = document.getElementById("po-order-date").value;
    const expected_delivery = document.getElementById("po-expected-delivery").value;
    const remarks = document.getElementById("po-remarks").value.trim();

    if (isNaN(supplier_id) || !order_date) {
        Swal.fire("Validation Error", "Supplier and Order Date are required.", "error");
        return;
    }

    const items = [];
    const rows = document.querySelectorAll("#po-items-rows-tbody tr");
    
    for (let row of rows) {
        const item_id = parseInt(row.querySelector(".po-row-item-select").value);
        const quantity = parseInt(row.querySelector(".po-row-qty").value);
        const unit_price = parseFloat(row.querySelector(".po-row-price").value);

        if (isNaN(item_id) || isNaN(quantity) || quantity <= 0 || isNaN(unit_price) || unit_price <= 0) {
            Swal.fire("Validation Error", "All rows must have items, positive quantity, and valid unit price.", "error");
            return;
        }

        items.push({ item_id, quantity, unit_price });
    }

    if (items.length === 0) {
        Swal.fire("Validation Error", "Please add at least one line item to purchase.", "error");
        return;
    }

    Swal.fire({
        title: 'Submitting purchase order...',
        allowOutsideClick: false,
        didOpen: () => { Swal.showLoading(); }
    });

    try {
        const res = await apiFetch("/api/purchase/create", {
            method: 'POST',
            body: {
                supplier_id,
                order_date,
                expected_delivery: expected_delivery || null,
                remarks,
                items
            }
        });

        Swal.fire("Success", `Purchase Order ${res.po_number} created successfully!`, "success").then(() => {
            navigate("purchase");
        });

    } catch (e) {
        Swal.fire("Failed to create PO", e.message, "error");
    }
}

// ── VIEW PURCHASE ORDER DETAILS & WORKFLOWS ──────────────────
async function viewPurchaseOrderDetail(poId) {
    try {
        Swal.fire({
            title: 'Fetching details...',
            allowOutsideClick: false,
            didOpen: () => { Swal.showLoading(); }
        });

        const res = await apiFetch(`/api/purchase/${poId}`);
        Swal.close();

        if (!res.success || !res.purchase_order) {
            throw new Error("Failed to load PO details");
        }

        const po = res.purchase_order;
        const items = res.items;

        const header = document.getElementById("purchase-header-section");
        const area = document.getElementById("purchase-content-area");

        header.innerHTML = `
            <h2>Purchase Order: ${po.po_number}</h2>
            <button class="btn-secondary" onclick="navigate('purchase')">
                <span class="material-symbols-outlined">arrow_back</span>
                Back to Registry
            </button>
        `;

        let statusClass = "badge pending";
        if (po.status === 'Approved') statusClass = "badge approved";
        if (po.status === 'Ordered') statusClass = "badge ordered";
        if (po.status === 'Partially Received') statusClass = "badge partially-received";
        if (po.status === 'Received') statusClass = "badge received";
        if (po.status === 'Cancelled') statusClass = "badge cancelled";

        const formattedTotal = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(po.total_amount);

        // Build items table
        let itemsHtml = "";
        items.forEach(item => {
            const formattedItemPrice = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(item.unit_price);
            const formattedItemSubtotal = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(item.subtotal);
            
            // Context receipt input depending on status
            const showReceiveInput = (po.status === 'Approved' || po.status === 'Ordered' || po.status === 'Partially Received');
            const remaining = item.quantity - item.received_quantity;

            itemsHtml += `
                <tr>
                    <td style="font-family:monospace;">${item.item_code}</td>
                    <td><strong>${item.item_name}</strong></td>
                    <td align="center">${item.quantity} ${item.unit}</td>
                    <td align="center">${item.received_quantity} ${item.unit}</td>
                    <td>${formattedItemPrice}</td>
                    <td style="font-weight:600;">${formattedItemSubtotal}</td>
                    ${showReceiveInput ? `
                        <td>
                            <input type="number" class="po-item-receive-qty" 
                                   data-item-id="${item.po_item_id}" 
                                   min="0" max="${remaining}" value="${remaining}" 
                                   style="width:75px; padding:6px; font-weight:600; background:var(--bg-input); border:1px solid var(--border-color); color:white; border-radius:6px;">
                        </td>
                    ` : ''}
                </tr>
            `;
        });

        // Determine available actions based on user role and order status
        const isManager = (currentUser.role === 'Admin' || currentUser.role === 'Inventory Manager');
        const showApproveBtn = (po.status === 'Pending' && isManager && currentUser.user_id !== po.ordered_by); 
        const showCancelBtn = (po.status !== 'Cancelled' && po.status !== 'Received' && isManager);
        const showReceiveBtn = (po.status === 'Approved' || po.status === 'Ordered' || po.status === 'Partially Received');

        area.innerHTML = `
            <div class="chart-card" style="margin-bottom:30px;">
                <div class="form-grid" style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); margin-bottom:25px; border-bottom:1px solid var(--border-color); padding-bottom:20px;">
                    <div>
                        <span style="color:var(--text-secondary); font-size:11px;">SUPPLIER DETAILS</span>
                        <div style="font-weight:700; margin-top:4px; font-size:15px;">${po.supplier_name}</div>
                        <div style="font-size:12px; color:var(--text-secondary);">${po.supplier_email || ''} | ${po.supplier_phone || ''}</div>
                    </div>
                    <div>
                        <span style="color:var(--text-secondary); font-size:11px;">PO STATUS</span>
                        <div style="margin-top:6px;"><span class="${statusClass}" style="font-size:13px;">${po.status}</span></div>
                    </div>
                    <div>
                        <span style="color:var(--text-secondary); font-size:11px;">DATE INWARD</span>
                        <div style="font-weight:600; margin-top:4px;">Ordered: ${po.order_date}</div>
                        <div style="font-size:12px; color:var(--text-secondary);">Target: ${po.expected_delivery || 'Flexible'}</div>
                    </div>
                    <div>
                        <span style="color:var(--text-secondary); font-size:11px;">ESTIMATED VALUE</span>
                        <div style="font-weight:700; font-size:18px; color:var(--accent-blue); margin-top:4px;">${formattedTotal}</div>
                    </div>
                </div>

                <div style="margin-bottom:20px; font-size:13px; color:var(--text-secondary);">
                    <strong>Remarks / Audit Reference:</strong> ${po.remarks || 'No remarks provided'}
                </div>

                <h3 style="font-family:var(--font-heading); font-size:15px; margin-bottom:15px; border-bottom:1px solid var(--border-color); padding-bottom:8px;">Line Items Summary</h3>
                <div class="table-wrapper" style="margin-bottom:30px;">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Item Code</th>
                                <th>Description</th>
                                <th align="center">Ordered Qty</th>
                                <th align="center">Received Qty</th>
                                <th>Unit Price</th>
                                <th>Subtotal</th>
                                ${showReceiveBtn ? `<th style="width:120px;">Receive Now</th>` : ''}
                            </tr>
                        </thead>
                        <tbody>
                            ${itemsHtml}
                        </tbody>
                    </table>
                </div>

                <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:15px;">
                    <div class="action-logs" style="font-size:12px; color:var(--text-secondary);">
                        <div>Ordered by: <strong>${po.ordered_by}</strong></div>
                        <div>Approved by: <strong>${po.approved_by || 'Awaiting Authorization'}</strong> ${po.approved_date ? `on ${new Date(po.approved_date).toLocaleString()}` : ''}</div>
                    </div>
                    <div style="display:flex; gap:10px;">
                        ${showApproveBtn ? `
                            <button class="btn-primary" onclick="approvePurchaseOrderAction(${po.po_id})" style="background-color:var(--accent-teal);">
                                <span class="material-symbols-outlined">task_alt</span> Approve Order
                            </button>
                        ` : ''}
                        
                        ${showReceiveBtn ? `
                            <button class="btn-primary" onclick="submitReceiptPurchaseOrder(${po.po_id})">
                                <span class="material-symbols-outlined">inventory</span> Submit Stock Receipt
                            </button>
                        ` : ''}

                        ${showCancelBtn ? `
                            <button class="btn-secondary" onclick="cancelPurchaseOrderAction(${po.po_id})" style="color:var(--color-danger); border-color:var(--color-danger); background:none;">
                                <span class="material-symbols-outlined">cancel</span> Cancel PO
                            </button>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;

    } catch (e) {
        Swal.fire("Error", e.message, "error");
    }
}

// ── WORKFLOW: APPROVE PURCHASE ORDER ──────────────────────────
async function approvePurchaseOrderAction(poId) {
    Swal.fire({
        title: 'Approve Purchase Order?',
        text: "Approving this PO authorizes suppliers to ship items, making it eligible for receiving.",
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#0d9488', // Teal accent
        cancelButtonColor: '#374151',
        confirmButtonText: 'Approve'
    }).then(async (result) => {
        if (result.isConfirmed) {
            Swal.fire({
                title: 'Authorizing...',
                allowOutsideClick: false,
                didOpen: () => { Swal.showLoading(); }
            });

            try {
                await apiFetch(`/api/purchase/${poId}/approve`, {
                    method: 'PUT'
                });

                Swal.fire("Approved", "Purchase order approved successfully!", "success").then(() => {
                    viewPurchaseOrderDetail(poId);
                });
            } catch (e) {
                Swal.fire("Failure", e.message, "error");
            }
        }
    });
}

// ── WORKFLOW: CANCEL PURCHASE ORDER ───────────────────────────
function cancelPurchaseOrderAction(poId) {
    Swal.fire({
        title: 'Cancel Purchase Order?',
        input: 'text',
        inputLabel: 'Reason for Cancellation',
        inputPlaceholder: 'Enter brief reason...',
        inputAttributes: { required: 'true' },
        showCancelButton: true,
        confirmButtonColor: '#ef4444',
        confirmButtonText: 'Cancel Order',
        preConfirm: (reason) => {
            if (!reason) {
                Swal.showValidationMessage('Reason is required');
                return false;
            }
            return reason;
        }
    }).then(async (result) => {
        if (result.isConfirmed) {
            Swal.fire({
                title: 'Cancelling...',
                allowOutsideClick: false,
                didOpen: () => { Swal.showLoading(); }
            });

            try {
                await apiFetch(`/api/purchase/${poId}/cancel`, {
                    method: 'PUT',
                    body: { reason: result.value }
                });

                Swal.fire("Cancelled", "Purchase order has been cancelled.", "success").then(() => {
                    viewPurchaseOrderDetail(poId);
                });
            } catch (e) {
                Swal.fire("Failure", e.message, "error");
            }
        }
    });
}

// ── WORKFLOW: RECEIVE ITEMS STOCK ────────────────────────────
async function submitReceiptPurchaseOrder(poId) {
    const receiveItems = [];
    const inputs = document.querySelectorAll(".po-item-receive-qty");

    inputs.forEach(input => {
        const po_item_id = parseInt(input.dataset.itemId);
        const received_qty = parseInt(input.value) || 0;

        if (received_qty > 0) {
            receiveItems.push({ po_item_id, received_qty });
        }
    });

    if (receiveItems.length === 0) {
        Swal.fire("Zero Quantity", "Please specify receipt quantities greater than 0 on at least one line item.", "warning");
        return;
    }

    Swal.fire({
        title: 'Submitting Stock Inward...',
        allowOutsideClick: false,
        didOpen: () => { Swal.showLoading(); }
    });

    try {
        const res = await apiFetch(`/api/purchase/${poId}/receive`, {
            method: 'PUT',
            body: { items: receiveItems }
        });

        let successText = `Stock updated! PO Status is now: ${res.po_status}.`;
        if (res.invoice_number) {
            successText += `\n\nPO fully received! Invoice #${res.invoice_number} has been automatically generated under Invoices tab.`;
        }

        Swal.fire({
            icon: 'success',
            title: 'Receipt Inward Successful',
            text: successText,
            confirmButtonColor: '#3b82f6'
        }).then(() => {
            viewPurchaseOrderDetail(poId);
            updateAlertBadge();
        });

    } catch (e) {
        Swal.fire("Failed to receive stock", e.message, "error");
    }
}
