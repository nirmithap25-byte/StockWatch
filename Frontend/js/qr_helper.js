// Frontend/js/qr_helper.js

let html5QrcodeScanner = null;

function openQrScanModal() {
    // Create element for scanner body inside SweetAlert
    const scannerHtml = `
        <div style="width: 100%; max-width: 350px; margin: 0 auto;">
            <div id="reader" style="width: 100%; background: #000; border-radius: 8px; overflow:hidden;"></div>
            <p style="margin-top: 10px; font-size: 13px; color: #666;">Align the QR code inside the frame to scan.</p>
        </div>
    `;

    Swal.fire({
        title: 'Scan Item QR Code',
        html: scannerHtml,
        showCancelButton: true,
        cancelButtonText: 'Close Camera',
        showConfirmButton: false,
        allowOutsideClick: false,
        didOpen: () => {
            // Initialize html5-qrcode
            html5QrcodeScanner = new Html5Qrcode("reader");
            const config = { fps: 10, qrbox: { width: 220, height: 220 } };

            html5QrcodeScanner.start(
                { facingMode: "environment" }, 
                config, 
                onScanSuccess,
                onScanFailure
            ).catch(err => {
                console.error("Camera start error:", err);
                Swal.showValidationMessage(`Camera access error: ${err}`);
            });
        },
        willClose: () => {
            stopScanner();
        }
    });
}

async function stopScanner() {
    if (html5QrcodeScanner && html5QrcodeScanner.isScanning) {
        try {
            await html5QrcodeScanner.stop();
            console.log("Scanner stopped.");
        } catch (err) {
            console.error("Failed to stop scanner:", err);
        }
    }
}

async function onScanSuccess(decodedText, decodedResult) {
    await stopScanner();
    Swal.close();

    Swal.fire({
        title: 'Fetching details...',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });

    try {
        const res = await apiFetch(`/api/qr/scan/${decodedText}`);
        if (!res.success || !res.item) {
            throw new Error(res.message || "Failed to parse item");
        }

        const item = res.item;
        
        // Show item details and ask for action
        showQrActionModal(item);

    } catch (e) {
        Swal.fire({
            icon: 'error',
            title: 'Scan Failed',
            text: e.message || 'Invalid QR code or inactive item.',
            confirmButtonColor: '#3b82f6'
        });
    }
}

function onScanFailure(error) {
    // Silently ignore scan failure logs to avoid spam
}

function showQrActionModal(item) {
    const actionHtml = `
        <div style="text-align: left; font-size: 14px;">
            <p style="margin-bottom: 8px;"><strong>Code:</strong> ${item.item_code}</p>
            <p style="margin-bottom: 8px;"><strong>Name:</strong> ${item.item_name}</p>
            <p style="margin-bottom: 8px;"><strong>Current Stock:</strong> ${item.quantity} ${item.unit} (<span class="badge ${item.stock_status.toLowerCase()}">${item.stock_status}</span>)</p>
            <p style="margin-bottom: 15px;"><strong>Supplier:</strong> ${item.supplier_name}</p>
            
            <hr style="border-color: #eee; margin-bottom: 15px;">

            <div class="form-group" style="margin-bottom: 12px;">
                <label style="color:#666; font-weight:600;">Transaction Type</label>
                <select id="qr-action-type" style="width:100%; padding:10px; border-radius:6px; border:1px solid #ccc; font-size:14px; background:#fff; color:#333;">
                    <option value="IN">Stock IN (+)</option>
                    <option value="OUT" ${item.quantity === 0 ? 'disabled' : ''}>Stock OUT (-)</option>
                </select>
            </div>
            
            <div class="form-group" style="margin-bottom: 12px;">
                <label style="color:#666; font-weight:600;">Quantity</label>
                <input type="number" id="qr-action-qty" min="1" max="${item.quantity}" value="1" style="width:100%; padding:10px; border-radius:6px; border:1px solid #ccc; font-size:14px; background:#fff; color:#333;">
            </div>

            <div class="form-group" style="margin-bottom: 12px;">
                <label style="color:#666; font-weight:600;">Reason / Remark</label>
                <input type="text" id="qr-action-reason" placeholder="e.g. Scanned receipt / Issue to lab" style="width:100%; padding:10px; border-radius:6px; border:1px solid #ccc; font-size:14px; background:#fff; color:#333;">
            </div>
        </div>
    `;

    Swal.fire({
        title: 'QR Code Quick Transaction',
        html: actionHtml,
        showCancelButton: true,
        confirmButtonText: 'Confirm Transaction',
        confirmButtonColor: '#3b82f6',
        cancelButtonText: 'Cancel',
        preConfirm: () => {
            const action = document.getElementById("qr-action-type").value;
            const qty = parseInt(document.getElementById("qr-action-qty").value);
            const reason = document.getElementById("qr-action-reason").value.trim();

            if (isNaN(qty) || qty <= 0) {
                Swal.showValidationMessage('Quantity must be greater than 0');
                return false;
            }
            if (action === 'OUT' && qty > item.quantity) {
                Swal.showValidationMessage(`Insufficient stock. Max available: ${item.quantity}`);
                return false;
            }
            if (!reason) {
                Swal.showValidationMessage('Reason is required');
                return false;
            }

            return { action, qty, reason };
        }
    }).then(async (result) => {
        if (result.isConfirmed) {
            Swal.fire({
                title: 'Processing...',
                allowOutsideClick: false,
                didOpen: () => { Swal.showLoading(); }
            });

            try {
                const endpoint = result.value.action === 'IN' ? '/api/qr/stock-in' : '/api/qr/stock-out';
                const res = await apiFetch(endpoint, {
                    method: 'POST',
                    body: {
                        qr_code: item.qr_code,
                        quantity: result.value.qty,
                        user_id: currentUser.user_id,
                        reason: result.value.reason
                    }
                });

                Swal.fire({
                    icon: 'success',
                    title: 'Stock Updated',
                    text: res.message,
                    confirmButtonColor: '#3b82f6'
                }).then(() => {
                    // Reload active view to sync details
                    const activeMenu = document.querySelector(".sidebar-menu .menu-link.active");
                    if (activeMenu) {
                        const onclickStr = activeMenu.getAttribute("onclick");
                        const match = onclickStr.match(/'([^']+)'/);
                        if (match && match[1]) {
                            navigate(match[1]);
                        }
                    }
                    updateAlertBadge();
                });

            } catch (err) {
                Swal.fire({
                    icon: 'error',
                    title: 'Transaction Failed',
                    text: err.message,
                    confirmButtonColor: '#ef4444'
                });
            }
        }
    });

    // Auto-update max quantity validation dynamically
    const typeSelect = document.getElementById("qr-action-type");
    if (typeSelect) {
        typeSelect.addEventListener("change", () => {
            const qtyInput = document.getElementById("qr-action-qty");
            if (typeSelect.value === 'OUT') {
                qtyInput.setAttribute("max", item.quantity);
            } else {
                qtyInput.removeAttribute("max");
            }
        });
    }
}

// Helper to trigger QR image file download
function downloadItemQr(qrCode, itemName) {
    const url = `${API_BASE}/api/qr/generate/${qrCode}`;
    const a = document.createElement("a");
    a.href = url;
    a.download = `${itemName.replace(/\s+/g, '_')}_QR.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}
