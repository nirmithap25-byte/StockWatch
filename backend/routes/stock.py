# routes/stock.py

from flask import Blueprint, request, jsonify
from database import get_cursor, commit, rollback
import jwt
import config

stock_bp = Blueprint('stock', __name__)


# ── Helper: extract user from JWT ─────────────────────────────
def get_user_from_token(req):
    try:
        token = req.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return {"user_id": 1, "role": "Admin"}
        return jwt.decode(token, config.SECRET_KEY, algorithms=['HS256'])
    except Exception:
        return {"user_id": 1, "role": "Admin"}


# ── Helper: audit log ─────────────────────────────────────────
def write_audit(cursor, user_id, action, record_id, description, ip):
    cursor.execute("""
        INSERT INTO audit_logs
            (user_id, module, action, table_name, record_id, description, ip_address)
        VALUES (%s, 'Stock', %s, 'stock_movements', %s, %s, %s)
    """, (user_id, action, record_id, description, ip))


# ── Helper: low stock alert ───────────────────────────────────
def check_low_stock(cursor, item_id):
    cursor.execute("""
        SELECT item_name, quantity, minimum_stock, reorder_level
        FROM inventory_items WHERE item_id = %s
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
              f"(current: {item['quantity']}, "
              f"minimum: {item['minimum_stock']})"))

    elif item['quantity'] <= item['reorder_level']:
        cursor.execute("""
            INSERT INTO alerts (item_id, alert_type, severity, message)
            VALUES (%s, 'Reorder Required', 'Medium', %s)
        """, (item_id,
              f"{item['item_name']} reached reorder level "
              f"(current: {item['quantity']}, "
              f"reorder at: {item['reorder_level']})"))


# ── Helper: auto reorder ──────────────────────────────────────
def check_auto_reorder(cursor, item_id, user_id):
    cursor.execute("""
        SELECT i.item_id, i.item_name, i.item_code,
               i.quantity, i.reorder_level,
               i.reorder_quantity, i.supplier_id, i.unit_price
        FROM inventory_items i
        WHERE i.item_id = %s AND i.quantity <= i.reorder_level
    """, (item_id,))
    item = cursor.fetchone()
    if not item:
        return None

    # Skip if pending PO already exists
    cursor.execute("""
        SELECT po.po_id FROM purchase_orders po
        JOIN purchase_order_items poi ON po.po_id = poi.po_id
        WHERE poi.item_id = %s
        AND po.status IN ('Pending','Approved','Ordered')
        LIMIT 1
    """, (item_id,))
    if cursor.fetchone():
        return None

    # Generate PO number
    cursor.execute("SELECT COUNT(*) AS cnt FROM purchase_orders")
    count     = cursor.fetchone()['cnt']
    po_number = f"AUTO-PO-{count + 1:04d}"
    subtotal  = item['reorder_quantity'] * float(item['unit_price'])

    cursor.execute("""
        INSERT INTO purchase_orders
            (po_number, supplier_id, ordered_by, order_date,
             expected_delivery, total_amount, status, remarks)
        VALUES (%s, %s, %s, CURDATE(),
                DATE_ADD(CURDATE(), INTERVAL 7 DAY),
                %s, 'Pending', %s)
    """, (po_number, item['supplier_id'], user_id,
          subtotal, f"Auto-reorder for {item['item_name']}"))

    po_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO purchase_order_items
            (po_id, item_id, quantity, received_quantity, unit_price, subtotal)
        VALUES (%s, %s, %s, 0, %s, %s)
    """, (po_id, item_id,
          item['reorder_quantity'], item['unit_price'], subtotal))

    cursor.execute("""
        INSERT INTO alerts (item_id, alert_type, severity, message)
        VALUES (%s, 'Reorder Required', 'High', %s)
    """, (item_id,
          f"Auto-reorder PO {po_number} created for "
          f"{item['item_name']} qty: {item['reorder_quantity']}"))

    return po_number


