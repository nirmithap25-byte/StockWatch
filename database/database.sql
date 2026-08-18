-- ─────────────────────────────────────────────────────────────
-- STOCKWATCH UNIFIED DATABASE SCHEMA & SAMPLE DATA
-- ─────────────────────────────────────────────────────────────
-- This file contains all table creations, triggers, views, and 
-- sample data in a single script. Import this file in phpMyAdmin 
-- to set up the database in one click.
-- ─────────────────────────────────────────────────────────────

DROP DATABASE IF EXISTS inventory_monitoring_system;
CREATE DATABASE inventory_monitoring_system;
USE inventory_monitoring_system;

-- ── 1. TABLES CREATION ────────────────────────────────────────

CREATE TABLE departments (
    department_id INT AUTO_INCREMENT PRIMARY KEY,
    department_name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    phone VARCHAR(15),
    role ENUM('Admin','Inventory Manager','Department Head','Auditor') NOT NULL,
    department_id INT,
    status ENUM('Active','Inactive') DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
        ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE suppliers (
    supplier_id INT AUTO_INCREMENT PRIMARY KEY,
    supplier_name VARCHAR(100) NOT NULL,
    contact_person VARCHAR(100),
    phone VARCHAR(15),
    email VARCHAR(100),
    address VARCHAR(255),
    city VARCHAR(50),
    state VARCHAR(50),
    pincode VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE inventory_items (
    item_id INT AUTO_INCREMENT PRIMARY KEY,
    item_code VARCHAR(20) UNIQUE NOT NULL,
    item_name VARCHAR(150) NOT NULL,
    description TEXT,
    category_id INT NOT NULL,
    supplier_id INT NOT NULL,
    department_id INT NOT NULL,
    quantity INT DEFAULT 0,
    minimum_stock INT DEFAULT 5,
    reorder_level INT DEFAULT 10,
    reorder_quantity INT DEFAULT 20,
    unit VARCHAR(20) NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    qr_code VARCHAR(100) UNIQUE,
    is_active ENUM('Yes','No') DEFAULT 'Yes',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY(category_id) REFERENCES categories(category_id),
    FOREIGN KEY(supplier_id) REFERENCES suppliers(supplier_id),
    FOREIGN KEY(department_id) REFERENCES departments(department_id)
);

CREATE TABLE purchase_orders (
    po_id INT AUTO_INCREMENT PRIMARY KEY,
    po_number VARCHAR(30) UNIQUE NOT NULL,
    supplier_id INT NOT NULL,
    ordered_by INT NOT NULL,
    approved_by INT NULL,
    order_date DATE NOT NULL,
    expected_delivery DATE,
    approved_date DATETIME NULL,
    total_amount DECIMAL(12,2) DEFAULT 0,
    status ENUM('Pending','Approved','Ordered','Partially Received','Received','Cancelled') DEFAULT 'Pending',
    remarks VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(supplier_id) REFERENCES suppliers(supplier_id),
    FOREIGN KEY(ordered_by) REFERENCES users(user_id),
    FOREIGN KEY(approved_by) REFERENCES users(user_id)
);

CREATE TABLE purchase_order_items (
    po_item_id INT AUTO_INCREMENT PRIMARY KEY,
    po_id INT NOT NULL,
    item_id INT NOT NULL,
    quantity INT NOT NULL,
    received_quantity INT DEFAULT 0,
    unit_price DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(12,2) NOT NULL,
    FOREIGN KEY(po_id) REFERENCES purchase_orders(po_id) ON DELETE CASCADE,
    FOREIGN KEY(item_id) REFERENCES inventory_items(item_id)
);

CREATE TABLE stock_movements (
    movement_id INT AUTO_INCREMENT PRIMARY KEY,
    item_id INT NOT NULL,
    movement_type ENUM('IN','OUT','TRANSFER','ADJUSTMENT') NOT NULL,
    quantity INT NOT NULL,
    previous_quantity INT NOT NULL,
    new_quantity INT NOT NULL,
    from_department_id INT NULL,
    to_department_id INT NULL,
    reference_type ENUM('Purchase','Issue','Transfer','Adjustment','Manual') DEFAULT 'Manual',
    reference_id INT NULL,
    user_id INT NOT NULL,
    reason VARCHAR(255),
    movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(item_id) REFERENCES inventory_items(item_id),
    FOREIGN KEY(user_id) REFERENCES users(user_id),
    FOREIGN KEY(from_department_id) REFERENCES departments(department_id),
    FOREIGN KEY(to_department_id) REFERENCES departments(department_id)
);

CREATE TABLE approvals (
    approval_id INT AUTO_INCREMENT PRIMARY KEY,
    item_id INT NOT NULL,
    requested_by INT NOT NULL,
    approved_by INT NULL,
    quantity INT NOT NULL,
    purpose VARCHAR(255),
    status ENUM('Pending','Approved','Rejected') DEFAULT 'Pending',
    comments VARCHAR(255),
    request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approval_date TIMESTAMP NULL,
    FOREIGN KEY(item_id) REFERENCES inventory_items(item_id),
    FOREIGN KEY(requested_by) REFERENCES users(user_id),
    FOREIGN KEY(approved_by) REFERENCES users(user_id)
);

CREATE TABLE alerts (
    alert_id INT AUTO_INCREMENT PRIMARY KEY,
    item_id INT NULL,
    alert_type ENUM('Low Stock','Reorder Required','Anomaly','System') NOT NULL,
    severity ENUM('Low','Medium','High') DEFAULT 'Medium',
    message VARCHAR(255) NOT NULL,
    status ENUM('Unread','Read') DEFAULT 'Unread',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(item_id) REFERENCES inventory_items(item_id)
);

CREATE TABLE audit_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    module VARCHAR(100),
    action VARCHAR(100),
    table_name VARCHAR(100),
    record_id INT,
    description VARCHAR(255),
    ip_address VARCHAR(50),
    log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

CREATE TABLE invoices (
    invoice_id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_number VARCHAR(30) UNIQUE NOT NULL,
    po_id INT NOT NULL,
    supplier_id INT NOT NULL,
    supplier_name VARCHAR(100) NOT NULL,
    supplier_phone VARCHAR(15),
    supplier_email VARCHAR(100),
    supplier_address VARCHAR(255),
    total_amount DECIMAL(12,2) DEFAULT 0,
    status ENUM('Draft', 'Finalized', 'Cancelled') DEFAULT 'Draft',
    generated_by INT NOT NULL,
    notes TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(po_id) REFERENCES purchase_orders(po_id),
    FOREIGN KEY(supplier_id) REFERENCES suppliers(supplier_id),
    FOREIGN KEY(generated_by) REFERENCES users(user_id)
);

CREATE TABLE invoice_items (
    invoice_item_id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_id INT NOT NULL,
    item_id INT NOT NULL,
    item_code VARCHAR(20) NOT NULL,
    item_name VARCHAR(150) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(12,2) NOT NULL,
    FOREIGN KEY(invoice_id) REFERENCES invoices(invoice_id) ON DELETE CASCADE,
    FOREIGN KEY(item_id) REFERENCES inventory_items(item_id)
);

-- Indexes for performance
CREATE INDEX idx_item_name ON inventory_items(item_name);
CREATE INDEX idx_item_code ON inventory_items(item_code);
CREATE INDEX idx_stock_date ON stock_movements(movement_date);
CREATE INDEX idx_stock_item ON stock_movements(item_id);
CREATE INDEX idx_alert_status ON alerts(status);
CREATE INDEX idx_po_status ON purchase_orders(status);
CREATE INDEX idx_invoice_num ON invoices(invoice_number);

-- ── 2. TRIGGERS ──────────────────────────────────────────────

DELIMITER //

CREATE TRIGGER trg_stock_movement_insert
AFTER INSERT ON stock_movements
FOR EACH ROW
BEGIN
    IF NEW.movement_type = 'IN' THEN
        UPDATE inventory_items
        SET quantity = NEW.new_quantity
        WHERE item_id = NEW.item_id;
        
    ELSEIF NEW.movement_type IN ('OUT','TRANSFER','ADJUSTMENT') THEN
        UPDATE inventory_items
        SET quantity = NEW.new_quantity
        WHERE item_id = NEW.item_id;
    END IF;
END //

CREATE TRIGGER trg_low_stock_alert
AFTER UPDATE ON inventory_items
FOR EACH ROW
BEGIN
    IF NEW.quantity <= NEW.minimum_stock THEN
        INSERT INTO alerts(item_id, alert_type, severity, message)
        VALUES (NEW.item_id, 'Low Stock', 'High', 'Stock below minimum level');
    END IF;
END //

DELIMITER ;

-- ── 3. VIEWS ─────────────────────────────────────────────────

CREATE VIEW vw_inventory_summary AS
SELECT 
    i.item_id,
    i.item_code,
    i.item_name,
    c.category_name,
    d.department_name,
    i.quantity,
    i.minimum_stock,
    i.unit_price,
    s.supplier_name
FROM inventory_items i
JOIN categories c ON i.category_id = c.category_id
JOIN departments d ON i.department_id = d.department_id
JOIN suppliers s ON i.supplier_id = s.supplier_id;

CREATE VIEW vw_stock_report AS
SELECT 
    sm.movement_id,
    i.item_name,
    sm.movement_type,
    sm.quantity,
    sm.previous_quantity,
    sm.new_quantity,
    sm.movement_date,
    u.full_name AS performed_by
FROM stock_movements sm
JOIN inventory_items i ON sm.item_id = i.item_id
JOIN users u ON sm.user_id = u.user_id;

CREATE VIEW vw_pending_approvals AS
SELECT 
    a.approval_id,
    i.item_name,
    u.full_name AS requested_by,
    a.quantity,
    a.purpose,
    a.status,
    a.request_date
FROM approvals a
JOIN inventory_items i ON a.item_id = i.item_id
JOIN users u ON a.requested_by = u.user_id
WHERE a.status = 'Pending';

CREATE VIEW vw_invoice_summary AS
SELECT 
    i.invoice_id,
    i.invoice_number,
    i.po_id,
    po.po_number,
    i.supplier_name,
    i.supplier_phone,
    i.supplier_email,
    i.supplier_address,
    ii.invoice_item_id,
    ii.item_code,
    ii.item_name,
    ii.unit,
    ii.quantity,
    ii.unit_price,
    ii.subtotal,
    i.total_amount,
    i.status,
    u.full_name AS generated_by,
    i.generated_at,
    i.notes
FROM invoices i
JOIN purchase_orders po ON i.po_id = po.po_id
JOIN users u ON i.generated_by = u.user_id
JOIN invoice_items ii ON i.invoice_id = ii.invoice_id;

-- ── 4. SAMPLE DATA INSERTS ────────────────────────────────────

INSERT INTO departments(department_name,description) VALUES
('Warehouse','Central warehouse'),
('Sales','Sales department'),
('Finance','Finance department'),
('IT','IT support'),
('Administration','Admin office');

INSERT INTO categories(category_name,description) VALUES
('Electronics','Electronic items'),
('Networking','Network devices'),
('Office Supplies','Office items'),
('Furniture','Furniture'),
('Accessories','Accessories');

INSERT INTO suppliers(supplier_name,contact_person,phone,email,address,city,state,pincode) VALUES
('TechNova Solutions','Rajesh','9876500001','sales@technova.com','12 MG Road','Bengaluru','Karnataka','560001'),
('Global IT Supplies','Anita','9876500002','info@globalit.com','45 Park St','Mumbai','Maharashtra','400001'),
('Prime Office Systems','Vijay','9876500003','contact@primeoffice.com','88 Market Rd','Hyderabad','Telangana','500001'),
('Elite Electronics','Kiran','9876500004','support@elite.com','22 Ring Rd','Chennai','Tamil Nadu','600001'),
('Smart Trade Distributors','Rohit','9876500005','sales@smarttrade.com','10 Industrial Area','Pune','Maharashtra','411001');

INSERT INTO users(full_name,email,password,phone,role,department_id) VALUES
('Admin User','admin@stockwatch.com','admin123','9000000001','Admin',5),
('Asha Manager','manager@stockwatch.com','manager123','9000000002','Inventory Manager',1),
('Ravi Head','head@stockwatch.com','head123','9000000003','Department Head',2),
('Meera Auditor','auditor@stockwatch.com','audit123','9000000004','Auditor',3),
('Kiran IT','it@stockwatch.com','it123','9000000005','Inventory Manager',4);

INSERT INTO inventory_items(item_code,item_name,description,category_id,supplier_id,department_id,quantity,minimum_stock,reorder_level,reorder_quantity,unit,unit_price,qr_code) VALUES
('ITM001','Dell Latitude Laptop','Laptop',1,1,4,25,5,10,20,'Nos',65000,'QR001'),
('ITM002','HP Laser Printer','Printer',1,2,1,8,3,5,10,'Nos',18000,'QR002'),
('ITM003','Cisco Router','Router',2,4,4,12,4,6,10,'Nos',12000,'QR003'),
('ITM004','24 Inch Monitor','Monitor',1,1,4,15,5,8,10,'Nos',9000,'QR004'),
('ITM005','Wireless Mouse','Mouse',5,4,4,50,10,20,40,'Nos',700,'QR005'),
('ITM006','Keyboard','Keyboard',5,4,4,40,10,20,40,'Nos',900,'QR006'),
('ITM007','Network Switch','Switch',2,2,4,10,3,5,10,'Nos',8500,'QR007'),
('ITM008','UPS','UPS',1,5,1,9,2,4,8,'Nos',6500,'QR008'),
('ITM009','Office Chair','Chair',4,3,5,20,5,10,15,'Nos',3500,'QR009'),
('ITM010','External HDD','Storage',5,1,4,18,5,8,10,'Nos',5500,'QR010');

INSERT INTO purchase_orders(po_number,supplier_id,ordered_by,approved_by,order_date,expected_delivery,approved_date,total_amount,status,remarks) VALUES
('PO1001',1,2,1,'2026-06-01','2026-06-05','2026-06-02',130000,'Received','Initial order'),
('PO1002',2,2,1,'2026-06-08','2026-06-12','2026-06-09',36000,'Ordered','Printer order'),
('PO1003',4,5,1,'2026-06-10','2026-06-15','2026-06-11',24000,'Approved','Network'),
('PO1004',3,2,1,'2026-06-15','2026-06-20','2026-06-16',17500,'Pending','Furniture'),
('PO1005',5,2,1,'2026-06-18','2026-06-25','2026-06-19',13000,'Cancelled','Cancelled');

INSERT INTO purchase_order_items(po_id,item_id,quantity,received_quantity,unit_price,subtotal) VALUES
(1,1,2,2,65000,130000),(2,2,2,0,18000,36000),(3,3,2,0,12000,24000),(4,9,5,0,3500,17500),
(5,8,2,0,6500,13000),(3,7,1,0,8500,8500),(2,8,1,0,6500,6500),(1,5,10,10,700,7000),(1,6,10,10,900,9000),(4,10,2,0,5500,11000);

INSERT INTO stock_movements(item_id,movement_type,quantity,previous_quantity,new_quantity,from_department_id,to_department_id,reference_type,reference_id,user_id,reason) VALUES
(1,'IN',2,23,25,NULL,4,'Purchase',1,2,'PO'),
(2,'OUT',2,10,8,1,2,'Issue',101,2,'Issue'),
(3,'IN',2,10,12,NULL,4,'Purchase',3,5,'PO'),
(4,'ADJUSTMENT',1,14,15,NULL,NULL,'Adjustment',NULL,1,'Count'),
(5,'OUT',5,55,50,4,2,'Issue',102,2,'Issue'),
(6,'TRANSFER',5,45,40,4,1,'Transfer',201,2,'Transfer'),
(7,'IN',1,9,10,NULL,4,'Purchase',3,5,'PO'),
(8,'OUT',1,10,9,1,5,'Issue',103,2,'Issue'),
(9,'IN',5,15,20,NULL,5,'Purchase',4,2,'PO'),
(10,'OUT',2,20,18,4,2,'Issue',104,5,'Issue');

INSERT INTO approvals(item_id,requested_by,approved_by,quantity,purpose,status,comments,approval_date) VALUES
(1,3,1,2,'Project','Approved','OK',NOW()),
(2,3,NULL,1,'Office','Pending','',NULL),
(5,2,1,5,'Replacement','Approved','Approved',NOW()),
(8,5,1,1,'Maintenance','Rejected','Budget',NOW()),
(9,3,NULL,2,'Expansion','Pending','',NULL);

INSERT INTO alerts(item_id,alert_type,severity,message) VALUES
(2,'Low Stock','High','Printer stock low'),
(8,'Reorder Required','Medium','UPS reorder required'),
(5,'Anomaly','High','Unusual issue quantity'),
(NULL,'System','Low','Daily backup completed'),
(7,'Low Stock','Medium','Switch nearing minimum');

INSERT INTO audit_logs(user_id,module,action,table_name,record_id,description,ip_address) VALUES
(1,'Login','LOGIN','users',1,'Admin login','192.168.1.10'),
(2,'Inventory','INSERT','inventory_items',10,'Added HDD','192.168.1.11'),
(2,'Purchase','CREATE','purchase_orders',2,'Created PO1002','192.168.1.11'),
(5,'Stock','TRANSFER','stock_movements',6,'Transferred keyboard','192.168.1.12'),
(4,'Audit','VIEW','audit_logs',5,'Viewed logs','192.168.1.13');
