// Frontend/js/panels/invoices_panel.js

async function renderInvoicesPanel(container) {
    container.innerHTML = `
        <div class="panel-header-section" id="invoice-header-section">
            <h2>Financial Invoices</h2>
        </div>

        <div id="invoice-content-area">
            <div class="table-card">
                <div class="table-header">
                    <span class="table-title">Invoices Records Ledger</span>
                    <div class="table-actions">
                        <div class="search-wrapper">
                            <span class="material-symbols-outlined">search</span>
                            <input type="text" id="invoice-search-input" placeholder="Search invoices..." onkeyup="filterInvoiceTable()">
                        </div>
                    </div>
                </div>
                <div class="table-wrapper">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Invoice Number</th>
                                <th>Supplier</th>
                                <th>Order PO Ref</th>
                                <th>Total Bill Amount</th>
                                <th>Billing Status</th>
                                <th>Date Generated</th>
                                <th>Billed By</th>
                                <th align="center">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="invoice-tbody">
                            <tr><td colspan="8" align="center" style="color:var(--text-secondary);">Loading financial ledger...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;

    loadInvoicesLedger();
}

let invoicesLedgerList = [];

async function loadInvoicesLedger() {
    try {
        const res = await apiFetch("/api/invoices/");
        const tbody = document.getElementById("invoice-tbody");
        if (tbody && res.success) {
            invoicesLedgerList = res.data;
            renderInvoiceTableRows(invoicesLedgerList);
        }
    } catch (e) {
        console.error(e);
        const tbody = document.getElementById("invoice-tbody");
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="8" align="center" style="color:var(--color-danger);">Error: ${e.message}</td></tr>`;
        }
    }
}

