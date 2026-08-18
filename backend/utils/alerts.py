# utils/check_low_stock.py

from datetime import datetime


def check_low_stock(cur, item_id):
    """
    Triggered after every stock OUT or ADJUSTMENT.
    If quantity <= reorder_level:
      1. Insert Low Stock alert (if no unread exists)
      2. Insert Reorder Required alert (if no unread exists)
      3. Auto-create a Purchase Order (if no pending PO exists for this item)
         — Manager must approve via /api/purchase/<po_id>/approve
    Uses raw cursor (cur) — caller must commit after calling this.
    """

    cur.execute("""
        SELECT
            item_name, quantity, minimum_stock,
            reorder_level, reorder_quantity,
            supplier_id, unit_price
        FROM inventory_items
        WHERE item_id = %s AND is_active = 'Yes'
    """, (item_id,))
    item = cur.fetchone()

    if not item:
        return

    item_name = item['item_name']
    quantity = item['quantity']
    minimum_stock = item['minimum_stock']
    reorder_level = item['reorder_level']
    reorder_quantity = item['reorder_quantity']
    supplier_id = item['supplier_id']
    unit_price = item['unit_price']


    if quantity > reorder_level:
        return  # Stock is fine, nothing to do

    # ──────────────────────────────────────────────────────────
    # STEP 1: Insert Low Stock Alert (avoid duplicates)
    # ──────────────────────────────────────────────────────────
    cur.execute("""
        SELECT alert_id FROM alerts
        WHERE item_id = %s AND status = 'Unread' AND alert_type = 'Low Stock'
    """, (item_id,))
    if not cur.fetchone():
        severity = "High" if quantity == 0 else "Medium"
        cur.execute("""
            INSERT INTO alerts (item_id, alert_type, severity, message)
            VALUES (%s, 'Low Stock', %s, %s)
        """, (
            item_id,
            severity,
            f"{item_name} is below reorder level. "
            f"Current stock: {quantity}. Auto PO raised."
        ))

    # ──────────────────────────────────────────────────────────
    # STEP 2: Insert Reorder Required Alert (avoid duplicates)
    # ──────────────────────────────────────────────────────────
    cur.execute("""
        SELECT alert_id FROM alerts
        WHERE item_id = %s AND status = 'Unread' AND alert_type = 'Reorder Required'
    """, (item_id,))
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO alerts (item_id, alert_type, severity, message)
            VALUES (%s, 'Reorder Required', 'High', %s)
        """, (
            item_id,
            f"Auto Purchase Order raised for '{item_name}'. "
            f"Pending manager approval."
        ))

    # ──────────────────────────────────────────────────────────
    # STEP 3: Auto Create Purchase Order (skip if one already pending)
    # ──────────────────────────────────────────────────────────
    cur.execute("""
        SELECT po.po_id FROM purchase_orders po
        JOIN purchase_order_items poi ON po.po_id = poi.po_id
        WHERE poi.item_id = %s AND po.status = 'Pending'
        LIMIT 1
    """, (item_id,))
    if cur.fetchone():
        return  # Pending PO already exists — skip

    po_number    = "AUTO-PO-" + datetime.now().strftime("%Y%m%d%H%M%S")
    total_amount = float(reorder_quantity) * float(unit_price)
    order_date   = datetime.now().strftime("%Y-%m-%d")

    cur.execute("""
        INSERT INTO purchase_orders
            (po_number, supplier_id, ordered_by, order_date,
             total_amount, status, remarks)
        VALUES (%s, %s, 1, %s, %s, 'Pending', %s)
    """, (
        po_number,
        supplier_id,
        order_date,
        total_amount,
        f"Auto-generated PO for low stock item: {item_name}"
    ))
    po_id = cur.lastrowid

    cur.execute("""
        INSERT INTO purchase_order_items
            (po_id, item_id, quantity, received_quantity, unit_price, subtotal)
        VALUES (%s, %s, %s, 0, %s, %s)
    """, (
        po_id, item_id,
        reorder_quantity,
        unit_price,
        total_amount
    ))

    # Audit log for Auto PO
    cur.execute("""
        INSERT INTO audit_logs
            (user_id, module, action, table_name, record_id, description, ip_address)
        VALUES (1, 'Purchase Order', 'AUTO-CREATE', 'purchase_orders', %s, %s, 'system')
    """, (
        po_id,
        f"Auto PO {po_number} created for low stock item "
        f"'{item_name}'. Awaiting manager approval."
    ))
    # NOTE: Caller is responsible for commit() after this function returns.
