// Frontend/js/panels/inventory_panel.js

async function renderInventoryPanel(container) {
    const isEditAuthorized = currentUser.role === 'Admin' || currentUser.role === 'Inventory Manager';

    container.innerHTML = `
        <div class="panel-header-section">
            <h2>Inventory Directory</h2>
            ${isEditAuthorized ? `
                <button class="btn-primary" onclick="openAddItemModal()">
                    <span class="material-symbols-outlined">add</span>
                    New Inventory Item
                </button>
            ` : ''}
        </div>

        <div class="table-card">
            <div class="table-header">
                <span class="table-title">Inventory Items List</span>
                <div class="table-actions">
                    <div class="search-wrapper">
                        <span class="material-symbols-outlined">search</span>
                        <input type="text" id="inventory-search-input" placeholder="Search by name or code..." onkeyup="filterInventoryTable()">
                    </div>
                </div>
            </div>
            <div class="table-wrapper">
                <table class="data-table" id="inventory-table">
                    <thead>
                        <tr>
                            <th>Code</th>
                            <th>Item Name</th>
                            <th>Category</th>
                            <th>Stock</th>
                            <th>Unit Price</th>
                            <th>Total Value</th>
                            <th>Department</th>
                            <th>Supplier</th>
                            <th align="center">Actions</th>
                        </tr>
                    </thead>
                    <tbody id="inventory-tbody">
                        <tr><td colspan="9" align="center" style="color:var(--text-secondary);">Loading inventory...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    `;

    loadInventoryItems();
}

let inventoryItemsList = [];

