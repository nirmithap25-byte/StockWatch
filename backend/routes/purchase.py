# routes/purchase.py

from flask import Blueprint, request, jsonify
from database import get_cursor, commit, rollback
import jwt
import config

purchase_bp = Blueprint('purchase', __name__)


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
        VALUES (%s, 'Purchase', %s, 'purchase_orders', %s, %s, %s)
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
              f"{item['item_name']} below minimum stock "
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


# ── Helper: generate invoice on full receive ──────────────────
def generate_invoice(cursor, po_id, user_id):
    # Fetch PO + supplier snapshot
    cursor.execute("""
        SELECT po.po_id, po.po_number, po.total_amount,
               po.supplier_id,
               s.supplier_name, s.phone, s.email, s.address
        FROM purchase_orders po
        JOIN suppliers s ON po.supplier_id = s.supplier_id
        WHERE po.po_id = %s
    """, (po_id,))
    po = cursor.fetchone()
    if not po:
        return None

    # Check invoice doesn't already exist
    cursor.execute(
        "SELECT invoice_id FROM invoices WHERE po_id = %s", (po_id,))
    if cursor.fetchone():
        return None

    # Generate invoice number INV-YYYY-NNNN
    cursor.execute("SELECT COUNT(*) AS cnt FROM invoices")
    count          = cursor.fetchone()['cnt']
    invoice_number = f"INV-2026-{count + 1:04d}"

    # Insert invoice header
    cursor.execute("""
        INSERT INTO invoices
            (invoice_number, po_id, supplier_id,
             supplier_name, supplier_phone,
             supplier_email, supplier_address,
             total_amount, status, generated_by, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Finalized', %s, %s)
    """, (
        invoice_number, po['po_id'], po['supplier_id'],
        po['supplier_name'], po['phone'],
        po['email'], po['address'],
        po['total_amount'], user_id,
        f"Auto-generated on full receive of {po['po_number']}"
    ))
    invoice_id = cursor.lastrowid

    # Insert invoice line items (snapshot)
    cursor.execute("""
        SELECT poi.item_id, poi.quantity,
               poi.unit_price, poi.subtotal,
               i.item_code, i.item_name, i.unit
        FROM purchase_order_items poi
        JOIN inventory_items i ON poi.item_id = i.item_id
        WHERE poi.po_id = %s
    """, (po_id,))
    items = cursor.fetchall()

    for item in items:
        cursor.execute("""
            INSERT INTO invoice_items
                (invoice_id, item_id, item_code, item_name,
                 unit, quantity, unit_price, subtotal)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            invoice_id,
            item['item_id'], item['item_code'],
            item['item_name'], item['unit'],
            item['quantity'], item['unit_price'],
            item['subtotal']
        ))

    return invoice_number


# ─────────────────────────────────────────────────────────────
# GET /api/purchase/  — all purchase orders
# ─────────────────────────────────────────────────────────────
@purchase_bp.route('/', methods=['GET'])
def get_purchase_orders():
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                po.po_id, po.po_number, po.order_date,
                po.expected_delivery, po.total_amount,
                po.status, po.remarks, po.created_at,
                s.supplier_name,
                u.full_name AS ordered_by,
                ab.full_name AS approved_by
            FROM purchase_orders po
            JOIN suppliers s ON po.supplier_id = s.supplier_id
            JOIN users u     ON po.ordered_by  = u.user_id
            LEFT JOIN users ab ON po.approved_by = ab.user_id
            ORDER BY po.po_id DESC
        """)
        pos = cursor.fetchall()
        for po in pos:
            if po.get('total_amount'):
                po['total_amount'] = float(po['total_amount'])
        return jsonify({
            "success": True,
            "count"  : len(pos),
            "data"   : pos
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/purchase/search?keyword=  — search POs
# ─────────────────────────────────────────────────────────────
@purchase_bp.route('/search', methods=['GET'])
def search_purchase_orders():
    cursor = None
    try:
        keyword = request.args.get('keyword', '').strip()
        if not keyword:
            return jsonify({"success": False,
                            "message": "keyword is required"}), 400

        like = f"%{keyword}%"
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                po.po_id, po.po_number, po.order_date,
                po.total_amount, po.status,
                s.supplier_name,
                u.full_name AS ordered_by
            FROM purchase_orders po
            JOIN suppliers s ON po.supplier_id = s.supplier_id
            JOIN users u     ON po.ordered_by  = u.user_id
            WHERE po.po_number     LIKE %s
               OR s.supplier_name  LIKE %s
               OR po.status        LIKE %s
            ORDER BY po.po_id DESC
        """, (like, like, like))

        pos = cursor.fetchall()
        for po in pos:
            if po.get('total_amount'):
                po['total_amount'] = float(po['total_amount'])

        return jsonify({
            "success": True,
            "count"  : len(pos),
            "data"   : pos
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/purchase/<po_id>  — single PO with items
# ─────────────────────────────────────────────────────────────
@purchase_bp.route('/<int:po_id>', methods=['GET'])
def get_purchase_order(po_id):
    cursor = None
    try:
        cursor = get_cursor()

        # PO header
        cursor.execute("""
            SELECT
                po.po_id, po.po_number, po.order_date,
                po.expected_delivery, po.approved_date,
                po.total_amount, po.status, po.remarks,
                po.created_at,
                s.supplier_id, s.supplier_name,
                s.phone AS supplier_phone,
                s.email AS supplier_email,
                u.full_name  AS ordered_by,
                ab.full_name AS approved_by
            FROM purchase_orders po
            JOIN suppliers s ON po.supplier_id = s.supplier_id
            JOIN users u     ON po.ordered_by  = u.user_id
            LEFT JOIN users ab ON po.approved_by = ab.user_id
            WHERE po.po_id = %s
        """, (po_id,))
        po = cursor.fetchone()

        if not po:
            return jsonify({"success": False,
                            "message": "Purchase order not found"}), 404

        if po.get('total_amount'):
            po['total_amount'] = float(po['total_amount'])

        # PO line items
        cursor.execute("""
            SELECT
                poi.po_item_id, poi.item_id,
                poi.quantity, poi.received_quantity,
                poi.unit_price, poi.subtotal,
                i.item_code, i.item_name, i.unit
            FROM purchase_order_items poi
            JOIN inventory_items i ON poi.item_id = i.item_id
            WHERE poi.po_id = %s
        """, (po_id,))
        items = cursor.fetchall()
        for item in items:
            item['unit_price'] = float(item['unit_price'])
            item['subtotal']   = float(item['subtotal'])

        return jsonify({
            "success"        : True,
            "purchase_order" : po,
            "items"          : items
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# POST /api/purchase/create  — create new PO
# ─────────────────────────────────────────────────────────────
@purchase_bp.route('/create', methods=['POST'])
def create_purchase_order():
    cursor = None
    try:
        data = request.get_json()
        user = get_user_from_token(request)
        ip   = request.remote_addr

        # Validate header
        required = ['supplier_id', 'order_date', 'items']
        for field in required:
            if not data.get(field):
                return jsonify({"success": False,
                                "message": f"{field} is required"}), 400

        items = data['items']
        if not isinstance(items, list) or len(items) == 0:
            return jsonify({"success": False,
                            "message": "At least one item is required"}), 400

        cursor = get_cursor()

        # Validate supplier exists
        cursor.execute(
            "SELECT supplier_id FROM suppliers WHERE supplier_id = %s",
            (data['supplier_id'],))
        if not cursor.fetchone():
            return jsonify({"success": False,
                            "message": "Supplier not found"}), 404

        # Validate items and calculate total
        total_amount = 0
        for item in items:
            if not item.get('item_id') or not item.get('quantity') \
                    or not item.get('unit_price'):
                return jsonify({"success": False,
                                "message": "Each item needs "
                                           "item_id, quantity, unit_price"}), 400
            if int(item['quantity']) <= 0:
                return jsonify({"success": False,
                                "message": "Item quantity must be > 0"}), 400
            if float(item['unit_price']) <= 0:
                return jsonify({"success": False,
                                "message": "Unit price must be > 0"}), 400

            # Verify item exists
            cursor.execute(
                "SELECT item_id FROM inventory_items WHERE item_id = %s",
                (item['item_id'],))
            if not cursor.fetchone():
                return jsonify({"success": False,
                                "message": f"Item {item['item_id']} "
                                           f"not found"}), 404

            total_amount += int(item['quantity']) * float(item['unit_price'])

        # Generate clean PO number: PO-YYYY-NNNN
        cursor.execute("SELECT COUNT(*) AS cnt FROM purchase_orders")
        count     = cursor.fetchone()['cnt']
        po_number = f"PO-2026-{count + 1:04d}"

        # Insert PO header
        cursor.execute("""
            INSERT INTO purchase_orders
                (po_number, supplier_id, ordered_by, order_date,
                 expected_delivery, total_amount, status, remarks)
            VALUES (%s, %s, %s, %s, %s, %s, 'Pending', %s)
        """, (
            po_number,
            data['supplier_id'],
            user['user_id'],
            data['order_date'],
            data.get('expected_delivery'),
            total_amount,
            data.get('remarks', '')
        ))
        po_id = cursor.lastrowid

        # Insert PO items
        for item in items:
            subtotal = int(item['quantity']) * float(item['unit_price'])
            cursor.execute("""
                INSERT INTO purchase_order_items
                    (po_id, item_id, quantity, received_quantity,
                     unit_price, subtotal)
                VALUES (%s, %s, %s, 0, %s, %s)
            """, (
                po_id, item['item_id'],
                item['quantity'], item['unit_price'],
                subtotal
            ))

        # Audit log
        write_audit(cursor, user['user_id'], 'CREATE', po_id,
                    f"PO {po_number} created with "
                    f"{len(items)} item(s), "
                    f"total ₹{total_amount:.2f}", ip)

        commit()
        return jsonify({
            "success"     : True,
            "message"     : "Purchase order created successfully",
            "po_id"       : po_id,
            "po_number"   : po_number,
            "total_amount": total_amount
        }), 201

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# PUT /api/purchase/<po_id>/approve  — approve PO
# ─────────────────────────────────────────────────────────────
@purchase_bp.route('/<int:po_id>/approve', methods=['PUT'])
def approve_purchase_order(po_id):
    cursor = None
    try:
        user = get_user_from_token(request)
        ip   = request.remote_addr

        cursor = get_cursor()

        cursor.execute("""
            SELECT po_number, status, ordered_by
            FROM purchase_orders WHERE po_id = %s
        """, (po_id,))
        po = cursor.fetchone()

        if not po:
            return jsonify({"success": False,
                            "message": "Purchase order not found"}), 404

        if po['status'] != 'Pending':
            return jsonify({"success": False,
                            "message": f"Cannot approve. "
                                       f"Current status: {po['status']}"}), 400

        # Approver cannot be same as creator
        if user['user_id'] == po['ordered_by']:
            return jsonify({"success": False,
                            "message": "You cannot approve your "
                                       "own purchase order"}), 403

        cursor.execute("""
            UPDATE purchase_orders
            SET status = 'Approved',
                approved_by = %s,
                approved_date = NOW()
            WHERE po_id = %s
        """, (user['user_id'], po_id))

        write_audit(cursor, user['user_id'], 'APPROVE', po_id,
                    f"PO {po['po_number']} approved", ip)

        commit()
        return jsonify({
            "success": True,
            "message": f"PO {po['po_number']} approved successfully"
        }), 200

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# PUT /api/purchase/<po_id>/cancel  — cancel PO
# ─────────────────────────────────────────────────────────────
@purchase_bp.route('/<int:po_id>/cancel', methods=['PUT'])
def cancel_purchase_order(po_id):
    cursor = None
    try:
        data   = request.get_json() or {}
        user   = get_user_from_token(request)
        ip     = request.remote_addr
        reason = data.get('reason', 'No reason provided')

        cursor = get_cursor()

        cursor.execute("""
            SELECT po_number, status
            FROM purchase_orders WHERE po_id = %s
        """, (po_id,))
        po = cursor.fetchone()

        if not po:
            return jsonify({"success": False,
                            "message": "Purchase order not found"}), 404

        # Cannot cancel if already received or cancelled
        if po['status'] in ('Cancelled', 'Received'):
            return jsonify({"success": False,
                            "message": f"Cannot cancel a "
                                       f"{po['status']} order"}), 400

        cursor.execute("""
            UPDATE purchase_orders
            SET status = 'Cancelled', remarks = %s
            WHERE po_id = %s
        """, (f"Cancelled: {reason}", po_id))

        write_audit(cursor, user['user_id'], 'CANCEL', po_id,
                    f"PO {po['po_number']} cancelled. "
                    f"Reason: {reason}", ip)

        commit()
        return jsonify({
            "success": True,
            "message": f"PO {po['po_number']} cancelled successfully"
        }), 200

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# PUT /api/purchase/<po_id>/receive  — receive PO (partial + full)
# ─────────────────────────────────────────────────────────────
@purchase_bp.route('/<int:po_id>/receive', methods=['PUT'])
def receive_purchase_order(po_id):
    cursor = None
    try:
        data  = request.get_json()
        user  = get_user_from_token(request)
        ip    = request.remote_addr

        # items = [{"po_item_id": 1, "received_qty": 5}, ...]
        items = data.get('items', [])
        if not items:
            return jsonify({"success": False,
                            "message": "items list is required"}), 400

        cursor = get_cursor()

        # Validate PO status
        cursor.execute("""
            SELECT po_number, status
            FROM purchase_orders WHERE po_id = %s
        """, (po_id,))
        po = cursor.fetchone()

        if not po:
            return jsonify({"success": False,
                            "message": "Purchase order not found"}), 404

        if po['status'] in ('Cancelled', 'Received'):
            return jsonify({"success": False,
                            "message": f"Cannot receive a "
                                       f"{po['status']} order"}), 400

        if po['status'] == 'Pending':
            return jsonify({"success": False,
                            "message": "PO must be Approved "
                                       "before receiving"}), 400

        received_summary = []

        for receive_item in items:
            po_item_id   = receive_item.get('po_item_id')
            received_qty = int(receive_item.get('received_qty', 0))

            if not po_item_id or received_qty <= 0:
                continue

            # Fetch PO item
            cursor.execute("""
                SELECT poi.po_item_id, poi.item_id,
                       poi.quantity, poi.received_quantity,
                       poi.unit_price,
                       i.item_name, i.item_code
                FROM purchase_order_items poi
                JOIN inventory_items i ON poi.item_id = i.item_id
                WHERE poi.po_item_id = %s AND poi.po_id = %s
            """, (po_item_id, po_id))
            po_item = cursor.fetchone()

            if not po_item:
                continue

            # Cannot receive more than ordered
            remaining = po_item['quantity'] - po_item['received_quantity']
            if received_qty > remaining:
                return jsonify({
                    "success": False,
                    "message": f"{po_item['item_name']}: "
                               f"Cannot receive {received_qty}. "
                               f"Remaining: {remaining}"
                }), 400

            # Update received_quantity on PO item
            new_received = po_item['received_quantity'] + received_qty
            cursor.execute("""
                UPDATE purchase_order_items
                SET received_quantity = %s
                WHERE po_item_id = %s
            """, (new_received, po_item_id))

            # Update inventory_items quantity
            cursor.execute("""
                SELECT quantity FROM inventory_items
                WHERE item_id = %s
            """, (po_item['item_id'],))
            inv = cursor.fetchone()
            prev_qty = inv['quantity']
            new_qty  = prev_qty + received_qty

            cursor.execute("""
                UPDATE inventory_items SET quantity = %s
                WHERE item_id = %s
            """, (new_qty, po_item['item_id']))

            # Insert stock movement
            cursor.execute("""
                INSERT INTO stock_movements
                    (item_id, movement_type, quantity,
                     previous_quantity, new_quantity,
                     reference_type, reference_id,
                     user_id, reason)
                VALUES (%s, 'IN', %s, %s, %s,
                        'Purchase', %s, %s, %s)
            """, (
                po_item['item_id'], received_qty,
                prev_qty, new_qty,
                po_id, user['user_id'],
                f"Received from PO {po['po_number']}"
            ))

            # Low stock check after receive
            check_low_stock(cursor, po_item['item_id'])

            received_summary.append({
                "item_name"    : po_item['item_name'],
                "received_qty" : received_qty,
                "new_quantity" : new_qty
            })

        # Determine PO status: Fully or Partially received
        cursor.execute("""
            SELECT SUM(quantity)          AS total_ordered,
                   SUM(received_quantity) AS total_received
            FROM purchase_order_items
            WHERE po_id = %s
        """, (po_id,))
        totals = cursor.fetchone()

        if totals['total_received'] >= totals['total_ordered']:
            new_po_status = 'Received'
        else:
            new_po_status = 'Partially Received'

        cursor.execute("""
            UPDATE purchase_orders SET status = %s WHERE po_id = %s
        """, (new_po_status, po_id))

        # Auto generate invoice on full receive
        invoice_number = None
        if new_po_status == 'Received':
            invoice_number = generate_invoice(cursor, po_id, user['user_id'])

        # Audit log
        write_audit(cursor, user['user_id'], 'RECEIVE', po_id,
                    f"PO {po['po_number']} — "
                    f"{new_po_status}. "
                    f"Invoice: {invoice_number or 'N/A'}", ip)

        commit()
        return jsonify({
            "success"        : True,
            "message"        : f"PO {new_po_status} successfully",
            "po_status"      : new_po_status,
            "invoice_number" : invoice_number,
            "received_items" : received_summary
        }), 200

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()