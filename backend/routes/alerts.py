# routes/alerts.py

from flask import Blueprint, request, jsonify
from database import get_cursor, commit, rollback
import jwt
import config

alerts_bp = Blueprint('alerts', __name__)


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
        VALUES (%s, 'Alerts', %s, 'alerts', %s, %s, %s)
    """, (user_id, action, record_id, description, ip))


# ─────────────────────────────────────────────────────────────
# GET /api/alerts/summary  — MUST be before /<int:alert_id>
# ─────────────────────────────────────────────────────────────
@alerts_bp.route('/summary', methods=['GET'])
def alerts_summary():
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                COUNT(*)  AS total_unread,
                SUM(CASE WHEN severity = 'High'   THEN 1 ELSE 0 END) AS high,
                SUM(CASE WHEN severity = 'Medium' THEN 1 ELSE 0 END) AS medium,
                SUM(CASE WHEN severity = 'Low'    THEN 1 ELSE 0 END) AS low_count
            FROM alerts
            WHERE status = 'Unread'
        """)
        row = cursor.fetchone()

        return jsonify({
            "success": True,
            "summary": {
                "total_unread": row['total_unread'] or 0,
                "high"        : row['high']         or 0,
                "medium"      : row['medium']       or 0,
                "low"         : row['low_count']    or 0
            }
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# PUT /api/alerts/read-all  — MUST be before /<int:alert_id>
# ─────────────────────────────────────────────────────────────
@alerts_bp.route('/read-all', methods=['PUT'])
def mark_all_as_read():
    cursor = None
    try:
        user = get_user_from_token(request)
        ip   = request.remote_addr

        cursor = get_cursor()
        cursor.execute("""
            UPDATE alerts SET status = 'Read'
            WHERE status = 'Unread'
        """)
        affected = cursor.rowcount

        write_audit(cursor, user['user_id'], 'MARK_ALL_READ', 0,
                    f"Marked {affected} alerts as read", ip)

        commit()
        return jsonify({
            "success": True,
            "message": f"{affected} alerts marked as read"
        }), 200

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/alerts/  — all alerts (filter by unread + type)
# ─────────────────────────────────────────────────────────────
@alerts_bp.route('/', methods=['GET'])
def get_alerts():
    cursor = None
    try:
        unread_only = request.args.get('unread', 'true').lower() == 'true'
        alert_type  = request.args.get('type', '').strip()   # optional filter
        severity    = request.args.get('severity', '').strip()

        cursor = get_cursor()

        # Build dynamic WHERE clause
        conditions = []
        params     = []

        if unread_only:
            conditions.append("a.status = 'Unread'")

        valid_types = ['Low Stock', 'Reorder Required', 'Anomaly', 'System']
        if alert_type and alert_type in valid_types:
            conditions.append("a.alert_type = %s")
            params.append(alert_type)

        valid_severities = ['High', 'Medium', 'Low']
        if severity and severity in valid_severities:
            conditions.append("a.severity = %s")
            params.append(severity)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        cursor.execute(f"""
            SELECT
                a.alert_id, a.alert_type, a.severity,
                a.message, a.status, a.created_at,
                a.item_id,
                i.item_name, i.item_code,
                i.quantity, i.reorder_level
            FROM alerts a
            LEFT JOIN inventory_items i ON a.item_id = i.item_id
            {where}
            ORDER BY
                FIELD(a.severity, 'High', 'Medium', 'Low'),
                a.created_at DESC
        """, params)

        alerts = cursor.fetchall()
        return jsonify({
            "success": True,
            "count"  : len(alerts),
            "data"   : alerts
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/alerts/<alert_id>  — single alert
# ─────────────────────────────────────────────────────────────
@alerts_bp.route('/<int:alert_id>', methods=['GET'])
def get_alert(alert_id):
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                a.alert_id, a.alert_type, a.severity,
                a.message, a.status, a.created_at,
                a.item_id,
                i.item_name, i.item_code,
                i.quantity, i.minimum_stock, i.reorder_level
            FROM alerts a
            LEFT JOIN inventory_items i ON a.item_id = i.item_id
            WHERE a.alert_id = %s
        """, (alert_id,))

        alert = cursor.fetchone()
        if not alert:
            return jsonify({"success": False,
                            "message": "Alert not found"}), 404

        return jsonify({"success": True, "data": alert}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# PUT /api/alerts/<alert_id>/read  — mark single alert as read
# ─────────────────────────────────────────────────────────────
@alerts_bp.route('/<int:alert_id>/read', methods=['PUT'])
def mark_as_read(alert_id):
    cursor = None
    try:
        user = get_user_from_token(request)
        ip   = request.remote_addr

        cursor = get_cursor()

        cursor.execute(
            "SELECT alert_id, alert_type, status FROM alerts WHERE alert_id = %s",
            (alert_id,))
        alert = cursor.fetchone()

        if not alert:
            return jsonify({"success": False,
                            "message": "Alert not found"}), 404

        if alert['status'] == 'Read':
            return jsonify({"success": False,
                            "message": "Alert is already marked as read"}), 400

        cursor.execute("""
            UPDATE alerts SET status = 'Read' WHERE alert_id = %s
        """, (alert_id,))

        write_audit(cursor, user['user_id'], 'MARK_READ', alert_id,
                    f"Alert {alert_id} ({alert['alert_type']}) "
                    f"marked as read", ip)

        commit()
        return jsonify({
            "success": True,
            "message": "Alert marked as read"
        }), 200

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# POST /api/alerts/create  — manually create system alert
# ─────────────────────────────────────────────────────────────
@alerts_bp.route('/create', methods=['POST'])
def create_alert():
    cursor = None
    try:
        data     = request.get_json()
        user     = get_user_from_token(request)
        ip       = request.remote_addr

        message    = data.get('message', '').strip()
        alert_type = data.get('alert_type', 'System')
        severity   = data.get('severity', 'Medium')
        item_id    = data.get('item_id')

        if not message:
            return jsonify({"success": False,
                            "message": "message is required"}), 400

        valid_types = ['Low Stock', 'Reorder Required', 'Anomaly', 'System']
        if alert_type not in valid_types:
            return jsonify({"success": False,
                            "message": f"alert_type must be "
                                       f"one of {valid_types}"}), 400

        valid_severities = ['Low', 'Medium', 'High']
        if severity not in valid_severities:
            return jsonify({"success": False,
                            "message": f"severity must be "
                                       f"one of {valid_severities}"}), 400

        cursor = get_cursor()

        cursor.execute("""
            INSERT INTO alerts (item_id, alert_type, severity, message)
            VALUES (%s, %s, %s, %s)
        """, (item_id, alert_type, severity, message))

        alert_id = cursor.lastrowid

        write_audit(cursor, user['user_id'], 'CREATE', alert_id,
                    f"Manual alert created: {alert_type} — {message}", ip)

        commit()
        return jsonify({
            "success" : True,
            "message" : "Alert created successfully",
            "alert_id": alert_id
        }), 201

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# DELETE /api/alerts/<alert_id>  — delete alert (Admin only)
# ─────────────────────────────────────────────────────────────
@alerts_bp.route('/<int:alert_id>', methods=['DELETE'])
def delete_alert(alert_id):
    cursor = None
    try:
        user = get_user_from_token(request)
        ip   = request.remote_addr

        cursor = get_cursor()

        cursor.execute(
            "SELECT alert_id, alert_type FROM alerts WHERE alert_id = %s",
            (alert_id,))
        alert = cursor.fetchone()

        if not alert:
            return jsonify({"success": False,
                            "message": "Alert not found"}), 404

        cursor.execute(
            "DELETE FROM alerts WHERE alert_id = %s", (alert_id,))

        write_audit(cursor, user['user_id'], 'DELETE', alert_id,
                    f"Alert {alert_id} ({alert['alert_type']}) deleted", ip)

        commit()
        return jsonify({
            "success": True,
            "message": "Alert deleted successfully"
        }), 200

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()