async function loadInventoryItems() {
    try {
        const res = await apiFetch("/api/inventory/items");
        const tbody = document.getElementById("inventory-tbody");
        if (tbody && res.success) {
            inventoryItemsList = res.data;
            renderInventoryTableRows(inventoryItemsList);
        }
    } catch (e) {
        console.error("Failed to load inventory:", e);
        const tbody = document.getElementById("inventory-tbody");
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="9" align="center" style="color:var(--color-danger);">Error: ${e.message}</td></tr>`;
        }
    }
}

function renderInventoryTableRows(items) {
    const tbody = document.getElementById("inventory-tbody");
    if (!tbody) return;

    if (items.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" align="center" style="color:var(--text-secondary);">No active inventory items found.</td></tr>`;
        return;
    }

    const isEditAuthorized = currentUser.role === 'Admin' || currentUser.role === 'Inventory Manager';

    tbody.innerHTML = "";
    items.forEach(item => {
        const tr = document.createElement("tr");

        let statusClass = "badge available";
        if (item.quantity === 0) statusClass = "badge out-of-stock";
        else if (item.quantity <= item.minimum_stock) statusClass = "badge critical";
        else if (item.quantity <= item.reorder_level) statusClass = "badge low";

        const formattedPrice = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(item.unit_price);
        const formattedTotal = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(item.quantity * item.unit_price);

        tr.innerHTML = `
            <td style="font-family:monospace; font-weight:600;">${item.item_code}</td>
            <td>
                <div style="font-weight:600; color:var(--text-primary);">${item.item_name}</div>
                <div style="font-size:11px; color:var(--text-secondary); max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${item.description || 'No description'}</div>
            </td>
            <td><span class="badge" style="background:rgba(255,255,255,0.05); color:var(--text-primary);">${item.category_name}</span></td>
            <td>
                <span class="${statusClass}">${item.quantity}</span>
                <span style="font-size:10px; color:var(--text-secondary);">${item.unit}</span>
            </td>
            <td>${formattedPrice}</td>
            <td style="font-weight:600;">${formattedTotal}</td>
            <td>${item.department_name}</td>
            <td>${item.supplier_name}</td>
            <td>
                <div class="action-btns" style="justify-content:center;">
                    <button class="btn-icon view" title="QR Code" onclick="showItemQrModal(${item.item_id})">
                        <span class="material-symbols-outlined">qr_code_2</span>
                    </button>
                    ${isEditAuthorized ? `
                        <button class="btn-icon edit" title="Edit Item" onclick="openEditItemModal(${item.item_id})">
                            <span class="material-symbols-outlined">edit</span>
                        </button>
                        <button class="btn-icon delete" title="Deactivate" onclick="deleteItemAction(${item.item_id})">
                            <span class="material-symbols-outlined">delete</span>
                        </button>
                    ` : ''}
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function filterInventoryTable() {
    const query = document.getElementById("inventory-search-input").value.toLowerCase().trim();
    if (!query) {
        renderInventoryTableRows(inventoryItemsList);
        return;
    }

    const filtered = inventoryItemsList.filter(item => 
        item.item_name.toLowerCase().includes(query) || 
        item.item_code.toLowerCase().includes(query) ||
        item.category_name.toLowerCase().includes(query) ||
        item.department_name.toLowerCase().includes(query)
    );
    renderInventoryTableRows(filtered);
}

// ── ADD ITEM MODAL ───────────────────────────────────────────
async function openAddItemModal() {
    const randomCode = "SW-" + Date.now().toString().slice(-6);
    const randomQr = "QR-" + Math.random().toString(36).substring(2, 8).toUpperCase();

    const bodyHtml = `
        <form id="item-form" class="form-grid">
            <div class="form-group">
                <label>Item Code *</label>
                <input type="text" id="form-item-code" value="${randomCode}" required>
            </div>
            <div class="form-group">
                <label>Item Name *</label>
                <input type="text" id="form-item-name" placeholder="Dell Latitude Laptop" required>
            </div>
            <div class="form-group" style="grid-column: span 2;">
                <label>Description</label>
                <textarea id="form-description" rows="2" placeholder="Write item specification details..."></textarea>
            </div>
            <div class="form-group">
                <label>Category *</label>
                <select id="form-category-id" required>
                    <option value="">Loading categories...</option>
                </select>
            </div>
            <div class="form-group">
                <label>Supplier *</label>
                <select id="form-supplier-id" required>
                    <option value="">Loading suppliers...</option>
                </select>
            </div>
            <div class="form-group">
                <label>Department *</label>
                <select id="form-department-id" required>
                    <option value="">Loading departments...</option>
                </select>
            </div>
            <div class="form-group">
                <label>Initial Quantity *</label>
                <input type="number" id="form-quantity" min="0" value="0" required>
            </div>
            <div class="form-group">
                <label>Unit *</label>
                <input type="text" id="form-unit" value="Nos" placeholder="Nos, Kgs, Ltrs" required>
            </div>
            <div class="form-group">
                <label>Unit Price (₹) *</label>
                <input type="number" step="0.01" id="form-unit-price" min="0.01" placeholder="65000.00" required>
            </div>
            <div class="form-group">
                <label>Min Stock Level *</label>
                <input type="number" id="form-min-stock" min="1" value="5" required>
            </div>
            <div class="form-group">
                <label>Reorder Alert Level *</label>
                <input type="number" id="form-reorder-level" min="1" value="10" required>
            </div>
            <div class="form-group">
                <label>Reorder Quantity *</label>
                <input type="number" id="form-reorder-qty" min="1" value="20" required>
            </div>
            <div class="form-group" style="grid-column: span 2;">
                <label>QR Code String *</label>
                <input type="text" id="form-qr-code" value="${randomQr}" required>
            </div>
        </form>
    `;

    showModal("Add New Inventory Item", bodyHtml, "Save Item", async () => {
        // Validation
        const item_code = document.getElementById("form-item-code").value.trim();
        const item_name = document.getElementById("form-item-name").value.trim();
        const description = document.getElementById("form-description").value.trim();
        const category_id = parseInt(document.getElementById("form-category-id").value);
        const supplier_id = parseInt(document.getElementById("form-supplier-id").value);
        const department_id = parseInt(document.getElementById("form-department-id").value);
        const quantity = parseInt(document.getElementById("form-quantity").value);
        const unit = document.getElementById("form-unit").value.trim();
        const unit_price = parseFloat(document.getElementById("form-unit-price").value);
        const minimum_stock = parseInt(document.getElementById("form-min-stock").value);
        const reorder_level = parseInt(document.getElementById("form-reorder-level").value);
        const reorder_quantity = parseInt(document.getElementById("form-reorder-qty").value);
        const qr_code = document.getElementById("form-qr-code").value.trim();

        if (!item_code || !item_name || isNaN(category_id) || isNaN(supplier_id) || isNaN(department_id) || isNaN(quantity) || !unit || isNaN(unit_price) || isNaN(minimum_stock) || isNaN(reorder_level) || isNaN(reorder_quantity) || !qr_code) {
            Swal.fire("Validation Error", "Please fill in all required fields correctly", "error");
            return;
        }

        try {
            await apiFetch("/api/inventory/items", {
                method: "POST",
                body: {
                    item_code, item_name, description, category_id,
                    supplier_id, department_id, quantity, minimum_stock,
                    reorder_level, reorder_quantity, unit, unit_price, qr_code
                }
            });

            closeModal();
            Swal.fire("Success", "Item added to inventory successfully!", "success");
            loadInventoryItems();
            updateAlertBadge();
        } catch (e) {
            Swal.fire("Failure", e.message, "error");
        }
    });

    // Populate dropdowns
    loadCategoriesDropdown("form-category-id");
    loadSuppliersDropdown("form-supplier-id");
    loadDepartmentsDropdown("form-department-id");
}

// ── EDIT ITEM MODAL ──────────────────────────────────────────
async function openEditItemModal(itemId) {
    try {
        Swal.fire({
            title: 'Fetching item details...',
            allowOutsideClick: false,
            didOpen: () => { Swal.showLoading(); }
        });

        const res = await apiFetch(`/api/inventory/items/${itemId}`);
        Swal.close();

        if (!res.success || !res.data) throw new Error("Item not found");
        const item = res.data;

        const bodyHtml = `
            <form id="item-form" class="form-grid">
                <div class="form-group">
                    <label>Item Code (Read-Only)</label>
                    <input type="text" id="form-item-code" value="${item.item_code}" disabled style="background-color:rgba(255,255,255,0.05); cursor:not-allowed;">
                </div>
                <div class="form-group">
                    <label>Item Name *</label>
                    <input type="text" id="form-item-name" value="${item.item_name}" required>
                </div>
                <div class="form-group" style="grid-column: span 2;">
                    <label>Description</label>
                    <textarea id="form-description" rows="2">${item.description || ''}</textarea>
                </div>
                <div class="form-group">
                    <label>Category *</label>
                    <select id="form-category-id" required></select>
                </div>
                <div class="form-group">
                    <label>Supplier *</label>
                    <select id="form-supplier-id" required></select>
                </div>
                <div class="form-group">
                    <label>Department *</label>
                    <select id="form-department-id" required></select>
                </div>
                <div class="form-group">
                    <label>Stock Qty (Managed via Stock Movements)</label>
                    <input type="number" value="${item.quantity}" disabled style="background-color:rgba(255,255,255,0.05); cursor:not-allowed;">
                </div>
                <div class="form-group">
                    <label>Unit *</label>
                    <input type="text" id="form-unit" value="${item.unit}" required>
                </div>
                <div class="form-group">
                    <label>Unit Price (₹) *</label>
                    <input type="number" step="0.01" id="form-unit-price" value="${item.unit_price}" min="0.01" required>
                </div>
                <div class="form-group">
                    <label>Min Stock Level *</label>
                    <input type="number" id="form-min-stock" value="${item.minimum_stock}" min="1" required>
                </div>
                <div class="form-group">
                    <label>Reorder Alert Level *</label>
                    <input type="number" id="form-reorder-level" value="${item.reorder_level}" min="1" required>
                </div>
                <div class="form-group">
                    <label>Reorder Quantity *</label>
                    <input type="number" id="form-reorder-qty" value="${item.reorder_quantity}" min="1" required>
                </div>
                <div class="form-group" style="grid-column: span 2;">
                    <label>QR Code String (Read-Only)</label>
                    <input type="text" value="${item.qr_code}" disabled style="background-color:rgba(255,255,255,0.05); cursor:not-allowed;">
                </div>
            </form>
        `;

        showModal("Edit Inventory Item", bodyHtml, "Save Changes", async () => {
            const item_name = document.getElementById("form-item-name").value.trim();
            const description = document.getElementById("form-description").value.trim();
            const category_id = parseInt(document.getElementById("form-category-id").value);
            const supplier_id = parseInt(document.getElementById("form-supplier-id").value);
            const department_id = parseInt(document.getElementById("form-department-id").value);
            const unit = document.getElementById("form-unit").value.trim();
            const unit_price = parseFloat(document.getElementById("form-unit-price").value);
            const minimum_stock = parseInt(document.getElementById("form-min-stock").value);
            const reorder_level = parseInt(document.getElementById("form-reorder-level").value);
            const reorder_quantity = parseInt(document.getElementById("form-reorder-qty").value);

            if (!item_name || isNaN(category_id) || isNaN(supplier_id) || isNaN(department_id) || !unit || isNaN(unit_price) || isNaN(minimum_stock) || isNaN(reorder_level) || isNaN(reorder_quantity)) {
                Swal.fire("Validation Error", "Please fill in all required fields", "error");
                return;
            }

            try {
                await apiFetch(`/api/inventory/items/${itemId}`, {
                    method: "PUT",
                    body: {
                        item_name, description, category_id,
                        supplier_id, department_id, minimum_stock,
                        reorder_level, reorder_quantity, unit, unit_price,
                        is_active: 'Yes'
                    }
                });

                closeModal();
                Swal.fire("Success", "Item updated successfully!", "success");
                loadInventoryItems();
                updateAlertBadge();
            } catch (e) {
                Swal.fire("Failure", e.message, "error");
            }
        });

        // Load dropdowns and pre-select current values
        loadCategoriesDropdown("form-category-id", item.category_id);
        loadSuppliersDropdown("form-supplier-id", item.supplier_id);
        loadDepartmentsDropdown("form-department-id", item.department_id);

    } catch (e) {
        Swal.fire("Error", e.message, "error");
    }
}

// ── VIEW QR CODE MODAL ────────────────────────────────────────
async function showItemQrModal(itemId) {
    try {
        const item = inventoryItemsList.find(i => i.item_id === itemId);
        if (!item) return;

        const bodyHtml = `
            <div style="text-align: center; padding: 15px;">
                <p style="font-size: 15px; font-weight:600; margin-bottom: 15px;">QR Identification for: ${item.item_name}</p>
                <div style="background: white; display: inline-block; padding: 15px; border-radius: 12px; margin-bottom: 15px;">
                    <img src="${API_BASE}/api/qr/generate/${item.qr_code}" alt="Item QR" style="width: 200px; height: 200px; display: block;">
                </div>
                <p style="font-family: monospace; font-size: 16px; font-weight:700; color:var(--accent-blue);">${item.qr_code}</p>
                <p style="font-size:12px; color:var(--text-secondary); margin-top:5px;">Scanned via webcam inside StockWatch app for instant transactions.</p>
            </div>
        `;

        showModal("Inventory Item QR Code", bodyHtml, "Download QR Code", () => {
            downloadItemQr(item.qr_code, item.item_name);
            closeModal();
        });
        
    } catch (e) {
        console.error(e);
    }
}

// ── DELETE (DEACTIVATE) ITEM ACTION ───────────────────────────
function deleteItemAction(itemId) {
    const item = inventoryItemsList.find(i => i.item_id === itemId);
    if (!item) return;

    Swal.fire({
        title: 'Deactivate Item?',
        text: `Are you sure you want to deactivate "${item.item_name}"? This soft-deletes the item from active views.`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#ef4444',
        cancelButtonColor: '#374151',
        confirmButtonText: 'Deactivate'
    }).then(async (result) => {
        if (result.isConfirmed) {
            Swal.fire({
                title: 'Deactivating...',
                allowOutsideClick: false,
                didOpen: () => { Swal.showLoading(); }
            });

            try {
                await apiFetch(`/api/inventory/items/${itemId}`, {
                    method: 'DELETE'
                });

                Swal.fire("Deactivated", "Item was deactivated successfully", "success");
                loadInventoryItems();
            } catch (e) {
                Swal.fire("Failed", e.message, "error");
            }
        }
    });
}