function renderInvoiceTableRows(invs) {
    const tbody = document.getElementById("invoice-tbody");
    if (!tbody) return;

    if (invs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" align="center" style="color:var(--text-secondary);">No invoices recorded.</td></tr>`;
        return;
    }

    tbody.innerHTML = "";
    invs.forEach(inv => {
        const tr = document.createElement("tr");

        let statusClass = "badge received"; // Emerald for Finalized
        if (inv.status === 'Draft') statusClass = "badge pending"; // Yellow
        if (inv.status === 'Cancelled') statusClass = "badge cancelled"; // Red

        const formattedTotal = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(inv.total_amount);

        tr.innerHTML = `
            <td style="font-family:monospace; font-weight:700; color:var(--accent-blue);">${inv.invoice_number}</td>
            <td><strong>${inv.supplier_name}</strong></td>
            <td style="font-family:monospace;">${inv.po_number}</td>
            <td style="font-weight:600; color:var(--text-primary);">${formattedTotal}</td>
            <td><span class="${statusClass}">${inv.status}</span></td>
            <td style="color:var(--text-secondary); font-size:11px;">${new Date(inv.generated_at).toLocaleString()}</td>
            <td>${inv.generated_by}</td>
            <td>
                <div class="action-btns" style="justify-content:center;">
                    <button class="btn-icon view" title="View Bill" onclick="viewInvoiceReceiptDetails(${inv.invoice_id})">
                        <span class="material-symbols-outlined">receipt_long</span>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function filterInvoiceTable() {
    const query = document.getElementById("invoice-search-input").value.toLowerCase().trim();
    if (!query) {
        renderInvoiceTableRows(invoicesLedgerList);
        return;
    }

    const filtered = invoicesLedgerList.filter(inv => 
        inv.invoice_number.toLowerCase().includes(query) || 
        inv.supplier_name.toLowerCase().includes(query) ||
        inv.po_number.toLowerCase().includes(query) ||
        inv.status.toLowerCase().includes(query)
    );
    renderInvoiceTableRows(filtered);
}

// ── PRINTABLE BILL VIEW ──────────────────────────────────────
async function viewInvoiceReceiptDetails(invoiceId) {
    try {
        Swal.fire({
            title: 'Compiling invoice statement...',
            allowOutsideClick: false,
            didOpen: () => { Swal.showLoading(); }
        });

        const res = await apiFetch(`/api/invoices/view/${invoiceId}`);
        Swal.close();

        if (!res.success || !res.invoice) {
            throw new Error("Failed to load invoice receipt");
        }

        const inv = res.invoice;

        const header = document.getElementById("invoice-header-section");
        const area = document.getElementById("invoice-content-area");

        header.innerHTML = `
            <h2>Invoice Receipt: ${inv.invoice_number}</h2>
            <div style="display:flex; gap:10px;">
                <button class="btn-secondary" onclick="navigate('invoices')">
                    <span class="material-symbols-outlined">arrow_back</span> Back
                </button>
                <button class="btn-primary" onclick="window.print()" style="background-color:var(--accent-teal);">
                    <span class="material-symbols-outlined">print</span> Print
                </button>
                ${(inv.status !== 'Cancelled' && (currentUser.role === 'Admin' || currentUser.role === 'Inventory Manager')) ? `
                    <button class="btn-secondary" onclick="cancelInvoiceAction(${inv.invoice_id})" style="color:var(--color-danger); border-color:var(--color-danger); background:none;">
                        <span class="material-symbols-outlined">cancel</span> Cancel Invoice
                    </button>
                ` : ''}
            </div>
        `;

        // Render printable container
        let rowsHtml = "";
        inv.items.forEach((item, index) => {
            rowsHtml += `
                <tr>
                    <td>${index + 1}</td>
                    <td><strong>${item.item_name}</strong><br><span style="font-size:10px; font-family:monospace; color:#666;">Code: ${item.item_code}</span></td>
                    <td align="center">${item.quantity} ${item.unit}</td>
                    <td align="right">₹${item.unit_price.toFixed(2)}</td>
                    <td align="right" style="font-weight:600;">₹${item.subtotal.toFixed(2)}</td>
                </tr>
            `;
        });

        area.innerHTML = `
            <div class="invoice-print-container" id="printable-area">
                <div class="invoice-header-row">
                    <div>
                        <h1 style="font-family:var(--font-heading); font-weight:800; font-size:28px; color:var(--accent-blue); letter-spacing:-0.5px; display:flex; align-items:center; gap:8px;">
                            <span class="material-symbols-outlined" style="font-size:32px; color:#2563eb;">monitoring</span>
                            StockWatch
                        </h1>
                        <p style="font-size:12px; color:#666; margin-top:5px;">Smarter Inventory & Safer Audits major project</p>
                    </div>
                    <div style="text-align: right;">
                        <h2 style="font-family:var(--font-heading); font-weight:700; font-size:18px;">INVOICE STATEMENT</h2>
                        <p style="font-family:monospace; font-weight:700; color:#2563eb; font-size:15px; margin-top:5px;">${inv.invoice_number}</p>
                        <p style="font-size:12px; color:#666;">Date: ${new Date(inv.generated_at).toLocaleString()}</p>
                    </div>
                </div>

                <div class="invoice-billing-row">
                    <div class="invoice-bill-col">
                        <span style="font-size:10px; font-weight:700; color:#9ca3af; letter-spacing:0.5px; text-transform:uppercase;">Invoiced By:</span>
                        <div style="font-weight:700; margin-top:5px; font-size:15px;">StockWatch Organization</div>
                        <div style="font-size:12px; color:#555; margin-top:2px;">
                            Billed Operator: ${inv.generated_by}<br>
                            Ref PO: ${inv.po_number}
                        </div>
                    </div>
                    <div class="invoice-bill-col" style="text-align: right;">
                        <span style="font-size:10px; font-weight:700; color:#9ca3af; letter-spacing:0.5px; text-transform:uppercase;">Supplier Source:</span>
                        <div style="font-weight:700; margin-top:5px; font-size:15px;">${inv.supplier_name}</div>
                        <div style="font-size:12px; color:#555; margin-top:2px; line-height:1.4;">
                            ${inv.supplier_address || ''}<br>
                            Phone: ${inv.supplier_phone || 'N/A'}<br>
                            Email: ${inv.supplier_email || 'N/A'}
                        </div>
                    </div>
                </div>

                <table class="invoice-table">
                    <thead>
                        <tr>
                            <th style="width:8%;">#</th>
                            <th style="width:47%;">Item Specification</th>
                            <th align="center" style="width:15%;">Billed Qty</th>
                            <th align="right" style="width:15%;">Rate</th>
                            <th align="right" style="width:15%;">Line Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rowsHtml}
                    </tbody>
                </table>

                <div class="invoice-totals">
                    <table class="invoice-totals-table">
                        <tr>
                            <td style="color:#666;">Subtotal:</td>
                            <td align="right" style="font-weight:600;">₹${inv.total_amount.toFixed(2)}</td>
                        </tr>
                        <tr>
                            <td style="color:#666;">Tax (GST 0% / Project Exempt):</td>
                            <td align="right" style="font-weight:600;">₹0.00</td>
                        </tr>
                        <tr style="border-top: 1.5px solid #2563eb; font-size:16px; font-weight:700; color:#111827;">
                            <td style="padding-top:12px;">Total Due:</td>
                            <td align="right" style="padding-top:12px; color:#2563eb;">₹${inv.total_amount.toFixed(2)}</td>
                        </tr>
                    </table>
                </div>

                <div style="margin-top:50px; font-size:12px; color:#666; border-top:1px solid #e5e7eb; padding-top:15px; font-style:italic;">
                    <strong>Operator Notes:</strong> ${inv.notes || 'Billed against full procurement receipt.'}<br><br>
                    <div style="text-align: center; margin-top: 10px; font-weight:600; color:#999; font-size:10px;">This is a computer generated major project billing receipt. No signature required.</div>
                </div>
            </div>
        `;

    } catch (e) {
        Swal.fire("Error", e.message, "error");
    }
}

// ── ACTION: CANCEL INVOICE ───────────────────────────────────
function cancelInvoiceAction(invoiceId) {
    Swal.fire({
        title: 'Cancel Financial Invoice?',
        text: "This will void the invoice and mark its status as Cancelled. This cannot be undone.",
        input: 'text',
        inputLabel: 'Reason for Voiding',
        inputPlaceholder: 'Enter brief reason...',
        inputAttributes: { required: 'true' },
        showCancelButton: true,
        confirmButtonColor: '#ef4444',
        confirmButtonText: 'Void Invoice',
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
                title: 'Voiding statement...',
                allowOutsideClick: false,
                didOpen: () => { Swal.showLoading(); }
            });

            try {
                await apiFetch(`/api/invoices/${invoiceId}/cancel`, {
                    method: 'PUT',
                    body: { reason: result.value }
                });

                Swal.fire("Cancelled", "Invoice statement voided.", "success").then(() => {
                    navigate("invoices");
                });
            } catch (e) {
                Swal.fire("Failure", e.message, "error");
            }
        }
    });
}
