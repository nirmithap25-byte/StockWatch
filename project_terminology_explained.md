# 📖 StockWatch: Complete Terminology & Feature Guide

This guide explains **every metric, menu item, and feature** in your project, what they mean in real business terms, and how to explain them to your examiner.

---

## 📊 1. The Dashboard Metrics (Top Cards)

These cards give managers a high-level summary of the entire system at a single glance:

### 🔹 Active Items
* **What it means:** The total number of **unique product types** registered in your catalog (e.g., Cisco Router, HP Printer, Dell Laptop count as 3 active items).
* **Viva Explanation:** *"Mam, this shows how many distinct product models we currently manage in our warehouse catalog, regardless of their stock quantities."*

### 🔹 Total Value (₹)
* **What it means:** The total financial worth of your current inventory. It is calculated by multiplying the stock quantity of each item by its unit price (`Quantity × Unit Price`) and adding them all together.
* **Viva Explanation:** *"This represents the total capital investment currently sitting in our warehouse. If we sell or check out an item, this value automatically updates."*

### 🔹 Low Stock Warning
* **What it means:** The count of products whose current warehouse quantity has dropped below their defined **Minimum Stock Level** (reorder point).
* **Viva Explanation:** *"Each item has a safety threshold. If we have 10 printers as our limit, and stock drops to 9, this counter increases and triggers an alert so we can reorder before running out."*

### 🔹 Pending Orders (Purchase Orders)
* **What it means:** Orders placed by your organization to **external suppliers** for buying new items that have **not yet arrived** (still in transit or processing).
* **Viva Explanation:** *"This shows how many active shipments we are expecting from our suppliers. Once the supplier delivers the items and we mark them as 'Received', this number goes down and our stock goes up."*

### 🔹 Pending Requests (Stock Requests)
* **What it means:** Internal requests made by **Department Heads** (like the CSE or ECE department) asking the main warehouse to give them items, which are **waiting for the Manager's approval**.
* **Viva Explanation:** *"This tracks internal requests. Stock cannot leave the warehouse until the Inventory Manager clicks 'Approve' on these pending requests."*

---

## 🗂️ 2. The Left Sidebar Modules

Explain what each page on the left menu does:

### 🔹 Inventory (Master Catalog)
* **Purpose:** The list of all products. You can search, edit details, or register a new product here.
* **Key Concept:** This is **Master Data**. Editing a price here does not create a stock movement; it only changes the product description.

### 🔹 Stock Movements (Transactions)
* **Purpose:** The screen where physical inventory is checked in or out. It has:
  * **Stock IN (+):** Adding stock (e.g., new shipments).
  * **Stock OUT (-):** Deducting stock (e.g., items issued to a classroom or discarded).
  * **Transfer:** Moving stock from one department/lab to another.
  * **Adjustment:** Correcting stock counts manually after an audit.

### 🔹 Purchase Orders
* **Purpose:** Procurement management. It allows you to create orders to buy products from registered suppliers (like buying 20 keyboards from Dell).

### 🔹 Stock Requests
* **Purpose:** Departmental tracking. Department heads use this screen to request assets (like asking for 5 monitors). Managers use it to approve or reject requests.

### 🔹 Alerts Inbox
* **Purpose:** The notifications center. It displays system-generated warnings for **Low Stock** and **Machine Learning Anomalies**.

### 🔹 Invoices
* **Purpose:** Financial records. When stock is checked out or purchased, the system automatically generates an invoice receipt showing the total cost, tax, and department details.

### 🔹 Anomaly Detection (ML)
* **Purpose:** Security. It runs the **Isolation Forest** ML algorithm to scan all transactions and flag suspicious behaviors (like an employee logging a massive stock drop or a suspicious manual adjustment).

### 🔹 Audit Logs
* **Purpose:** Compliance and Security. A read-only, permanent timeline tracking **everything** that happens in the app:
  * Who logged in (with timestamps).
  * What record was edited or deleted.
  * What IP address they used.
  * *Meaning:* It ensures complete accountability—nobody can alter data secretly.

---

## 📈 3. Charts Explained

### 🔹 Popular Items Movements (Bar Chart)
* **What it shows:** Which products are being transacted the most. 
* **Meaning:** It tells the manager which items are in high demand (e.g., if "UPS" is moved 20 times this week, it will have a tall bar).

### 🔹 Movement Breakdown (Doughnut Chart)
* **What it shows:** The proportion of transaction types (IN, OUT, TRANSFER, ADJUSTMENT).
* **Meaning:** It tells the manager how busy the warehouse is with inbound shipments vs. outbound issues.
