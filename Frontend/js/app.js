// Frontend/js/app.js

const API_BASE = "http://127.0.0.1:5000";

let currentUser = null;

document.addEventListener("DOMContentLoaded", () => {
    // 1. Verify Authentication
    const token = localStorage.getItem("stockwatch_token");
    const userStr = localStorage.getItem("stockwatch_user");

    if (!token || !userStr) {
        handleLogout();
        return;
    }

    currentUser = JSON.parse(userStr);

    // 2. Set Profile Details in Sidebar
    const avatarEl = document.getElementById("user-avatar");
    const nameEl = document.getElementById("user-name");
    const roleEl = document.getElementById("user-role");

    if (nameEl) nameEl.innerText = currentUser.full_name;
    if (roleEl) roleEl.innerText = currentUser.role;
    if (avatarEl) {
        const initials = currentUser.full_name
            .split(" ")
            .map(n => n[0])
            .join("")
            .substring(0, 2)
            .toUpperCase();
        avatarEl.innerText = initials;
    }

    // 3. Admin user directory access
    const adminMenu = document.getElementById("admin-users-menu");
    if (adminMenu && currentUser.role === "Admin") {
        adminMenu.style.display = "block";
    }

    // 4. Initial Navigation
    navigate("dashboard");

    // 5. Initial Alert Check & Interval
    updateAlertBadge();
    setInterval(updateAlertBadge, 15000);
});

// ── NAVIGATION ROUTER ────────────────────────────────────────
function navigate(panelName) {
    // Reset active sidebar item styling
    const menuLinks = document.querySelectorAll(".sidebar-menu .menu-link");
    menuLinks.forEach(link => {
        link.classList.remove("active");
        // Simple string comparison for active state
        if (link.outerHTML.includes(`navigate('${panelName}')`)) {
            link.classList.add("active");
        }
    });

    const panelTitle = document.getElementById("navbar-title");
    const contentEl = document.getElementById("panel-content");

    if (panelTitle) {
        panelTitle.innerText = panelName.replace("-", " ").toUpperCase();
    }

    if (contentEl) {
        contentEl.innerHTML = `<div class="loader-spinner"></div>`;
    }

    // Run panel renderer
    try {
        switch (panelName) {
            case "dashboard":
                renderDashboardPanel(contentEl);
                break;
            case "inventory":
                renderInventoryPanel(contentEl);
                break;
            case "stock":
                renderStockPanel(contentEl);
                break;
            case "purchase":
                renderPurchasePanel(contentEl);
                break;
            case "approvals":
                renderApprovalsPanel(contentEl);
                break;
            case "alerts":
                renderAlertsPanel(contentEl);
                break;
            case "invoices":
                renderInvoicesPanel(contentEl);
                break;
            case "anomaly":
                renderAnomalyPanel(contentEl);
                break;
            case "audit":
                renderAuditPanel(contentEl);
                break;
            case "users":
                renderUsersPanel(contentEl);
                break;
            default:
                contentEl.innerHTML = `<p style="padding:20px; color:red;">Panel "${panelName}" not found.</p>`;
        }
    } catch (e) {
        console.error(e);
        contentEl.innerHTML = `<p style="padding:20px; color:red;">Error loading panel: ${e.message}</p>`;
    }
}

// ── SIDEBAR TOGGLE ───────────────────────────────────────────
function toggleSidebar() {
    const sidebar = document.getElementById("app-sidebar");
    if (sidebar) {
        sidebar.classList.toggle("collapsed");
    }
}

