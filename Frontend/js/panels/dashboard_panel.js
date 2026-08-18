// Frontend/js/panels/dashboard_panel.js

async function renderDashboardPanel(container) {
    container.innerHTML = `
        <div class="panel-header-section">
            <h2>System Overview</h2>
            <button class="btn-primary" onclick="navigate('inventory')">
                <span class="material-symbols-outlined">inventory_2</span>
                Manage Inventory
            </button>
        </div>

        <!-- ── STATS CARDS ──────────────────────────────────────── -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-info">
                    <h3>Active Items</h3>
                    <div class="stat-value" id="stat-total-items">-</div>
                </div>
                <div class="stat-icon-wrapper blue">
                    <span class="material-symbols-outlined">inventory</span>
                </div>
            </div>
            
            <div class="stat-card">
                <div class="stat-info">
                    <h3>Total Value</h3>
                    <div class="stat-value" id="stat-total-value">₹0.00</div>
                </div>
                <div class="stat-icon-wrapper teal">
                    <span class="material-symbols-outlined">payments</span>
                </div>
            </div>

            <div class="stat-card" style="cursor:pointer;" onclick="navigate('alerts')">
                <div class="stat-info">
                    <h3>Low Stock Warning</h3>
                    <div class="stat-value" id="stat-low-stock" style="color:var(--color-danger);">-</div>
                </div>
                <div class="stat-icon-wrapper red">
                    <span class="material-symbols-outlined">warning</span>
                </div>
            </div>

            <div class="stat-card" style="cursor:pointer;" onclick="navigate('purchase')">
                <div class="stat-info">
                    <h3>Pending Orders</h3>
                    <div class="stat-value" id="stat-pending-pos">-</div>
                </div>
                <div class="stat-icon-wrapper yellow">
                    <span class="material-symbols-outlined">shopping_cart</span>
                </div>
            </div>

            <div class="stat-card" style="cursor:pointer;" onclick="navigate('approvals')">
                <div class="stat-info">
                    <h3>Pending Requests</h3>
                    <div class="stat-value" id="stat-pending-approvals">-</div>
                </div>
                <div class="stat-icon-wrapper indigo">
                    <span class="material-symbols-outlined">rule</span>
                </div>
            </div>
        </div>

        <!-- ── CHARTS SECTION ───────────────────────────────────── -->
        <div class="charts-grid">
            <div class="chart-card">
                <div class="chart-header">
                    <span class="chart-title">Popular Items Movements</span>
                </div>
                <div class="chart-body" style="height: 300px;">
                    <canvas id="topItemsChart"></canvas>
                </div>
            </div>

            <div class="chart-card">
                <div class="chart-header">
                    <span class="chart-title">Movement Breakdown</span>
                </div>
                <div class="chart-body" style="height: 300px; display: flex; justify-content: center; align-items: center;">
                    <canvas id="movementStatsChart"></canvas>
                </div>
            </div>
        </div>

        <!-- ── LOWER SPLIT ──────────────────────────────────────── -->
        <div class="charts-grid" style="grid-template-columns: 1fr 1fr;">
            <!-- Recent Movements Log -->
            <div class="table-card">
                <div class="table-header">
                    <span class="table-title">Recent Movements Log</span>
                    <button class="btn-secondary" onclick="navigate('stock')" style="padding: 6px 12px; font-size: 11px;">View All</button>
                </div>
                <div class="table-wrapper" style="max-height: 350px; overflow-y:auto;">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Item</th>
                                <th>Type</th>
                                <th>Quantity</th>
                                <th>By</th>
                                <th>Date</th>
                            </tr>
                        </thead>
                        <tbody id="dashboard-movements-tbody">
                            <tr><td colspan="5" align="center" style="color:var(--text-secondary);">Loading...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Critical Low Stock Alert Table -->
            <div class="table-card">
                <div class="table-header">
                    <span class="table-title" style="color:var(--color-danger);">Critical Low Stock Items</span>
                    <button class="btn-secondary" onclick="navigate('alerts')" style="padding: 6px 12px; font-size: 11px;">Manage Alerts</button>
                </div>
                <div class="table-wrapper" style="max-height: 350px; overflow-y:auto;">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Code</th>
                                <th>Item Name</th>
                                <th>Department</th>
                                <th>Stock</th>
                                <th>Min Level</th>
                            </tr>
                        </thead>
                        <tbody id="dashboard-low-stock-tbody">
                            <tr><td colspan="5" align="center" style="color:var(--text-secondary);">Loading...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;

    // Fetch and populate metrics & charts
    try {
        const summaryData = await apiFetch("/api/dashboard/summary");
        if (summaryData.success && summaryData.summary) {
            const s = summaryData.summary;
            document.getElementById("stat-total-items").innerText = s.total_items;
            document.getElementById("stat-total-value").innerText = new Intl.NumberFormat('en-IN', {
                style: 'currency',
                currency: 'INR'
            }).format(s.total_stock_value);
            document.getElementById("stat-low-stock").innerText = s.low_stock_count;
            document.getElementById("stat-pending-pos").innerText = s.pending_po_count;
            document.getElementById("stat-pending-approvals").innerText = s.pending_approvals;
        }

        // Render charts
        renderTopItemsChart();
        renderMovementStatsChart();

        // Load logs
        loadDashboardLogs();
        loadDashboardLowStock();

    } catch (e) {
        console.error("Dashboard error:", e);
    }
}

async function renderTopItemsChart() {
    try {
        const res = await apiFetch("/api/dashboard/top-items");
        const ctx = document.getElementById("topItemsChart").getContext('2d');
        
        if (!res.success || !res.top_items || res.top_items.length === 0) {
            ctx.fillText("No movement data available.", 50, 50);
            return;
        }

        const labels = res.top_items.map(item => item.item_name);
        const totals = res.top_items.map(item => item.total_moved);

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Units Transacted',
                    data: totals,
                    backgroundColor: 'rgba(59, 130, 246, 0.6)',
                    borderColor: '#3b82f6',
                    borderWidth: 1.5,
                    borderRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(0,0,0,0.05)' },
                        ticks: { color: '#475569' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#475569' }
                    }
                }
            }
        });

    } catch (e) {
        console.error("Failed to load Top Items Chart:", e);
    }
}

async function renderMovementStatsChart() {
    try {
        const res = await apiFetch("/api/dashboard/movement-stats");
        const ctx = document.getElementById("movementStatsChart").getContext('2d');

        if (!res.success || !res.movement_stats || res.movement_stats.length === 0) {
            ctx.fillText("No transactions.", 50, 50);
            return;
        }

        const labels = res.movement_stats.map(item => item.movement_type);
        const data = res.movement_stats.map(item => item.total_count);

        const colors = {
            'IN': '#10b981',        // Success emerald
            'OUT': '#ef4444',       // Danger red
            'TRANSFER': '#4f46e5',  // Indigo accent
            'ADJUSTMENT': '#ea580c' // Orange accent
        };

        const bgColors = labels.map(label => colors[label] || '#9ca3af');

        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: bgColors,
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: '#475569',
                            boxWidth: 12,
                            font: { family: 'Inter', size: 12, weight: '500' }
                        }
                    }
                }
            }
        });

    } catch (e) {
        console.error("Failed to load Movement Stats Chart:", e);
    }
}

async function loadDashboardLogs() {
    try {
        const res = await apiFetch("/api/dashboard/recent-movements");
        const tbody = document.getElementById("dashboard-movements-tbody");
        if (tbody && res.success) {
            if (res.recent_movements.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" align="center" style="color:var(--text-secondary);">No movements recorded</td></tr>`;
                return;
            }

            tbody.innerHTML = "";
            res.recent_movements.forEach(log => {
                const tr = document.createElement("tr");
                
                let typeColor = "badge pending";
                if (log.movement_type === 'IN') typeColor = 'badge received';
                if (log.movement_type === 'OUT') typeColor = 'badge cancelled';
                if (log.movement_type === 'TRANSFER') typeColor = 'badge approved';
                if (log.movement_type === 'ADJUSTMENT') typeColor = 'badge ordered';

                tr.innerHTML = `
                    <td><strong>${log.item_name}</strong></td>
                    <td><span class="${typeColor}">${log.movement_type}</span></td>
                    <td>${log.quantity}</td>
                    <td>${log.performed_by}</td>
                    <td style="color:var(--text-secondary); font-size:11px;">${new Date(log.movement_date).toLocaleString()}</td>
                `;
                tbody.appendChild(tr);
            });
        }
    } catch (e) {
        console.error("Failed to load dashboard logs:", e);
    }
}

async function loadDashboardLowStock() {
    try {
        const res = await apiFetch("/api/dashboard/low-stock");
        const tbody = document.getElementById("dashboard-low-stock-tbody");
        if (tbody && res.success) {
            if (res.low_stock_items.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" align="center" style="color:var(--color-success);">All items are well stocked!</td></tr>`;
                return;
            }

            tbody.innerHTML = "";
            res.low_stock_items.slice(0, 8).forEach(item => {
                const tr = document.createElement("tr");
                const stockBadge = item.quantity === 0 ? 'badge out-of-stock' : 'badge critical';
                tr.innerHTML = `
                    <td style="font-family:monospace; font-weight:600;">${item.item_code}</td>
                    <td><strong>${item.item_name}</strong></td>
                    <td>${item.department_name}</td>
                    <td><span class="${stockBadge}">${item.quantity}</span></td>
                    <td style="font-weight:600; color:var(--text-secondary);">${item.minimum_stock}</td>
                `;
                tbody.appendChild(tr);
            });
        }
    } catch (e) {
        console.error("Failed to load low stock:", e);
    }
}
