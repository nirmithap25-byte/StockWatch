# 📁 StockWatch: Project Structure & File Guide

Use this guide to explain the files, folders, and code organization of your project to the examiner during your presentation.

---

## 🏛️ High-Level Project Overview
The project is built using a clean **client-server (3-tier) architecture**:
1. **Frontend (Presentation Layer):** Single-page web dashboard using HTML, CSS, and Vanilla JS.
2. **Backend (Application Layer):** Python Flask REST API performing database operations and running Machine Learning algorithms.
3. **Database (Data Layer):** MySQL (MariaDB) database schema managing relational tables, triggers, and views.

---

## 📂 Folder-by-Folder Details

### 1. 🌐 The `Frontend` Folder
*This folder contains all files related to what the user sees in the browser:*

* **`index.html`**: The HTML file for the login screen. It loads the customized styling, Google Fonts, and `auth.js`.
* **`dashboard.html`**: The master container page. It contains the sidebar menu, header navigation, and a dynamic container div where different panels (Dashboard, Inventory, Audit Logs) load.
* **`login_background.jpg`**: The full-screen background image showing the modern warehouse layout.
* 📂 **`css/`** (Styling Sheets)
  * `login.css`: Contains CSS rules, keyframes, transitions, and radial glow effects for the login screen.
  * `style.css`: Contains the **Premium Light Mode CSS theme variables**, layouts, table grids, buttons, and status badge colors.
* 📂 **`js/`** (Frontend Scripts)
  * `app.js`: The central routing script. It checks if the user is authenticated (using JWT tokens), handles sidebar menu clicks, and switches between panels dynamically.
  * `auth.js`: Captures email and password inputs, sends a POST request to the Flask server, and saves the login session to browser memory (`localStorage`).
  * `qr_helper.js`: Code helper that opens the webcam to scan QR codes and handles scanning logic.
  * 📂 **`panels/`** (Individual Page Scripts)
    * *These scripts contain the HTML structures and fetch requests for each specific page:*
    * `dashboard_panel.js`: Fetches summary stats and draws the two Chart.js graphs.
    * `inventory_panel.js`: Displays the catalog table, item search, and handles adding/editing products.
    * `stock_panel.js`: Renders the manual **Record Stock Transaction** form and the list of stock movements.
    * `purchase_panel.js`: Renders purchase order templates sent to suppliers.
    * `approvals_panel.js`: Displays stock requests waiting for manager verification.
    * `alerts_panel.js`: Renders notifications for low stock levels and anomalies.
    * `invoices_panel.js`: Displays invoice details and receipt summaries.
    * `anomaly_panel.js`: Runs the anomaly scan and draws anomaly results.
    * `audit_panel.js`: Displays the read-only audit log table.
    * `users_panel.js`: Manages user login roles.

---

### 2. 🐍 The `backend` Folder
*This folder contains all backend Flask logic and data routing:*

* **`app.py`**: The entry point of the server. It imports all blueprints (feature routes), configures CORS (allowing backend-frontend communication), and runs the local server on port 5000.
* **`config.py`**: Holds database connection details (host, user, password, port) and security constants.
* **`database.py`**: Configures the connection pool to connect Flask safely to MySQL.
* **`requirements.txt`**: Lists Python packages required to run the backend (Flask, pandas, scikit-learn, mysql-connector-python).
* 📂 **`routes/`** (REST API Controllers)
  * *Each file represents a set of endpoints `/api/...` matching the database tables:*
  * `auth.py`: Endpoints for login authentication and user registration.
  * `inventory.py`: SQL commands for adding, editing, and deleting inventory items.
  * `stock.py`: Validates and registers stock movements (IN/OUT/TRANSFER/ADJUSTMENT).
  * `purchase.py`: Handles purchase orders (creating them and receiving items).
  * `approvals.py`: Submits and updates stock request statuses.
  * `alerts.py`: Checks for items below limits and serves notifications.
  * `invoices.py`: Generates receipt PDFs.
  * `anomaly.py`: **The Machine Learning core**. Uses the **Isolation Forest** model to detect outliers in stock movements and write anomaly warnings.
  * `qr.py`: Generates and decodes item QR codes.
  * `dashboard.py`: Queries databases to calculate metrics (Active Items, Total Value).
  * `audit.py`: Inserts record logs of operations in the database.
---

### 3. 🗄️ The `database` Folder
*This folder groups your relational database script assets:*

* **`database.sql`**: The master database setup script. Running this file in MySQL automatically creates all database tables, indexes, triggers (for calculations), views, and seed credentials for login users.

---

### 4. 📄 The Root Directory (Project files)
*These files configure, setup, and document the project:*

* **`install_and_run.bat`**: One-click batch file that sets up a local Python virtual environment, installs the backend libraries, and launches the server.
* **`run_backend.bat`**: Shortcut to launch the Flask server directly if dependencies are already installed.
* **`fix_database_crash.bat`**: Interactive emergency tool you can use to free port 3306 or run deep repairs if the database crashes.
* **`stockwatch_final_project_report.md`**: Your complete academic report for the project.
* **`view_diagrams.html`**: A standalone browser page showing custom inline SVGs of your Chen ER diagram.
