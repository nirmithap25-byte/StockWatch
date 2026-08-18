# routes/dashboard.py

from flask import Blueprint, jsonify
from database import get_cursor

dashboard_bp = Blueprint("dashboard", __name__)


# ─────────────────────────────────────────────────────────────
# GET /api/dashboard/summary  — main KPI summary
# ─────────────────────────────────────────────────────────────
@dashboard_bp.route("/summary", methods=["GET"])
def dashboard_summary():
    cursor = None
    try:
        cursor = get_cursor()

        # 1. Total active inventory items
        cursor.execute("""
            SELECT COUNT(*) AS cnt FROM inventory_items WHERE is_active = 'Yes'
        """)
        total_items = cursor.fetchone()['cnt']

        # 2. Total stock value (quantity * unit_price)
        cursor.execute("""
            SELECT COALESCE(SUM(quantity * unit_price), 0) AS val
            FROM inventory_items WHERE is_active = 'Yes'
        """)
        total_stock_value = float(cursor.fetchone()['val'])

        # 3. Low stock items (quantity <= minimum_stock)
        cursor.execute("""
            SELECT COUNT(*) AS cnt FROM inventory_items
            WHERE is_active = 'Yes' AND quantity <= minimum_stock
        """)
        low_stock_count = cursor.fetchone()['cnt']

        # 4. Out of stock items (quantity = 0)
        cursor.execute("""
            SELECT COUNT(*) AS cnt FROM inventory_items
            WHERE is_active = 'Yes' AND quantity = 0
        """)
        out_of_stock_count = cursor.fetchone()['cnt']

        # 5. Pending purchase orders
        cursor.execute("""
            SELECT COUNT(*) AS cnt FROM purchase_orders WHERE status = 'Pending'
        """)
        pending_po_count = cursor.fetchone()['cnt']

        # 6. Approved purchase orders
        cursor.execute("""
            SELECT COUNT(*) AS cnt FROM purchase_orders WHERE status = 'Approved'
        """)
        approved_po_count = cursor.fetchone()['cnt']

        # 7. Unread alerts
        cursor.execute("""
            SELECT COUNT(*) AS cnt FROM alerts WHERE status = 'Unread'
        """)
        unread_alerts = cursor.fetchone()['cnt']

        # 8. Today's stock movements
        cursor.execute("""
            SELECT COUNT(*) AS cnt FROM stock_movements
            WHERE DATE(movement_date) = CURDATE()
        """)
        todays_movements = cursor.fetchone()['cnt']

        # 9. Pending approvals
        cursor.execute("""
            SELECT COUNT(*) AS cnt FROM approvals WHERE status = 'Pending'
        """)
        pending_approvals = cursor.fetchone()['cnt']

        return jsonify({
            "success": True,
            "summary": {
                "total_items"       : total_items,
                "total_stock_value" : total_stock_value,
                "low_stock_count"   : low_stock_count,
                "out_of_stock_count": out_of_stock_count,
                "pending_po_count"  : pending_po_count,
                "approved_po_count" : approved_po_count,
                "unread_alerts"     : unread_alerts,
                "todays_movements"  : todays_movements,
                "pending_approvals" : pending_approvals
            }
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/dashboard/recent-movements  — last 10 movements
# ─────────────────────────────────────────────────────────────
@dashboard_bp.route("/recent-movements", methods=["GET"])
def recent_movements():
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
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
            JOIN users u           ON sm.user_id  = u.user_id
            ORDER BY sm.movement_date DESC
            LIMIT 10
        """)
        data = cursor.fetchall()
        return jsonify({"success": True, "recent_movements": data}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/dashboard/low-stock  — items below minimum_stock
# ─────────────────────────────────────────────────────────────
@dashboard_bp.route("/low-stock", methods=["GET"])
def low_stock_items():
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                i.item_id, i.item_code, i.item_name,
                c.category_name, d.department_name,
                i.quantity, i.minimum_stock, i.reorder_level,
                i.unit_price, s.supplier_name
            FROM inventory_items i
            JOIN categories  c ON i.category_id  = c.category_id
            JOIN departments d ON i.department_id = d.department_id
            JOIN suppliers   s ON i.supplier_id   = s.supplier_id
            WHERE i.is_active = 'Yes'
            AND   i.quantity  <= i.minimum_stock
            ORDER BY i.quantity ASC
        """)
        data = cursor.fetchall()
        for item in data:
            item['unit_price'] = float(item['unit_price'])
        return jsonify({
            "success"        : True,
            "count"          : len(data),
            "low_stock_items": data
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/dashboard/movement-stats  — breakdown by type (for charts)
# ─────────────────────────────────────────────────────────────
@dashboard_bp.route("/movement-stats", methods=["GET"])
def movement_stats():
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                movement_type,
                COUNT(*)       AS total_count,
                SUM(quantity)  AS total_quantity
            FROM stock_movements
            GROUP BY movement_type
        """)
        data = cursor.fetchall()
        return jsonify({"success": True, "movement_stats": data}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/dashboard/top-items  — top 5 most moved items
# ─────────────────────────────────────────────────────────────
@dashboard_bp.route("/top-items", methods=["GET"])
def top_items():
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                i.item_id, i.item_code, i.item_name,
                COUNT(sm.movement_id) AS movement_count,
                SUM(sm.quantity)      AS total_moved
            FROM stock_movements sm
            JOIN inventory_items i ON sm.item_id = i.item_id
            GROUP BY i.item_id, i.item_code, i.item_name
            ORDER BY movement_count DESC
            LIMIT 5
        """)
        data = cursor.fetchall()
        return jsonify({"success": True, "top_items": data}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/dashboard/pending-approvals  — pending approval requests
# ─────────────────────────────────────────────────────────────
@dashboard_bp.route("/pending-approvals", methods=["GET"])
def pending_approvals():
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                a.approval_id,
                i.item_name,
                u.full_name AS requested_by,
                a.quantity,
                a.purpose,
                a.status,
                a.request_date
            FROM approvals a
            JOIN inventory_items i ON a.item_id      = i.item_id
            JOIN users u           ON a.requested_by = u.user_id
            WHERE a.status = 'Pending'
            ORDER BY a.request_date DESC
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
# GET /api/dashboard/alerts-summary  — alert counts by type
# ─────────────────────────────────────────────────────────────
@dashboard_bp.route("/alerts-summary", methods=["GET"])
def alerts_summary():
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                alert_type,
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'Unread' THEN 1 ELSE 0 END) AS unread
            FROM alerts
            GROUP BY alert_type
        """)
        data = cursor.fetchall()
        return jsonify({"success": True, "alerts_summary": data}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
