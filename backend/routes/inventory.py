# routes/inventory.py

from flask import Blueprint, request, jsonify
from database import get_cursor, commit, rollback
import jwt
import config

inventory_bp = Blueprint('inventory', __name__)


# ── Helper: extract user from JWT ─────────────────────────────
def get_user_from_token(req):
    try:
        token = req.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return {"user_id": 1, "role": "Admin"}  # fallback for testing
        return jwt.decode(token, config.SECRET_KEY, algorithms=['HS256'])
    except Exception:
        return {"user_id": 1, "role": "Admin"}  # fallback for testing


# ── Helper: write audit log ───────────────────────────────────
def write_audit(cursor, user_id, action, record_id, description, ip):
    cursor.execute("""
        INSERT INTO audit_logs
            (user_id, module, action, table_name, record_id, description, ip_address)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (user_id, 'Inventory', action, 'inventory_items', record_id, description, ip))


# ── Helper: check and trigger low stock alert ─────────────────
def check_low_stock(cursor, item_id):
    cursor.execute("""
        SELECT item_name, quantity, minimum_stock, reorder_level
        FROM inventory_items
        WHERE item_id = %s
    """, (item_id,))
    item = cursor.fetchone()
    if not item:
        return

    if item['quantity'] <= item['minimum_stock']:
        cursor.execute("""
            INSERT INTO alerts (item_id, alert_type, severity, message)
            VALUES (%s, 'Low Stock', 'High', %s)
        """, (item_id,
              f"{item['item_name']} is below minimum stock "
              f"(current: {item['quantity']}, minimum: {item['minimum_stock']})"))

    elif item['quantity'] <= item['reorder_level']:
        cursor.execute("""
            INSERT INTO alerts (item_id, alert_type, severity, message)
            VALUES (%s, 'Reorder Required', 'Medium', %s)
        """, (item_id,
              f"{item['item_name']} has reached reorder level "
              f"(current: {item['quantity']}, reorder at: {item['reorder_level']})"))


# ── Helper: check and trigger auto reorder ────────────────────
def check_auto_reorder(cursor, item_id, user_id):
    cursor.execute("""
        SELECT i.item_id, i.item_name, i.item_code, i.quantity,
               i.reorder_level, i.reorder_quantity,
               i.supplier_id, i.unit_price
        FROM inventory_items i
        WHERE i.item_id = %s AND i.quantity <= i.reorder_level
    """, (item_id,))
    item = cursor.fetchone()
    if not item:
        return None

    # Check if a pending PO already exists for this item
    cursor.execute("""
        SELECT po.po_id FROM purchase_orders po
        JOIN purchase_order_items poi ON po.po_id = poi.po_id
        WHERE poi.item_id = %s
        AND po.status IN ('Pending', 'Approved', 'Ordered')
        LIMIT 1
    """, (item_id,))
    if cursor.fetchone():
        return None  # PO already pending, skip

    # Generate PO number
    cursor.execute("SELECT COUNT(*) AS cnt FROM purchase_orders")
    count     = cursor.fetchone()['cnt']
    po_number = f"AUTO-PO-{count + 1:04d}"
    subtotal  = item['reorder_quantity'] * float(item['unit_price'])

    # Create PO
    cursor.execute("""
        INSERT INTO purchase_orders
            (po_number, supplier_id, ordered_by, order_date,
             expected_delivery, total_amount, status, remarks)
        VALUES (%s, %s, %s, CURDATE(),
                DATE_ADD(CURDATE(), INTERVAL 7 DAY),
                %s, 'Pending', %s)
    """, (po_number, item['supplier_id'], user_id, subtotal,
          f"Auto-reorder for {item['item_name']}"))

    po_id = cursor.lastrowid

    # Create PO item
    cursor.execute("""
        INSERT INTO purchase_order_items
            (po_id, item_id, quantity, received_quantity, unit_price, subtotal)
        VALUES (%s, %s, %s, 0, %s, %s)
    """, (po_id, item_id, item['reorder_quantity'],
          item['unit_price'], subtotal))

    # Alert
    cursor.execute("""
        INSERT INTO alerts (item_id, alert_type, severity, message)
        VALUES (%s, 'Reorder Required', 'High', %s)
    """, (item_id,
          f"Auto-reorder PO {po_number} created for "
          f"{item['item_name']} (qty: {item['reorder_quantity']})"))

    return po_number


# ─────────────────────────────────────────────────────────────
# GET /api/inventory/items  — all active items with full details
# ─────────────────────────────────────────────────────────────
@inventory_bp.route('/items', methods=['GET'])
def get_all_items():
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                i.item_id, i.item_code, i.item_name, i.description,
                i.quantity, i.minimum_stock, i.reorder_level,
                i.reorder_quantity, i.unit, i.unit_price,
                i.qr_code, i.is_active, i.created_at, i.updated_at,
                c.category_name,
                s.supplier_name,
                d.department_name
            FROM inventory_items i
            JOIN categories  c ON i.category_id  = c.category_id
            JOIN suppliers   s ON i.supplier_id   = s.supplier_id
            JOIN departments d ON i.department_id = d.department_id
            WHERE i.is_active = 'Yes'
            ORDER BY i.item_name
        """)
        items = cursor.fetchall()

        # Convert Decimal to float for JSON
        for item in items:
            item['unit_price'] = float(item['unit_price'])

        return jsonify({"success": True, "count": len(items), "data": items}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/inventory/items/low-stock  — items below reorder level
# ─────────────────────────────────────────────────────────────
@inventory_bp.route('/items/low-stock', methods=['GET'])
def get_low_stock():
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                i.item_id, i.item_code, i.item_name,
                i.quantity, i.minimum_stock, i.reorder_level,
                i.reorder_quantity, i.unit, i.unit_price,
                c.category_name, s.supplier_name, d.department_name
            FROM inventory_items i
            JOIN categories  c ON i.category_id  = c.category_id
            JOIN suppliers   s ON i.supplier_id   = s.supplier_id
            JOIN departments d ON i.department_id = d.department_id
            WHERE i.is_active = 'Yes'
            AND   i.quantity <= i.reorder_level
            ORDER BY i.quantity ASC
        """)
        items = cursor.fetchall()
        for item in items:
            item['unit_price'] = float(item['unit_price'])

        return jsonify({"success": True, "count": len(items), "data": items}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/inventory/items/search?keyword=laptop
# ─────────────────────────────────────────────────────────────
@inventory_bp.route('/items/search', methods=['GET'])
def search_items():
    cursor = None
    try:
        keyword = request.args.get('keyword', '').strip()
        if not keyword:
            return jsonify({"success": False, "message": "keyword is required"}), 400

        like = f"%{keyword}%"
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                i.item_id, i.item_code, i.item_name,
                i.quantity, i.unit, i.unit_price, i.is_active,
                c.category_name, s.supplier_name, d.department_name
            FROM inventory_items i
            JOIN categories  c ON i.category_id  = c.category_id
            JOIN suppliers   s ON i.supplier_id   = s.supplier_id
            JOIN departments d ON i.department_id = d.department_id
            WHERE i.is_active = 'Yes'
            AND (i.item_name LIKE %s OR i.item_code LIKE %s)
        """, (like, like))

        items = cursor.fetchall()
        for item in items:
            item['unit_price'] = float(item['unit_price'])

        return jsonify({"success": True, "count": len(items), "data": items}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/inventory/items/<id>  — single item full details
# ─────────────────────────────────────────────────────────────
@inventory_bp.route('/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                i.item_id, i.item_code, i.item_name, i.description,
                i.quantity, i.minimum_stock, i.reorder_level,
                i.reorder_quantity, i.unit, i.unit_price,
                i.qr_code, i.is_active, i.created_at, i.updated_at,
                i.category_id, i.supplier_id, i.department_id,
                c.category_name, s.supplier_name, d.department_name
            FROM inventory_items i
            JOIN categories  c ON i.category_id  = c.category_id
            JOIN suppliers   s ON i.supplier_id   = s.supplier_id
            JOIN departments d ON i.department_id = d.department_id
            WHERE i.item_id = %s
        """, (item_id,))
        item = cursor.fetchone()

        if not item:
            return jsonify({"success": False, "message": "Item not found"}), 404

        item['unit_price'] = float(item['unit_price'])
        return jsonify({"success": True, "data": item}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# POST /api/inventory/items  — add new item
# ─────────────────────────────────────────────────────────────
@inventory_bp.route('/items', methods=['POST'])
def add_item():
    cursor = None
    try:
        data = request.get_json()
        user = get_user_from_token(request)
        ip   = request.remote_addr

        required = [
            'item_code', 'item_name', 'category_id', 'supplier_id',
            'department_id', 'quantity', 'minimum_stock',
            'reorder_level', 'reorder_quantity', 'unit',
            'unit_price', 'qr_code'
        ]
        for field in required:
            if not data.get(field) and data.get(field) != 0:
                return jsonify({"success": False,
                                "message": f"{field} is required"}), 400

        cursor = get_cursor()

        # Duplicate item_code check
        cursor.execute(
            "SELECT item_id FROM inventory_items WHERE item_code = %s",
            (data['item_code'],))
        if cursor.fetchone():
            return jsonify({"success": False,
                            "message": "Item code already exists"}), 409

        # Duplicate qr_code check
        cursor.execute(
            "SELECT item_id FROM inventory_items WHERE qr_code = %s",
            (data['qr_code'],))
        if cursor.fetchone():
            return jsonify({"success": False,
                            "message": "QR code already exists"}), 409

        # Insert item
        cursor.execute("""
            INSERT INTO inventory_items
                (item_code, item_name, description, category_id,
                 supplier_id, department_id, quantity, minimum_stock,
                 reorder_level, reorder_quantity, unit, unit_price, qr_code)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            data['item_code'], data['item_name'],
            data.get('description', ''),
            data['category_id'], data['supplier_id'], data['department_id'],
            data['quantity'], data['minimum_stock'], data['reorder_level'],
            data['reorder_quantity'], data['unit'], data['unit_price'],
            data['qr_code']
        ))
        item_id = cursor.lastrowid

        # Initial stock movement if quantity > 0
        if int(data['quantity']) > 0:
            cursor.execute("""
                INSERT INTO stock_movements
                    (item_id, movement_type, quantity, previous_quantity,
                     new_quantity, reference_type, user_id, reason)
                VALUES (%s, 'IN', %s, 0, %s, 'Manual', %s, %s)
            """, (item_id, data['quantity'], data['quantity'],
                  user['user_id'], 'Initial stock entry'))

        # Audit log
        write_audit(cursor, user['user_id'], 'INSERT', item_id,
                    f"Added item {data['item_code']} - {data['item_name']}", ip)

        # Check low stock alert
        check_low_stock(cursor, item_id)

        commit()
        return jsonify({
            "success": True,
            "message": "Item added successfully",
            "item_id": item_id
        }), 201

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# PUT /api/inventory/items/<id>  — update item
# ─────────────────────────────────────────────────────────────
@inventory_bp.route('/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    cursor = None
    try:
        data = request.get_json()
        user = get_user_from_token(request)
        ip   = request.remote_addr

        cursor = get_cursor()

        # Check item exists
        cursor.execute(
            "SELECT item_id, item_name FROM inventory_items WHERE item_id = %s",
            (item_id,))
        existing = cursor.fetchone()
        if not existing:
            return jsonify({"success": False, "message": "Item not found"}), 404

        cursor.execute("""
            UPDATE inventory_items SET
                item_name      = %s, description  = %s,
                category_id    = %s, supplier_id  = %s,
                department_id  = %s, minimum_stock = %s,
                reorder_level  = %s, reorder_quantity = %s,
                unit           = %s, unit_price   = %s,
                is_active      = %s
            WHERE item_id = %s
        """, (
            data['item_name'], data.get('description', ''),
            data['category_id'], data['supplier_id'],
            data['department_id'], data['minimum_stock'],
            data['reorder_level'], data['reorder_quantity'],
            data['unit'], data['unit_price'],
            data.get('is_active', 'Yes'),
            item_id
        ))

        # Audit log
        write_audit(cursor, user['user_id'], 'UPDATE', item_id,
                    f"Updated item {existing['item_name']}", ip)

        # Check low stock after update
        check_low_stock(cursor, item_id)

        # Check auto reorder
        check_auto_reorder(cursor, item_id, user['user_id'])

        commit()
        return jsonify({"success": True,
                        "message": "Item updated successfully"}), 200

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# DELETE /api/inventory/items/<id>  — soft delete
# ─────────────────────────────────────────────────────────────
@inventory_bp.route('/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    cursor = None
    try:
        user = get_user_from_token(request)
        ip   = request.remote_addr

        cursor = get_cursor()
        cursor.execute(
            "SELECT item_code, item_name FROM inventory_items WHERE item_id = %s",
            (item_id,))
        item = cursor.fetchone()
        if not item:
            return jsonify({"success": False, "message": "Item not found"}), 404

        cursor.execute(
            "UPDATE inventory_items SET is_active = 'No' WHERE item_id = %s",
            (item_id,))

        write_audit(cursor, user['user_id'], 'DELETE', item_id,
                    f"Deactivated {item['item_code']} - {item['item_name']}", ip)
        commit()

        return jsonify({"success": True,
                        "message": "Item deactivated successfully"}), 200

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/inventory/categories  — for dropdowns
# ─────────────────────────────────────────────────────────────
@inventory_bp.route('/categories', methods=['GET'])
def get_categories():
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("SELECT category_id, category_name FROM categories ORDER BY category_name")
        return jsonify({"success": True, "data": cursor.fetchall()}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/inventory/suppliers  — for dropdowns
# ─────────────────────────────────────────────────────────────
@inventory_bp.route('/suppliers', methods=['GET'])
def get_suppliers():
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("SELECT supplier_id, supplier_name, phone, email FROM suppliers ORDER BY supplier_name")
        return jsonify({"success": True, "data": cursor.fetchall()}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/inventory/departments  — for dropdowns
# ─────────────────────────────────────────────────────────────
@inventory_bp.route('/departments', methods=['GET'])
def get_departments():
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("SELECT department_id, department_name FROM departments ORDER BY department_name")
        return jsonify({"success": True, "data": cursor.fetchall()}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()