# ─────────────────────────────────────────────────────────────
# GET /api/stock/movements  — all movements
# ─────────────────────────────────────────────────────────────
@stock_bp.route('/movements', methods=['GET'])
def get_stock_movements():
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                sm.movement_id, sm.movement_type,
                sm.quantity, sm.previous_quantity, sm.new_quantity,
                sm.reference_type, sm.reference_id,
                sm.reason, sm.movement_date,
                i.item_id, i.item_code, i.item_name, i.unit,
                u.full_name AS performed_by,
                fd.department_name AS from_department,
                td.department_name AS to_department
            FROM stock_movements sm
            JOIN inventory_items i  ON sm.item_id = i.item_id
            JOIN users u            ON sm.user_id  = u.user_id
            LEFT JOIN departments fd ON sm.from_department_id = fd.department_id
            LEFT JOIN departments td ON sm.to_department_id   = td.department_id
            ORDER BY sm.movement_date DESC
        """)
        movements = cursor.fetchall()
        return jsonify({
            "success": True,
            "count"  : len(movements),
            "data"   : movements
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/stock/movements/<item_id>  — history for one item
# ─────────────────────────────────────────────────────────────
@stock_bp.route('/movements/<int:item_id>', methods=['GET'])
def get_item_movements(item_id):
    cursor = None
    try:
        cursor = get_cursor()

        # Verify item exists
        cursor.execute(
            "SELECT item_name FROM inventory_items WHERE item_id = %s",
            (item_id,))
        item = cursor.fetchone()
        if not item:
            return jsonify({"success": False,
                            "message": "Item not found"}), 404

        cursor.execute("""
            SELECT
                sm.movement_id, sm.movement_type,
                sm.quantity, sm.previous_quantity, sm.new_quantity,
                sm.reference_type, sm.reference_id,
                sm.reason, sm.movement_date,
                u.full_name AS performed_by,
                fd.department_name AS from_department,
                td.department_name AS to_department
            FROM stock_movements sm
            JOIN users u ON sm.user_id = u.user_id
            LEFT JOIN departments fd ON sm.from_department_id = fd.department_id
            LEFT JOIN departments td ON sm.to_department_id   = td.department_id
            WHERE sm.item_id = %s
            ORDER BY sm.movement_date DESC
        """, (item_id,))

        movements = cursor.fetchall()
        return jsonify({
            "success"  : True,
            "item_name": item['item_name'],
            "count"    : len(movements),
            "data"     : movements
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# POST /api/stock/in  — stock IN
# ─────────────────────────────────────────────────────────────
@stock_bp.route('/in', methods=['POST'])
def stock_in():
    cursor = None
    try:
        data = request.get_json()
        user = get_user_from_token(request)
        ip   = request.remote_addr

        # Validate
        if not data.get('item_id'):
            return jsonify({"success": False,
                            "message": "item_id is required"}), 400
        if not data.get('quantity') or int(data['quantity']) <= 0:
            return jsonify({"success": False,
                            "message": "quantity must be greater than 0"}), 400
        if not data.get('reason'):
            return jsonify({"success": False,
                            "message": "reason is required"}), 400

        cursor = get_cursor()

        # Fetch current stock
        cursor.execute("""
            SELECT item_id, item_name, item_code, quantity
            FROM inventory_items
            WHERE item_id = %s AND is_active = 'Yes'
        """, (data['item_id'],))
        item = cursor.fetchone()
        if not item:
            return jsonify({"success": False,
                            "message": "Item not found or inactive"}), 404

        previous_qty = item['quantity']
        new_qty      = previous_qty + int(data['quantity'])

        # Update inventory
        cursor.execute("""
            UPDATE inventory_items SET quantity = %s WHERE item_id = %s
        """, (new_qty, data['item_id']))

        # Stock movement record
        cursor.execute("""
            INSERT INTO stock_movements
                (item_id, movement_type, quantity,
                 previous_quantity, new_quantity,
                 reference_type, reference_id, user_id, reason)
            VALUES (%s, 'IN', %s, %s, %s, %s, %s, %s, %s)
        """, (
            data['item_id'], data['quantity'],
            previous_qty, new_qty,
            data.get('reference_type', 'Manual'),
            data.get('reference_id'),
            user['user_id'],
            data['reason']
        ))
        movement_id = cursor.lastrowid

        # Audit log
        write_audit(cursor, user['user_id'], 'IN', movement_id,
                    f"Stock IN: {item['item_name']} | "
                    f"{previous_qty} → {new_qty} "
                    f"(+{data['quantity']})", ip)

        # Low stock check (in case stock was previously low)
        check_low_stock(cursor, data['item_id'])

        # Auto reorder check
        po_number = check_auto_reorder(cursor, data['item_id'], user['user_id'])

        commit()
        return jsonify({
            "success"          : True,
            "message"          : "Stock added successfully",
            "movement_id"      : movement_id,
            "item_name"        : item['item_name'],
            "previous_quantity": previous_qty,
            "new_quantity"     : new_qty,
            "auto_reorder_po"  : po_number
        }), 201

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# POST /api/stock/out  — stock OUT
# ─────────────────────────────────────────────────────────────
@stock_bp.route('/out', methods=['POST'])
def stock_out():
    cursor = None
    try:
        data = request.get_json()
        user = get_user_from_token(request)
        ip   = request.remote_addr

        # Validate
        if not data.get('item_id'):
            return jsonify({"success": False,
                            "message": "item_id is required"}), 400
        if not data.get('quantity') or int(data['quantity']) <= 0:
            return jsonify({"success": False,
                            "message": "quantity must be greater than 0"}), 400
        if not data.get('reason'):
            return jsonify({"success": False,
                            "message": "reason is required"}), 400

        cursor = get_cursor()

        # Fetch current stock
        cursor.execute("""
            SELECT item_id, item_name, item_code,
                   quantity, minimum_stock, reorder_level
            FROM inventory_items
            WHERE item_id = %s AND is_active = 'Yes'
        """, (data['item_id'],))
        item = cursor.fetchone()
        if not item:
            return jsonify({"success": False,
                            "message": "Item not found or inactive"}), 404

        previous_qty = item['quantity']
        qty_out      = int(data['quantity'])

        # Insufficient stock check
        if previous_qty < qty_out:
            return jsonify({
                "success": False,
                "message": f"Insufficient stock. "
                           f"Available: {previous_qty}, "
                           f"Requested: {qty_out}"
            }), 400

        new_qty = previous_qty - qty_out

        # Update inventory
        cursor.execute("""
            UPDATE inventory_items SET quantity = %s WHERE item_id = %s
        """, (new_qty, data['item_id']))

        # Stock movement record
        cursor.execute("""
            INSERT INTO stock_movements
                (item_id, movement_type, quantity,
                 previous_quantity, new_quantity,
                 reference_type, reference_id, user_id, reason)
            VALUES (%s, 'OUT', %s, %s, %s, %s, %s, %s, %s)
        """, (
            data['item_id'], qty_out,
            previous_qty, new_qty,
            data.get('reference_type', 'Issue'),
            data.get('reference_id'),
            user['user_id'],
            data['reason']
        ))
        movement_id = cursor.lastrowid

        # Audit log
        write_audit(cursor, user['user_id'], 'OUT', movement_id,
                    f"Stock OUT: {item['item_name']} | "
                    f"{previous_qty} → {new_qty} "
                    f"(-{qty_out})", ip)

        # Low stock alert
        check_low_stock(cursor, data['item_id'])

        # Auto reorder
        po_number = check_auto_reorder(cursor, data['item_id'], user['user_id'])

        commit()
        return jsonify({
            "success"          : True,
            "message"          : "Stock issued successfully",
            "movement_id"      : movement_id,
            "item_name"        : item['item_name'],
            "previous_quantity": previous_qty,
            "new_quantity"     : new_qty,
            "auto_reorder_po"  : po_number
        }), 201

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# POST /api/stock/transfer  — transfer between departments
# ─────────────────────────────────────────────────────────────
@stock_bp.route('/transfer', methods=['POST'])
def stock_transfer():
    cursor = None
    try:
        data = request.get_json()
        user = get_user_from_token(request)
        ip   = request.remote_addr

        # Validate
        required = ['item_id', 'quantity',
                    'from_department_id', 'to_department_id', 'reason']
        for field in required:
            if not data.get(field):
                return jsonify({"success": False,
                                "message": f"{field} is required"}), 400

        if int(data['quantity']) <= 0:
            return jsonify({"success": False,
                            "message": "quantity must be greater than 0"}), 400

        if data['from_department_id'] == data['to_department_id']:
            return jsonify({"success": False,
                            "message": "Source and destination"
                                       " departments cannot be same"}), 400

        cursor = get_cursor()

        # Fetch item
        cursor.execute("""
            SELECT item_id, item_name, item_code, quantity
            FROM inventory_items
            WHERE item_id = %s AND is_active = 'Yes'
        """, (data['item_id'],))
        item = cursor.fetchone()
        if not item:
            return jsonify({"success": False,
                            "message": "Item not found or inactive"}), 404

        previous_qty = item['quantity']
        qty          = int(data['quantity'])

        if previous_qty < qty:
            return jsonify({
                "success": False,
                "message": f"Insufficient stock. "
                           f"Available: {previous_qty}, "
                           f"Requested: {qty}"
            }), 400

        # ⚠️ Transfer reduces quantity from source department
        # Total inventory quantity stays same (internal transfer)
        new_qty = previous_qty  # quantity unchanged at item level

        # Stock movement record
        cursor.execute("""
            INSERT INTO stock_movements
                (item_id, movement_type, quantity,
                 previous_quantity, new_quantity,
                 from_department_id, to_department_id,
                 reference_type, user_id, reason)
            VALUES (%s, 'TRANSFER', %s, %s, %s, %s, %s, 'Transfer', %s, %s)
        """, (
            data['item_id'], qty,
            previous_qty, new_qty,
            data['from_department_id'],
            data['to_department_id'],
            user['user_id'],
            data['reason']
        ))
        movement_id = cursor.lastrowid

        # Audit log
        write_audit(cursor, user['user_id'], 'TRANSFER', movement_id,
                    f"Transfer: {item['item_name']} | "
                    f"qty {qty} | "
                    f"dept {data['from_department_id']} → "
                    f"{data['to_department_id']}", ip)

        commit()
        return jsonify({
            "success"    : True,
            "message"    : "Stock transferred successfully",
            "movement_id": movement_id,
            "item_name"  : item['item_name'],
            "quantity"   : qty
        }), 201

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# POST /api/stock/adjustment  — manual stock correction
# ─────────────────────────────────────────────────────────────
@stock_bp.route('/adjustment', methods=['POST'])
def stock_adjustment():
    cursor = None
    try:
        data = request.get_json()
        user = get_user_from_token(request)
        ip   = request.remote_addr

        # Validate
        if not data.get('item_id'):
            return jsonify({"success": False,
                            "message": "item_id is required"}), 400
        if data.get('new_quantity') is None or int(data['new_quantity']) < 0:
            return jsonify({"success": False,
                            "message": "new_quantity must be 0 or more"}), 400
        if not data.get('reason'):
            return jsonify({"success": False,
                            "message": "reason is required"}), 400

        cursor = get_cursor()

        # Fetch current stock
        cursor.execute("""
            SELECT item_id, item_name, item_code, quantity
            FROM inventory_items
            WHERE item_id = %s AND is_active = 'Yes'
        """, (data['item_id'],))
        item = cursor.fetchone()
        if not item:
            return jsonify({"success": False,
                            "message": "Item not found or inactive"}), 404

        previous_qty   = item['quantity']
        new_qty        = int(data['new_quantity'])
        adjustment_qty = abs(new_qty - previous_qty)

        if previous_qty == new_qty:
            return jsonify({"success": False,
                            "message": "New quantity is same as current."
                                       " No adjustment needed."}), 400

        # Update inventory
        cursor.execute("""
            UPDATE inventory_items SET quantity = %s WHERE item_id = %s
        """, (new_qty, data['item_id']))

        # Stock movement
        cursor.execute("""
            INSERT INTO stock_movements
                (item_id, movement_type, quantity,
                 previous_quantity, new_quantity,
                 reference_type, user_id, reason)
            VALUES (%s, 'ADJUSTMENT', %s, %s, %s, 'Adjustment', %s, %s)
        """, (
            data['item_id'], adjustment_qty,
            previous_qty, new_qty,
            user['user_id'],
            data['reason']
        ))
        movement_id = cursor.lastrowid

        # Audit log
        write_audit(cursor, user['user_id'], 'ADJUSTMENT', movement_id,
                    f"Adjustment: {item['item_name']} | "
                    f"{previous_qty} → {new_qty} | "
                    f"diff: {'+' if new_qty > previous_qty else ''}"
                    f"{new_qty - previous_qty}", ip)

        # Low stock check
        check_low_stock(cursor, data['item_id'])

        # Auto reorder check
        po_number = check_auto_reorder(cursor, data['item_id'], user['user_id'])

        commit()
        return jsonify({
            "success"          : True,
            "message"          : "Stock adjusted successfully",
            "movement_id"      : movement_id,
            "item_name"        : item['item_name'],
            "previous_quantity": previous_qty,
            "new_quantity"     : new_qty,
            "adjustment"       : new_qty - previous_qty,
            "auto_reorder_po"  : po_number
        }), 201

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()