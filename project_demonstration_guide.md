# 🎓 StockWatch Project Demonstration & Viva Guide

This guide is your step-by-step script for your main lab exam demonstration tomorrow. Use it to walk the external examiner through your project logically and confidently to score maximum marks!

---

## ⏱️ Section 1: The 1-Minute Pitch (How to start)
When the external examiner sits at your computer, start with this opening statement:
> *"Good morning, Mam / Sir. Today I am presenting **StockWatch**, a Smart Inventory Monitoring and Audit System. Traditional inventory systems rely on simple manual counts or spreadsheet tracking, which lack accountability and lead to theft or data loss. StockWatch solves this by providing role-based tracking, automatic transaction logging, and a Machine Learning module (using Isolation Forest) that automatically detects and flags suspicious or anomalous stock behaviors."*

---

## 🚶‍♂️ Section 2: Step-by-Step Live Demo Script

Follow this exact user journey to show off the system features smoothly:

### 👤 Part 1: The Inventory Manager (Operations)
* **Goal:** Show how daily inventory is managed and tracked.
1. **Login:** Log in with `manager@stockwatch.com` (Password: `manager123`).
2. **Dashboard:** Point out the main summary cards:
   * Point out the **Total Value** auto-calculated in Rupees (e.g., ₹24,31,500.00).
   * Show the **Movement Breakdown Chart** (Green for `IN`, Red for `OUT`, Purple for `TRANSFER`) and explain that this gives the manager an instant visual summary of daily warehouse traffic.
3. **Add an Item (Master Catalog):** 
   * Go to **Inventory** -> click **Add Item**.
   * Add a test item (e.g., "Logitech Keyboard", Code: `LOGI001`, Dept: `IT`, Stock: `50`, Price: `1500`).
   * Explain: *"This creates a new product category in our master catalog database."*
4. **Record a Transaction (Daily Action):**
   * Go to **Stock Movements**.
   * Select **Stock OUT (-)**, pick **HP Laser Printer**, enter Quantity **`2`**, and write Reason: *"Issued to Computer Lab 3"*. Click **Execute**.
   * Explain: *"Mam, this updates the inventory quantity in real-time and logs the transaction in the Movements Log with the operator's name, timestamps, and reason. This prevents employees from altering quantities without a trace."*

### 👤 Part 2: The Department Head (Approvals)
* **Goal:** Show how departments request new stock securely.
1. **Login:** Log out and log in with `head@stockwatch.com` (Password: `head123`).
2. **Stock Request:** Create a request for some items (e.g. 5 UPS).
3. **Approval Flow:** Log back in as Manager and approve the request.
4. Explain: *"Only authorized users can request stock, and it must go through manager approval before any item is deducted from the database."*

### 👤 Part 3: The Auditor & Machine Learning (Security & Audits)
* **Goal:** Show the advanced security features that will earn you the highest marks.
1. **Login:** Log in with `auditor@stockwatch.com` (Password: `auditor123`).
2. **Run Anomaly Detection:**
   * Go to the **Anomaly Detection** / **Scan** panel.
   * Click **Run Scan**.
   * Explain: *"Our system uses the **Isolation Forest Machine Learning algorithm** to scan all transaction records. It calculates the percentage of stock changed in each transaction. If an employee tries to drain an unusually large amount of stock in one go, the algorithm flags it as an outlier."*
3. **Alerts Inbox:**
   * Go to **Alerts**. Show the list of red warnings (e.g., Anomaly warning for high volume stock outs).
   * Explain: *"The flagged anomalies are sent straight to the security alerts inbox for investigation."*
4. **Audit Logs:**
   * Go to **Audit Logs**.
   * Explain: *"Every single login attempt, password change, stock movement, or scan is logged permanently with the user's role, action details, and IP address for complete transparency."*

---

## ❓ Section 3: Standard Viva Questions & Answers

Be prepared to answer these common questions instantly:

### Q1: What machine learning algorithm did you use, and how does it work?
> **Answer:** "We used the **Isolation Forest** algorithm from Python's `scikit-learn` library. It is an unsupervised outlier detection method. Instead of learning what normal data looks like, it isolates anomalies by randomly partitioning transaction features. Anomalies require fewer partitions to isolate (they are closer to the root of the tree) and receive a negative score."

### Q2: What features does the Anomaly Detection model analyze?
> **Answer:** "It analyzes each stock transaction's quantity, the previous stock level, the new stock level, the transaction type (IN/OUT/ADJUSTMENT), the absolute size of the change, and the **drop percentage** (how much of the existing stock was removed in a single event)."

### Q3: Why do you have both "Inventory" and "Stock Movements" pages?
> **Answer:** "The **Inventory** page represents **Master Data** (the product catalog—defining names, codes, and prices). The **Stock Movements** page represents **Transactional Data** (recording daily stock increases, decreases, or audits with timestamps, user IDs, and justifications to maintain a complete audit trail)."

### Q4: How is database security handled in this project?
> **Answer:** "We implemented three levels of security:
> 1. **Role-Based Access Control (RBAC):** Different screens and API endpoints are restricted based on roles (Manager, Department Head, Auditor, Admin).
> 2. **Audit Logging:** Every user action is recorded in the `audit_logs` table along with their IP address and timestamps.
> 3. **Validation Triggers:** MySQL database triggers prevent inventory quantities from dropping below zero."

### Q5: What is the tech stack of your application?
> **Answer:** 
> * **Frontend:** Vanilla HTML5, CSS3 (Light Mode theme), and JavaScript.
> * **Backend:** Flask (Python web framework) creating a RESTful API.
> * **Database:** MariaDB/MySQL hosted locally on XAMPP.

---

🎨 *Good luck tomorrow! Keep XAMPP and your backend running before the examiner arrives, and present with confidence!*