// ── UNIFIED AUTHORIZED FETCH ─────────────────────────────────
async function apiFetch(endpoint, options = {}) {
    const token = localStorage.getItem("stockwatch_token");
    if (!token) {
        handleLogout();
        return;
    }

    const headers = {
        "Authorization": `Bearer ${token}`,
        ...options.headers
    };

    if (options.body && !(options.body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
        if (typeof options.body === "object") {
            options.body = JSON.stringify(options.body);
        }
    }

    const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint}`;

    try {
        const response = await fetch(url, { ...options, headers });
        const data = await response.json();

        if (response.status === 401 || response.status === 403) {
            // Token expired or unauthorized
            Swal.fire({
                icon: 'error',
                title: 'Session Expired',
                text: data.error || 'Please log in again.',
                confirmButtonColor: '#3b82f6'
            }).then(() => {
                handleLogout();
            });
            throw new Error("Session expired");
        }

        if (!response.ok) {
            throw new Error(data.message || data.error || "Request failed");
        }

        return data;

    } catch (error) {
        console.error(`API Error on ${endpoint}:`, error);
        throw error;
    }
}

// ── ALERT BADGE UTILITY ──────────────────────────────────────
async function updateAlertBadge() {
    try {
        const res = await apiFetch("/api/alerts/summary");
        const badge = document.getElementById("header-alert-badge");
        if (badge && res.success && res.summary) {
            const count = res.summary.total_unread;
            if (count > 0) {
                badge.innerText = count > 99 ? "99+" : count;
                badge.style.display = "flex";
            } else {
                badge.style.display = "none";
            }
        }
    } catch (e) {
        console.warn("Failed to check alerts:", e.message);
    }
}

// ── COMMON SYSTEM MODAL ──────────────────────────────────────
let modalSubmitCallback = null;

function showModal(title, bodyHtml, submitText = "Submit", onSubmit = null) {
    const modal = document.getElementById("app-modal");
    const titleEl = document.getElementById("modal-title");
    const bodyEl = document.getElementById("modal-body");
    const submitBtn = document.getElementById("modal-submit-btn");

    if (!modal) return;

    titleEl.innerText = title;
    bodyEl.innerHTML = bodyHtml;
    submitBtn.innerText = submitText;
    
    if (onSubmit) {
        submitBtn.style.display = "inline-block";
        modalSubmitCallback = onSubmit;
    } else {
        submitBtn.style.display = "none";
        modalSubmitCallback = null;
    }

    modal.classList.add("active");
}

function closeModal() {
    const modal = document.getElementById("app-modal");
    if (modal) {
        modal.classList.remove("active");
    }
    modalSubmitCallback = null;
}

// Bind modal submit button click
document.addEventListener("DOMContentLoaded", () => {
    const submitBtn = document.getElementById("modal-submit-btn");
    if (submitBtn) {
        submitBtn.addEventListener("click", async () => {
            if (modalSubmitCallback) {
                submitBtn.disabled = true;
                const oldText = submitBtn.innerText;
                submitBtn.innerText = "Processing...";
                try {
                    await modalSubmitCallback();
                } catch (e) {
                    console.error("Modal Submit Error:", e);
                } finally {
                    submitBtn.disabled = false;
                    submitBtn.innerText = oldText;
                }
            }
        });
    }
});

// ── LOGOUT UTILITY ───────────────────────────────────────────
function handleLogout() {
    localStorage.removeItem("stockwatch_token");
    localStorage.removeItem("stockwatch_user");
    window.location.href = "index.html";
}

// ── HELPER DATA DROPDOWN LOADERS ──────────────────────────────
async function loadCategoriesDropdown(selectId, selectedId = null) {
    try {
        const res = await apiFetch("/api/inventory/categories");
        const select = document.getElementById(selectId);
        if (select && res.success) {
            select.innerHTML = '<option value="">-- Select Category --</option>';
            res.data.forEach(cat => {
                const opt = document.createElement("option");
                opt.value = cat.category_id;
                opt.innerText = cat.category_name;
                if (selectedId && String(cat.category_id) === String(selectedId)) {
                    opt.selected = true;
                }
                select.appendChild(opt);
            });
        }
    } catch (e) {
        console.error("Failed to load categories dropdown:", e);
    }
}

async function loadSuppliersDropdown(selectId, selectedId = null) {
    try {
        const res = await apiFetch("/api/inventory/suppliers");
        const select = document.getElementById(selectId);
        if (select && res.success) {
            select.innerHTML = '<option value="">-- Select Supplier --</option>';
            res.data.forEach(sup => {
                const opt = document.createElement("option");
                opt.value = sup.supplier_id;
                opt.innerText = sup.supplier_name;
                if (selectedId && String(sup.supplier_id) === String(selectedId)) {
                    opt.selected = true;
                }
                select.appendChild(opt);
            });
        }
    } catch (e) {
        console.error("Failed to load suppliers dropdown:", e);
    }
}

async function loadDepartmentsDropdown(selectId, selectedId = null) {
    try {
        const res = await apiFetch("/api/inventory/departments");
        const select = document.getElementById(selectId);
        if (select && res.success) {
            select.innerHTML = '<option value="">-- Select Department --</option>';
            res.data.forEach(dept => {
                const opt = document.createElement("option");
                opt.value = dept.department_id;
                opt.innerText = dept.department_name;
                if (selectedId && String(dept.department_id) === String(selectedId)) {
                    opt.selected = true;
                }
                select.appendChild(opt);
            });
        }
    } catch (e) {
        console.error("Failed to load departments dropdown:", e);
    }
}
