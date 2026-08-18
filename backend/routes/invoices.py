# routes/invoices.py

from flask import Blueprint, request, jsonify
from database import get_cursor, commit, rollback
import jwt
import config

invoice_bp = Blueprint('invoice', __name__)


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
        VALUES (%s, 'Invoice', %s, 'invoices', %s, %s, %s)
    """, (user_id, action, record_id, description, ip))


# ── Helper: generate invoice number ──────────────────────────
def generate_invoice_number(cursor):
    cursor.execute("SELECT COUNT(*) AS cnt FROM invoices")
    count = cursor.fetchone()['cnt']
    return f"INV-2026-{count + 1:04d}"


# ─────────────────────────────────────────────────────────────
# GET /api/invoices/  — all invoices
# ─────────────────────────────────────────────────────────────
@invoice_bp.route('/', methods=['GET'])
def get_all_invoices():
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                i.invoice_id, i.invoice_number,
                i.po_id, po.po_number,
                i.supplier_name, i.supplier_phone,
                i.supplier_email, i.supplier_address,
                i.total_amount, i.status,
                i.generated_at, i.notes,
                u.full_name AS generated_by
            FROM invoices i
            JOIN purchase_orders po ON i.po_id       = po.po_id
            JOIN users u            ON i.generated_by = u.user_id
            ORDER BY i.generated_at DESC
        """)
        invoices = cursor.fetchall()
        for inv in invoices:
            inv['total_amount'] = float(inv['total_amount'])

        return jsonify({
            "success": True,
            "count"  : len(invoices),
            "data"   : invoices
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/invoices/<invoice_id>  — single invoice with line items
# ─────────────────────────────────────────────────────────────
@invoice_bp.route('/<int:invoice_id>', methods=['GET'])
def get_invoice(invoice_id):
    cursor = None
    try:
        cursor = get_cursor()

        # Invoice header
        cursor.execute("""
            SELECT
                i.invoice_id, i.invoice_number,
                i.po_id, po.po_number,
                i.supplier_id, i.supplier_name,
                i.supplier_phone, i.supplier_email,
                i.supplier_address, i.total_amount,
                i.status, i.generated_at, i.notes,
                u.full_name AS generated_by
            FROM invoices i
            JOIN purchase_orders po ON i.po_id        = po.po_id
            JOIN users u            ON i.generated_by = u.user_id
            WHERE i.invoice_id = %s
        """, (invoice_id,))
        invoice = cursor.fetchone()

        if not invoice:
            return jsonify({"success": False,
                            "message": "Invoice not found"}), 404

        invoice['total_amount'] = float(invoice['total_amount'])

        # Invoice line items
        cursor.execute("""
            SELECT
                ii.invoice_item_id, ii.item_id,
                ii.item_code, ii.item_name,
                ii.unit, ii.quantity,
                ii.unit_price, ii.subtotal
            FROM invoice_items ii
            WHERE ii.invoice_id = %s
            ORDER BY ii.invoice_item_id
        """, (invoice_id,))
        items = cursor.fetchall()
        for item in items:
            item['unit_price'] = float(item['unit_price'])
            item['subtotal']   = float(item['subtotal'])

        return jsonify({
            "success": True,
            "invoice": invoice,
            "items"  : items
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/invoices/po/<po_id>  — get invoice by PO ID
# ─────────────────────────────────────────────────────────────
@invoice_bp.route('/po/<int:po_id>', methods=['GET'])
def get_invoice_by_po(po_id):
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                i.invoice_id, i.invoice_number,
                i.po_id, po.po_number,
                i.supplier_name, i.total_amount,
                i.status, i.generated_at,
                u.full_name AS generated_by
            FROM invoices i
            JOIN purchase_orders po ON i.po_id        = po.po_id
            JOIN users u            ON i.generated_by = u.user_id
            WHERE i.po_id = %s
        """, (po_id,))
        invoice = cursor.fetchone()

        if not invoice:
            return jsonify({"success": False,
                            "message": "No invoice found for this PO"}), 404

        invoice['total_amount'] = float(invoice['total_amount'])
        return jsonify({"success": True, "invoice": invoice}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/invoices/summary  — invoice count by status
# ─────────────────────────────────────────────────────────────
@invoice_bp.route('/summary', methods=['GET'])
def invoice_summary():
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                COUNT(*)  AS total,
                SUM(CASE WHEN status = 'Draft'     THEN 1 ELSE 0 END) AS draft,
                SUM(CASE WHEN status = 'Finalized' THEN 1 ELSE 0 END) AS finalized,
                SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) AS cancelled,
                COALESCE(SUM(CASE WHEN status = 'Finalized'
                             THEN total_amount ELSE 0 END), 0) AS total_invoiced
            FROM invoices
        """)
        row = cursor.fetchone()
        row['total_invoiced'] = float(row['total_invoiced'])

        return jsonify({"success": True, "summary": row}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# POST /api/invoices/generate/<po_id>  — manually generate invoice
# ─────────────────────────────────────────────────────────────
@invoice_bp.route('/generate/<int:po_id>', methods=['POST'])
def generate_invoice(po_id):
    cursor = None
    try:
        data  = request.get_json() or {}
        user  = get_user_from_token(request)
        ip    = request.remote_addr
        notes = data.get('notes', '')

        cursor = get_cursor()

        # Validate PO exists and is received
        cursor.execute("""
            SELECT po.po_id, po.po_number, po.status,
                   po.total_amount, po.supplier_id,
                   s.supplier_name, s.phone, s.email, s.address
            FROM purchase_orders po
            JOIN suppliers s ON po.supplier_id = s.supplier_id
            WHERE po.po_id = %s
        """, (po_id,))
        po = cursor.fetchone()

        if not po:
            return jsonify({"success": False,
                            "message": "Purchase order not found"}), 404

        if po['status'] not in ('Received', 'Partially Received'):
            return jsonify({
                "success": False,
                "message": f"Invoice can only be generated for Received "
                           f"or Partially Received POs. "
                           f"Current status: {po['status']}"
            }), 400

        # Check if invoice already exists for this PO
        cursor.execute(
            "SELECT invoice_id, invoice_number FROM invoices WHERE po_id = %s",
            (po_id,))
        existing = cursor.fetchone()
        if existing:
            return jsonify({
                "success": False,
                "message": f"Invoice {existing['invoice_number']} "
                           f"already exists for this PO"
            }), 409

        # Generate invoice number
        invoice_number = generate_invoice_number(cursor)

        # Insert invoice header
        cursor.execute("""
            INSERT INTO invoices
                (invoice_number, po_id, supplier_id,
                 supplier_name, supplier_phone,
                 supplier_email, supplier_address,
                 total_amount, status, generated_by, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Finalized', %s, %s)
        """, (
            invoice_number,
            po['po_id'],
            po['supplier_id'],
            po['supplier_name'],
            po['phone'],
            po['email'],
            po['address'],
            po['total_amount'],
            user['user_id'],
            notes or f"Invoice for PO {po['po_number']}"
        ))
        invoice_id = cursor.lastrowid

        # Insert invoice line items (snapshot from PO items)
        cursor.execute("""
            SELECT poi.item_id, poi.quantity, poi.received_quantity,
                   poi.unit_price, poi.subtotal,
                   i.item_code, i.item_name, i.unit
            FROM purchase_order_items poi
            JOIN inventory_items i ON poi.item_id = i.item_id
            WHERE poi.po_id = %s
        """, (po_id,))
        po_items = cursor.fetchall()

        for item in po_items:
            cursor.execute("""
                INSERT INTO invoice_items
                    (invoice_id, item_id, item_code, item_name,
                     unit, quantity, unit_price, subtotal)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                invoice_id,
                item['item_id'],
                item['item_code'],
                item['item_name'],
                item['unit'],
                item['quantity'],
                item['unit_price'],
                item['subtotal']
            ))

        write_audit(cursor, user['user_id'], 'GENERATE', invoice_id,
                    f"Invoice {invoice_number} generated for "
                    f"PO {po['po_number']}", ip)

        commit()
        return jsonify({
            "success"       : True,
            "message"       : "Invoice generated successfully",
            "invoice_id"    : invoice_id,
            "invoice_number": invoice_number,
            "po_number"     : po['po_number'],
            "total_amount"  : float(po['total_amount'])
        }), 201

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# PUT /api/invoices/<invoice_id>/cancel  — cancel invoice
# ─────────────────────────────────────────────────────────────
@invoice_bp.route('/<int:invoice_id>/cancel', methods=['PUT'])
def cancel_invoice(invoice_id):
    cursor = None
    try:
        data   = request.get_json() or {}
        user   = get_user_from_token(request)
        ip     = request.remote_addr
        reason = data.get('reason', 'No reason provided')

        cursor = get_cursor()

        cursor.execute("""
            SELECT invoice_id, invoice_number, status
            FROM invoices WHERE invoice_id = %s
        """, (invoice_id,))
        invoice = cursor.fetchone()

        if not invoice:
            return jsonify({"success": False,
                            "message": "Invoice not found"}), 404

        if invoice['status'] == 'Cancelled':
            return jsonify({"success": False,
                            "message": "Invoice is already cancelled"}), 400

        cursor.execute("""
            UPDATE invoices
            SET status = 'Cancelled', notes = %s
            WHERE invoice_id = %s
        """, (f"Cancelled: {reason}", invoice_id))

        write_audit(cursor, user['user_id'], 'CANCEL', invoice_id,
                    f"Invoice {invoice['invoice_number']} cancelled. "
                    f"Reason: {reason}", ip)

        commit()
        return jsonify({
            "success": True,
            "message": f"Invoice {invoice['invoice_number']} cancelled successfully"
        }), 200

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# PUT /api/invoices/<invoice_id>/finalize  — finalize draft invoice
# ─────────────────────────────────────────────────────────────
@invoice_bp.route('/<int:invoice_id>/finalize', methods=['PUT'])
def finalize_invoice(invoice_id):
    cursor = None
    try:
        user = get_user_from_token(request)
        ip   = request.remote_addr

        cursor = get_cursor()

        cursor.execute("""
            SELECT invoice_id, invoice_number, status
            FROM invoices WHERE invoice_id = %s
        """, (invoice_id,))
        invoice = cursor.fetchone()

        if not invoice:
            return jsonify({"success": False,
                            "message": "Invoice not found"}), 404

        if invoice['status'] != 'Draft':
            return jsonify({
                "success": False,
                "message": f"Only Draft invoices can be finalized. "
                           f"Current status: {invoice['status']}"
            }), 400

        cursor.execute("""
            UPDATE invoices SET status = 'Finalized'
            WHERE invoice_id = %s
        """, (invoice_id,))

        write_audit(cursor, user['user_id'], 'FINALIZE', invoice_id,
                    f"Invoice {invoice['invoice_number']} finalized", ip)

        commit()
        return jsonify({
            "success": True,
            "message": f"Invoice {invoice['invoice_number']} finalized successfully"
        }), 200

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/invoices/view/<invoice_id>  — full invoice using view
# ─────────────────────────────────────────────────────────────
@invoice_bp.route('/view/<int:invoice_id>', methods=['GET'])
def view_invoice(invoice_id):
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT * FROM vw_invoice_summary
            WHERE invoice_id = %s
        """, (invoice_id,))
        rows = cursor.fetchall()

        if not rows:
            return jsonify({"success": False,
                            "message": "Invoice not found"}), 404

        # Build structured response from flat view rows
        first = rows[0]
        invoice = {
            "invoice_id"      : first['invoice_id'],
            "invoice_number"  : first['invoice_number'],
            "po_id"           : first['po_id'],
            "po_number"       : first['po_number'],
            "supplier_name"   : first['supplier_name'],
            "supplier_phone"  : first['supplier_phone'],
            "supplier_email"  : first['supplier_email'],
            "supplier_address": first['supplier_address'],
            "total_amount"    : float(first['total_amount']),
            "status"          : first['status'],
            "generated_by"    : first['generated_by'],
            "generated_at"    : str(first['generated_at']),
            "notes"           : first['notes'],
            "items"           : []
        }

        for row in rows:
            invoice['items'].append({
                "invoice_item_id": row['invoice_item_id'],
                "item_code"      : row['item_code'],
                "item_name"      : row['item_name'],
                "unit"           : row['unit'],
                "quantity"       : row['quantity'],
                "unit_price"     : float(row['unit_price']),
                "subtotal"       : float(row['subtotal'])
            })

        return jsonify({"success": True, "invoice": invoice}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/invoices/search?keyword=  — search invoices
# ─────────────────────────────────────────────────────────────
@invoice_bp.route('/search', methods=['GET'])
def search_invoices():
    cursor = None
    try:
        keyword = request.args.get('keyword', '').strip()
        if not keyword:
            return jsonify({"success": False,
                            "message": "keyword is required"}), 400

        like   = f"%{keyword}%"
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                i.invoice_id, i.invoice_number,
                po.po_number, i.supplier_name,
                i.total_amount, i.status, i.generated_at,
                u.full_name AS generated_by
            FROM invoices i
            JOIN purchase_orders po ON i.po_id        = po.po_id
            JOIN users u            ON i.generated_by = u.user_id
            WHERE i.invoice_number LIKE %s
               OR i.supplier_name  LIKE %s
               OR po.po_number     LIKE %s
               OR i.status         LIKE %s
            ORDER BY i.generated_at DESC
        """, (like, like, like, like))

        invoices = cursor.fetchall()
        for inv in invoices:
            inv['total_amount'] = float(inv['total_amount'])

        return jsonify({
            "success": True,
            "count"  : len(invoices),
            "data"   : invoices
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
