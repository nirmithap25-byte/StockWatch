# routes/qr.py

from flask import Blueprint, request, jsonify
from database import get_cursor, commit, rollback
import jwt
import config

qr_bp = Blueprint("qr", __name__)


# ── Helper: extract user from JWT ─────────────────────────────
def get_user_from_token(req):
    try:
        token = req.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return {"user_id": 1, "role": "Admin"}
        return jwt.decode(token, config.SECRET_KEY, algorithms=['HS256'])
    except Exception:
        return {"user_id": 1, "role": "Admin"}


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


# ─────────────────────────────────────────────────────────────
# GET /api/qr/scan/<qr_code>  — get item details by QR code
# ─────────────────────────────────────────────────────────────
@qr_bp.route("/scan/<string:qr_code>", methods=["GET"])
def scan_qr(qr_code):
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                i.item_id, i.item_code, i.item_name, i.description,
                i.quantity, i.minimum_stock, i.reorder_level,
                i.reorder_quantity, i.unit, i.unit_price,
                i.qr_code, i.is_active,
                c.category_name,
                s.supplier_name,
                d.department_name
            FROM inventory_items i
            JOIN categories  c ON i.category_id  = c.category_id
            JOIN suppliers   s ON i.supplier_id   = s.supplier_id
            JOIN departments d ON i.department_id = d.department_id
            WHERE i.qr_code = %s AND i.is_active = 'Yes'
        """, (qr_code,))
        item = cursor.fetchone()

        if not item:
            return jsonify({"success": False,
                            "message": "Invalid QR code or item is inactive"}), 404

        item['unit_price'] = float(item['unit_price'])

        # Stock status label
        if item['quantity'] == 0:
            stock_status = "Out of Stock"
        elif item['quantity'] <= item['minimum_stock']:
            stock_status = "Critical"
        elif item['quantity'] <= item['reorder_level']:
            stock_status = "Low"
        else:
            stock_status = "Available"

        item['stock_status'] = stock_status

        return jsonify({"success": True, "message": "Item found", "item": item}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# POST /api/qr/stock-in  — QR-triggered stock IN
# ─────────────────────────────────────────────────────────────
@qr_bp.route("/stock-in", methods=["POST"])
def qr_stock_in():
    cursor = None
    try:
        data = request.get_json()
        ip   = request.remote_addr

        required = ["qr_code", "quantity", "user_id", "reason"]
        for field in required:
            if not data.get(field) and data.get(field) != 0:
                return jsonify({"success": False,
                                "message": f"{field} is required"}), 400

        if int(data["quantity"]) <= 0:
            return jsonify({"success": False,
                            "message": "Quantity must be greater than 0"}), 400

        cursor = get_cursor()

        # Find item by QR code
        cursor.execute("""
            SELECT item_id, item_name, quantity
            FROM inventory_items
            WHERE qr_code = %s AND is_active = 'Yes'
        """, (data["qr_code"],))
        item = cursor.fetchone()

        if not item:
            return jsonify({"success": False,
                            "message": "Invalid QR code or item is inactive"}), 404

        previous_qty = item['quantity']
        new_qty      = previous_qty + int(data["quantity"])

        # Update inventory
        cursor.execute("""
            UPDATE inventory_items SET quantity = %s WHERE item_id = %s
        """, (new_qty, item['item_id']))

        # Stock movement
        cursor.execute("""
            INSERT INTO stock_movements
                (item_id, movement_type, quantity,
                 previous_quantity, new_quantity,
                 reference_type, user_id, reason)
            VALUES (%s, 'IN', %s, %s, %s, 'Manual', %s, %s)
        """, (item['item_id'], data["quantity"],
              previous_qty, new_qty,
              data["user_id"], data["reason"]))
        movement_id = cursor.lastrowid

        # Low stock check (in case stock was critically low before)
        check_low_stock(cursor, item['item_id'])

        # Audit log
        cursor.execute("""
            INSERT INTO audit_logs
                (user_id, module, action, table_name, record_id, description, ip_address)
            VALUES (%s, 'QR Stock', 'IN', 'stock_movements', %s, %s, %s)
        """, (data["user_id"], movement_id,
              f"QR Stock IN — '{item['item_name']}' qty: {data['quantity']}", ip))

        commit()
        return jsonify({
            "success"          : True,
            "message"          : f"Stock IN successful for '{item['item_name']}'",
            "item_id"          : item['item_id'],
            "item_name"        : item['item_name'],
            "movement_id"      : movement_id,
            "previous_quantity": previous_qty,
            "new_quantity"     : new_qty
        }), 201

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# POST /api/qr/stock-out  — QR-triggered stock OUT
# ─────────────────────────────────────────────────────────────
@qr_bp.route("/stock-out", methods=["POST"])
def qr_stock_out():
    cursor = None
    try:
        data = request.get_json()
        ip   = request.remote_addr

        required = ["qr_code", "quantity", "user_id", "reason"]
        for field in required:
            if not data.get(field) and data.get(field) != 0:
                return jsonify({"success": False,
                                "message": f"{field} is required"}), 400

        if int(data["quantity"]) <= 0:
            return jsonify({"success": False,
                            "message": "Quantity must be greater than 0"}), 400

        cursor = get_cursor()

        # Find item by QR code
        cursor.execute("""
            SELECT item_id, item_name, quantity
            FROM inventory_items
            WHERE qr_code = %s AND is_active = 'Yes'
        """, (data["qr_code"],))
        item = cursor.fetchone()

        if not item:
            return jsonify({"success": False,
                            "message": "Invalid QR code or item is inactive"}), 404

        previous_qty = item['quantity']

        if int(data["quantity"]) > previous_qty:
            return jsonify({
                "success": False,
                "message": f"Insufficient stock. "
                           f"Available: {previous_qty}, "
                           f"Requested: {data['quantity']}"
            }), 400

        new_qty = previous_qty - int(data["quantity"])

        # Update inventory
        cursor.execute("""
            UPDATE inventory_items SET quantity = %s WHERE item_id = %s
        """, (new_qty, item['item_id']))

        # Stock movement
        cursor.execute("""
            INSERT INTO stock_movements
                (item_id, movement_type, quantity,
                 previous_quantity, new_quantity,
                 reference_type, user_id, reason)
            VALUES (%s, 'OUT', %s, %s, %s, 'Manual', %s, %s)
        """, (item['item_id'], data["quantity"],
              previous_qty, new_qty,
              data["user_id"], data["reason"]))
        movement_id = cursor.lastrowid

        # Low stock alert after OUT
        check_low_stock(cursor, item['item_id'])

        # Audit log
        cursor.execute("""
            INSERT INTO audit_logs
                (user_id, module, action, table_name, record_id, description, ip_address)
            VALUES (%s, 'QR Stock', 'OUT', 'stock_movements', %s, %s, %s)
        """, (data["user_id"], movement_id,
              f"QR Stock OUT — '{item['item_name']}' qty: {data['quantity']}", ip))

        commit()
        return jsonify({
            "success"          : True,
            "message"          : f"Stock OUT successful for '{item['item_name']}'",
            "item_id"          : item['item_id'],
            "item_name"        : item['item_name'],
            "movement_id"      : movement_id,
            "previous_quantity": previous_qty,
            "new_quantity"     : new_qty
        }), 201

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/qr/generate/<qr_code>  — generate QR image
# ─────────────────────────────────────────────────────────────
@qr_bp.route("/generate/<string:qr_code>", methods=["GET"])
def generate_qr(qr_code):
    cursor = None
    try:
        import qrcode
        import io
        from flask import send_file

        cursor = get_cursor()
        cursor.execute("""
            SELECT item_id, item_name
            FROM inventory_items
            WHERE qr_code = %s AND is_active = 'Yes'
        """, (qr_code,))
        item = cursor.fetchone()

        if not item:
            return jsonify({"success": False, "message": "Item not found"}), 404

        # Generate QR code image
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4
        )
        qr.add_data(qr_code)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        return send_file(
            buf,
            mimetype="image/png",
            as_attachment=False,
            download_name=f"{qr_code}.png"
        )

    except ImportError:
        return jsonify({
            "success": False,
            "message": "qrcode library not installed. Run: pip install qrcode[pil]"
        }), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
