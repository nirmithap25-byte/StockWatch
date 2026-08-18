// Frontend/js/panels/users_panel.js

async function renderUsersPanel(container) {
    if (currentUser.role !== 'Admin') {
        container.innerHTML = `<p style="padding:20px; color:red;">Access Denied. Admin privileges required.</p>`;
        return;
    }

    container.innerHTML = `
        <div class="panel-header-section">
            <h2>User Management Directory</h2>
            <button class="btn-primary" onclick="openRegisterUserModal()">
                <span class="material-symbols-outlined">person_add</span>
                Register New User
            </button>
        </div>

        <div class="table-card">
            <div class="table-header">
                <span class="table-title">System Users & Roles Access</span>
            </div>
            <div class="table-wrapper">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>User ID</th>
                            <th>Full Name</th>
                            <th>Email Address</th>
                            <th>Phone</th>
                            <th>Access Role</th>
                            <th>Department</th>
                            <th>Account Status</th>
                            <th>Date Created</th>
                            <th align="center">Actions</th>
                        </tr>
                    </thead>
                    <tbody id="users-tbody">
                        <tr><td colspan="9" align="center" style="color:var(--text-secondary);">Loading system directory...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    `;

    loadUsersDirectory();
}

let usersDirectoryList = [];

async function loadUsersDirectory() {
    try {
        const res = await apiFetch("/api/auth/users");
        const tbody = document.getElementById("users-tbody");
        if (tbody && res.users) {
            usersDirectoryList = res.users;
            renderUsersTableRows(usersDirectoryList);
        }
    } catch (e) {
        console.error("Failed to load user directory:", e);
        const tbody = document.getElementById("users-tbody");
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="9" align="center" style="color:var(--color-danger);">Error: ${e.message}</td></tr>`;
        }
    }
}

function renderUsersTableRows(users) {
    const tbody = document.getElementById("users-tbody");
    if (!tbody) return;

    if (users.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" align="center" style="color:var(--text-secondary);">No system users registered.</td></tr>`;
        return;
    }

    tbody.innerHTML = "";
    users.forEach(user => {
        const tr = document.createElement("tr");

        let statusClass = "badge received"; // Green Active
        if (user.status === 'Inactive') statusClass = "badge cancelled"; // Red Inactive

        tr.innerHTML = `
            <td style="font-family:monospace; font-weight:700;">USR-${user.user_id}</td>
            <td><strong>${user.full_name}</strong></td>
            <td>${user.email}</td>
            <td>${user.phone || 'N/A'}</td>
            <td>
                <span class="badge" style="background:rgba(255,255,255,0.05); color:var(--text-primary); font-weight:600;">
                    ${user.role}
                </span>
            </td>
            <td>${user.department_name || 'All'}</td>
            <td><span class="${statusClass}">${user.status}</span></td>
            <td style="color:var(--text-secondary); font-size:11px;">${new Date(user.created_at).toLocaleDateString()}</td>
            <td>
                <div class="action-btns" style="justify-content:center;">
                    <button class="btn-icon edit" title="Edit User" onclick="openEditUserModal(${user.user_id})">
                        <span class="material-symbols-outlined">manage_accounts</span>
                    </button>
                    <button class="btn-icon delete" title="Toggle Access" onclick="toggleUserStatusAction(${user.user_id})">
                        <span class="material-symbols-outlined">swap_calls</span>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// ── REGISTER NEW USER MODAL ──────────────────────────────────
async function openRegisterUserModal() {
    const bodyHtml = `
        <form id="user-register-form">
            <div class="form-group">
                <label>Full Name *</label>
                <input type="text" id="reg-full-name" placeholder="Ravi Shankar" required>
            </div>
            <div class="form-group">
                <label>Email Address *</label>
                <input type="email" id="reg-email" placeholder="shankar@stockwatch.com" required>
            </div>
            <div class="form-group">
                <label>Password *</label>
                <input type="password" id="reg-password" placeholder="Enter secure password" required>
            </div>
            <div class="form-group">
                <label>Phone Number</label>
                <input type="text" id="reg-phone" placeholder="9000012345">
            </div>
            <div class="form-group">
                <label>Access Role *</label>
                <select id="reg-role" required>
                    <option value="Admin">Admin (Full Control)</option>
                    <option value="Inventory Manager">Inventory Manager (Stock & POs)</option>
                    <option value="Department Head">Department Head (Requests)</option>
                    <option value="Auditor">Auditor (Read-Only Logs & ML)</option>
                </select>
            </div>
            <div class="form-group">
                <label>Associated Department</label>
                <select id="reg-department-id">
                    <option value="">-- All Departments / Global --</option>
                </select>
            </div>
        </form>
    `;

    showModal("Register New System Account", bodyHtml, "Create User", async () => {
        const full_name = document.getElementById("reg-full-name").value.trim();
        const email = document.getElementById("reg-email").value.trim();
        const password = document.getElementById("reg-password").value.trim();
        const phone = document.getElementById("reg-phone").value.trim();
        const role = document.getElementById("reg-role").value;
        const deptVal = document.getElementById("reg-department-id").value;
        const department_id = deptVal ? parseInt(deptVal) : null;

        if (!full_name || !email || !password || !role) {
            Swal.fire("Validation Error", "Please fill in all required fields", "error");
            return;
        }

        try {
            await apiFetch("/api/auth/register", {
                method: "POST",
                body: { full_name, email, password, phone, role, department_id }
            });

            closeModal();
            Swal.fire("Success", "New operator registered successfully!", "success").then(() => {
                loadUsersDirectory();
            });

        } catch (e) {
            Swal.fire("Registration Failed", e.message, "error");
        }
    });

    loadDepartmentsDropdown("reg-department-id");
}

// ── EDIT USER MODAL ──────────────────────────────────────────
async function openEditUserModal(userId) {
    const user = usersDirectoryList.find(u => u.user_id === userId);
    if (!user) return;

    const bodyHtml = `
        <form id="user-edit-form">
            <div class="form-group">
                <label>Full Name (Read-Only)</label>
                <input type="text" value="${user.full_name}" disabled style="background:rgba(255,255,255,0.05); cursor:not-allowed;">
            </div>
            <div class="form-group">
                <label>Email Address (Read-Only)</label>
                <input type="text" value="${user.email}" disabled style="background:rgba(255,255,255,0.05); cursor:not-allowed;">
            </div>
            <div class="form-group">
                <label>Phone Number</label>
                <input type="text" id="edit-phone" value="${user.phone || ''}">
            </div>
            <div class="form-group">
                <label>Access Role *</label>
                <select id="edit-role" required>
                    <option value="Admin" ${user.role === 'Admin' ? 'selected' : ''}>Admin</option>
                    <option value="Inventory Manager" ${user.role === 'Inventory Manager' ? 'selected' : ''}>Inventory Manager</option>
                    <option value="Department Head" ${user.role === 'Department Head' ? 'selected' : ''}>Department Head</option>
                    <option value="Auditor" ${user.role === 'Auditor' ? 'selected' : ''}>Auditor</option>
                </select>
            </div>
        </form>
    `;

    showModal(`Edit User: ${user.full_name}`, bodyHtml, "Save Changes", async () => {
        const phone = document.getElementById("edit-phone").value.trim();
        const role = document.getElementById("edit-role").value;

        if (!role) {
            Swal.fire("Validation Error", "Role is required", "error");
            return;
        }

        try {
            await apiFetch(`/api/auth/users/${userId}`, {
                method: "PUT",
                body: { phone, role }
            });

            closeModal();
            Swal.fire("Success", "User details updated successfully!", "success").then(() => {
                loadUsersDirectory();
            });

        } catch (e) {
            Swal.fire("Failure", e.message, "error");
        }
    });
}

// ── TOGGLE STATUS ACTION ─────────────────────────────────────
function toggleUserStatusAction(userId) {
    const user = usersDirectoryList.find(u => u.user_id === userId);
    if (!user) return;

    if (user.user_id === currentUser.user_id) {
        Swal.fire("Action Blocked", "You cannot deactivate or lock your own admin account.", "warning");
        return;
    }

    const newStatus = user.status === 'Active' ? 'Inactive' : 'Active';

    Swal.fire({
        title: `${newStatus === 'Active' ? 'Activate' : 'Block'} Account?`,
        text: `Change account status for "${user.full_name}" to ${newStatus}?`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: newStatus === 'Active' ? '#10b981' : '#ef4444',
        cancelButtonColor: '#374151',
        confirmButtonText: `Toggle Status`
    }).then(async (result) => {
        if (result.isConfirmed) {
            try {
                await apiFetch(`/api/auth/users/${userId}`, {
                    method: 'PUT',
                    body: { status: newStatus }
                });

                Swal.fire("Status Updated", `User is now ${newStatus}.`, "success").then(() => {
                    loadUsersDirectory();
                });
            } catch (e) {
                Swal.fire("Failed to update status", e.message, "error");
            }
        }
    });
}
