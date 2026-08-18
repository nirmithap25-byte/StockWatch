# routes/approvals.py

from flask import Blueprint, request, jsonify
from database import get_cursor, commit, rollback
import jwt
import config

approvals_bp = Blueprint("approvals", __name__)


# ── Helper: extract user from JWT ─────────────────────────────
def get_user_from_token(req):
    try:
        token = req.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return {"user_id": 1, "role": "Admin"}
        return jwt.decode(token, config.SECRET_KEY, algorithms=['HS256'])
    except Exception:
        return {"user_id": 1, "role": "Admin"}


# ── Helper: low stock alert + auto reorder ────────────────────
def check_low_stock_and_reorder(cursor, item_id):
    cursor.execute("""
        SELECT item_name, quantity, minimum_stock, reorder_level,
               reorder_quantity, supplier_id, unit_price
        FROM inventory_items
        WHERE item_id = %s AND is_active = 'Yes'
    """, (item_id,))
    item = cursor.fetchone()
    if not item:
        return

    quantity = item['quantity']

    if quantity <= item['reorder_level']:
        # Low stock alert (avoid duplicates)
        cursor.execute("""
            SELECT alert_id FROM alerts
            WHERE item_id = %s AND status = 'Unread' AND alert_type = 'Low Stock'
        """, (item_id,))
        if not cursor.fetchone():
            severity = 'High' if quantity == 0 else 'Medium'
            cursor.execute("""
                INSERT INTO alerts (item_id, alert_type, severity, message)
                VALUES (%s, 'Low Stock', %s, %s)
            """, (item_id, severity,
                  f"{item['item_name']} is below reorder level. "
                  f"Current stock: {quantity}."))

        # Auto reorder PO (avoid duplicates)
        cursor.execute("""
            SELECT po.po_id FROM purchase_orders po
            JOIN purchase_order_items poi ON po.po_id = poi.po_id
            WHERE poi.item_id = %s AND po.status = 'Pending'
            LIMIT 1
        """, (item_id,))
        if not cursor.fetchone():
            from datetime import datetime
            po_number    = "AUTO-PO-" + datetime.now().strftime("%Y%m%d%H%M%S")
            total_amount = float(item['reorder_quantity']) * float(item['unit_price'])
            order_date   = datetime.now().strftime("%Y-%m-%d")

            cursor.execute("""
                INSERT INTO purchase_orders
                    (po_number, supplier_id, ordered_by, order_date,
                     total_amount, status, remarks)
                VALUES (%s, %s, 1, %s, %s, 'Pending', %s)
            """, (po_number, item['supplier_id'], order_date, total_amount,
                  f"Auto-generated PO for low stock: {item['item_name']}"))
            po_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO purchase_order_items
                    (po_id, item_id, quantity, received_quantity, unit_price, subtotal)
                VALUES (%s, %s, %s, 0, %s, %s)
            """, (po_id, item_id, item['reorder_quantity'],
                  item['unit_price'], total_amount))

            cursor.execute("""
                INSERT INTO alerts (item_id, alert_type, severity, message)
                VALUES (%s, 'Reorder Required', 'High', %s)
            """, (item_id,
                  f"Auto PO {po_number} created for '{item['item_name']}'. "
                  f"Awaiting manager approval."))

            cursor.execute("""
                INSERT INTO audit_logs
                    (user_id, module, action, table_name, record_id, description, ip_address)
                VALUES (1, 'Purchase Order', 'AUTO-CREATE', 'purchase_orders', %s, %s, 'system')
            """, (po_id,
                  f"Auto PO {po_number} created for low stock item "
                  f"'{item['item_name']}'."))


# ─────────────────────────────────────────────────────────────
# GET /api/approvals/  — all approvals
# ─────────────────────────────────────────────────────────────
@approvals_bp.route("/", methods=["GET"])
def get_all_approvals():
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                a.approval_id,
                i.item_code,
                i.item_name,
                i.quantity AS available_stock,
                u1.full_name AS requested_by,
                u2.full_name AS approved_by,
                a.quantity   AS requested_quantity,
                a.purpose,
                a.status,
                a.comments,
                a.request_date,
                a.approval_date
            FROM approvals a
            JOIN inventory_items i  ON a.item_id      = i.item_id
            JOIN users u1           ON a.requested_by = u1.user_id
            LEFT JOIN users u2      ON a.approved_by  = u2.user_id
            ORDER BY a.request_date DESC
        """)
        data = cursor.fetchall()
        return jsonify({"success": True, "count": len(data), "approvals": data}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/approvals/pending  — pending approvals (for manager)
# ─────────────────────────────────────────────────────────────
@approvals_bp.route("/pending", methods=["GET"])
def get_pending_approvals():
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                a.approval_id,
                i.item_code,
                i.item_name,
                i.quantity AS available_stock,
                u1.full_name AS requested_by,
                a.quantity   AS requested_quantity,
                a.purpose,
                a.status,
                a.request_date
            FROM approvals a
            JOIN inventory_items i ON a.item_id      = i.item_id
            JOIN users u1          ON a.requested_by = u1.user_id
            WHERE a.status = 'Pending'
            ORDER BY a.request_date ASC
        """)
        data = cursor.fetchall()
        return jsonify({
            "success"          : True,
            "count"            : len(data),
            "pending_approvals": data
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/approvals/<id>  — single approval
# ─────────────────────────────────────────────────────────────
@approvals_bp.route("/<int:approval_id>", methods=["GET"])
def get_approval(approval_id):
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                a.approval_id,
                i.item_id, i.item_code, i.item_name,
                i.quantity AS available_stock, i.unit,
                u1.full_name AS requested_by,
                u2.full_name AS approved_by,
                a.quantity   AS requested_quantity,
                a.purpose, a.status, a.comments,
                a.request_date, a.approval_date
            FROM approvals a
            JOIN inventory_items i ON a.item_id      = i.item_id
            JOIN users u1          ON a.requested_by = u1.user_id
            LEFT JOIN users u2     ON a.approved_by  = u2.user_id
            WHERE a.approval_id = %s
        """, (approval_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"success": False, "message": "Approval not found"}), 404
        return jsonify({"success": True, "approval": row}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# POST /api/approvals/request  — employee raises stock request
# ─────────────────────────────────────────────────────────────
@approvals_bp.route("/request", methods=["POST"])
def request_stock():
    cursor = None
    try:
        data = request.get_json()
        ip   = request.remote_addr

        required = ["item_id", "requested_by", "quantity", "purpose"]
        for field in required:
            if not data.get(field) and data.get(field) != 0:
                return jsonify({"success": False,
                                "message": f"{field} is required"}), 400

        if int(data["quantity"]) <= 0:
            return jsonify({"success": False,
                            "message": "Quantity must be greater than 0"}), 400

        cursor = get_cursor()

        # Check item exists and is active
        cursor.execute("""
            SELECT item_name, quantity FROM inventory_items
            WHERE item_id = %s AND is_active = 'Yes'
        """, (data["item_id"],))
        item = cursor.fetchone()
        if not item:
            return jsonify({"success": False,
                            "message": "Item not found or inactive"}), 404

        if int(data["quantity"]) > item['quantity']:
            return jsonify({
                "success": False,
                "message": f"Requested quantity {data['quantity']} "
                           f"exceeds available stock {item['quantity']}"
            }), 400

        # Check user exists
        cursor.execute("""
            SELECT full_name FROM users
            WHERE user_id = %s AND status = 'Active'
        """, (data["requested_by"],))
        if not cursor.fetchone():
            return jsonify({"success": False,
                            "message": "User not found or inactive"}), 404

        # Insert approval request
        cursor.execute("""
            INSERT INTO approvals
                (item_id, requested_by, quantity, purpose, status)
            VALUES (%s, %s, %s, %s, 'Pending')
        """, (data["item_id"], data["requested_by"],
              data["quantity"], data["purpose"]))
        approval_id = cursor.lastrowid

        # Audit log
        cursor.execute("""
            INSERT INTO audit_logs
                (user_id, module, action, table_name, record_id, description, ip_address)
            VALUES (%s, 'Approvals', 'REQUEST', 'approvals', %s, %s, %s)
        """, (data["requested_by"], approval_id,
              f"Stock request for '{item['item_name']}' "
              f"qty: {data['quantity']} — {data['purpose']}", ip))

        commit()
        return jsonify({
            "success"    : True,
            "message"    : "Stock request raised successfully. Awaiting manager approval.",
            "approval_id": approval_id
        }), 201

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# PUT /api/approvals/<id>/approve  — manager approves → auto stock OUT
# ─────────────────────────────────────────────────────────────
@approvals_bp.route("/<int:approval_id>/approve", methods=["PUT"])
def approve_request(approval_id):
    cursor = None
    try:
        data        = request.get_json()
        approved_by = data.get("approved_by")
        comments    = data.get("comments", "Approved")
        ip          = request.remote_addr

        if not approved_by:
            return jsonify({"success": False,
                            "message": "approved_by is required"}), 400

        cursor = get_cursor()

        # Get approval details
        cursor.execute("""
            SELECT
                a.item_id, a.requested_by, a.quantity,
                a.purpose, a.status,
                i.item_name, i.quantity AS current_stock
            FROM approvals a
            JOIN inventory_items i ON a.item_id = i.item_id
            WHERE a.approval_id = %s
        """, (approval_id,))
        approval = cursor.fetchone()

        if not approval:
            return jsonify({"success": False,
                            "message": "Approval request not found"}), 404

        if approval['status'] != "Pending":
            return jsonify({"success": False,
                            "message": f"Cannot approve. "
                                       f"Request is already '{approval['status']}'"}), 400

        qty           = approval['quantity']
        current_stock = approval['current_stock']

        if qty > current_stock:
            return jsonify({
                "success": False,
                "message": f"Insufficient stock. "
                           f"Available: {current_stock}, Requested: {qty}"
            }), 400

        # Update approval status
        cursor.execute("""
            UPDATE approvals
            SET status = 'Approved', approved_by = %s,
                comments = %s, approval_date = NOW()
            WHERE approval_id = %s
        """, (approved_by, comments, approval_id))

        # Auto Stock OUT
        previous_qty = current_stock
        new_qty      = current_stock - qty

        cursor.execute("""
            UPDATE inventory_items SET quantity = %s WHERE item_id = %s
        """, (new_qty, approval['item_id']))

        cursor.execute("""
            INSERT INTO stock_movements
                (item_id, movement_type, quantity,
                 previous_quantity, new_quantity,
                 reference_type, reference_id, user_id, reason)
            VALUES (%s, 'OUT', %s, %s, %s, 'Issue', %s, %s, %s)
        """, (approval['item_id'], qty, previous_qty, new_qty,
              approval_id, approved_by,
              f"Stock issued for approval — {approval['purpose']}"))
        movement_id = cursor.lastrowid

        # Check low stock + auto reorder after stock OUT
        check_low_stock_and_reorder(cursor, approval['item_id'])

        # Audit log
        cursor.execute("""
            INSERT INTO audit_logs
                (user_id, module, action, table_name, record_id, description, ip_address)
            VALUES (%s, 'Approvals', 'APPROVE', 'approvals', %s, %s, %s)
        """, (approved_by, approval_id,
              f"Approved stock request for '{approval['item_name']}' "
              f"qty: {qty}. Movement ID: {movement_id}", ip))

        commit()
        return jsonify({
            "success"       : True,
            "message"       : f"{qty} units of '{approval['item_name']}' issued successfully.",
            "approval_id"   : approval_id,
            "movement_id"   : movement_id,
            "previous_stock": previous_qty,
            "current_stock" : new_qty
        }), 200

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# PUT /api/approvals/<id>/reject  — manager rejects
# ─────────────────────────────────────────────────────────────
@approvals_bp.route("/<int:approval_id>/reject", methods=["PUT"])
def reject_request(approval_id):
    cursor = None
    try:
        data        = request.get_json()
        approved_by = data.get("approved_by")
        comments    = data.get("comments", "Rejected")
        ip          = request.remote_addr

        if not approved_by:
            return jsonify({"success": False,
                            "message": "approved_by is required"}), 400

        cursor = get_cursor()

        cursor.execute("""
            SELECT a.status, i.item_name, a.quantity
            FROM approvals a
            JOIN inventory_items i ON a.item_id = i.item_id
            WHERE a.approval_id = %s
        """, (approval_id,))
        approval = cursor.fetchone()

        if not approval:
            return jsonify({"success": False,
                            "message": "Approval request not found"}), 404

        if approval['status'] != "Pending":
            return jsonify({"success": False,
                            "message": f"Cannot reject. "
                                       f"Request is already '{approval['status']}'"}), 400

        cursor.execute("""
            UPDATE approvals
            SET status = 'Rejected', approved_by = %s,
                comments = %s, approval_date = NOW()
            WHERE approval_id = %s
        """, (approved_by, comments, approval_id))

        cursor.execute("""
            INSERT INTO audit_logs
                (user_id, module, action, table_name, record_id, description, ip_address)
            VALUES (%s, 'Approvals', 'REJECT', 'approvals', %s, %s, %s)
        """, (approved_by, approval_id,
              f"Rejected stock request for '{approval['item_name']}' "
              f"qty: {approval['quantity']} — {comments}", ip))

        commit()
        return jsonify({
            "success"    : True,
            "message"    : f"Stock request for '{approval['item_name']}' rejected.",
            "approval_id": approval_id
        }), 200

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
