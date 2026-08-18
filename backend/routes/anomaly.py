# routes/anomaly.py

from flask import Blueprint, request, jsonify
from database import get_cursor, commit, rollback
import pandas as pd
from sklearn.ensemble import IsolationForest

anomaly_bp = Blueprint("anomaly", __name__)


# ── Helper: encode movement type to int ───────────────────────
def encode_movement_type(movement_type):
    return {"IN": 1, "OUT": 2, "TRANSFER": 3, "ADJUSTMENT": 4}.get(movement_type, 0)


# ─────────────────────────────────────────────────────────────
# POST /api/anomaly/detect  — run Isolation Forest
# ─────────────────────────────────────────────────────────────
@anomaly_bp.route("/detect", methods=["POST"])
def detect_anomalies():
    cursor = None
    try:
        cursor = get_cursor()

        cursor.execute("""
            SELECT
                sm.movement_id, sm.item_id, sm.movement_type,
                sm.quantity, sm.previous_quantity, sm.new_quantity,
                i.item_name
            FROM stock_movements sm
            JOIN inventory_items i ON sm.item_id = i.item_id
            ORDER BY sm.movement_date ASC
        """)
        rows = cursor.fetchall()

        if len(rows) < 5:
            return jsonify({
                "success": False,
                "message": "Not enough data. Need at least 5 stock movement records."
            }), 400

        # Build DataFrame
        df = pd.DataFrame(rows)

        df["movement_type_encoded"] = df["movement_type"].apply(encode_movement_type)
        df["quantity_change"]       = abs(df["new_quantity"] - df["previous_quantity"])
        df["drop_percentage"]       = df.apply(
            lambda r: (r["quantity_change"] / r["previous_quantity"] * 100)
                      if r["previous_quantity"] > 0 else 0,
            axis=1
        )

        features = df[[
            "quantity", "previous_quantity", "new_quantity",
            "movement_type_encoded", "quantity_change", "drop_percentage"
        ]].values

        # Run Isolation Forest
        model = IsolationForest(
            n_estimators=100,
            contamination=0.1,
            random_state=42
        )
        predictions        = model.fit_predict(features)
        scores             = model.decision_function(features)
        df["anomaly"]      = predictions
        df["anomaly_score"] = scores

        anomalies = df[df["anomaly"] == -1]

        if anomalies.empty:
            return jsonify({
                "success"                  : True,
                "message"                  : "No anomalies detected. All movements look normal.",
                "total_movements_analyzed" : len(df),
                "anomalies_found"          : 0,
                "anomalies"                : []
            }), 200

        inserted    = 0
        anomaly_list = []

        for _, row in anomalies.iterrows():
            # Skip if same anomaly alert already exists (Unread)
            cursor.execute("""
                SELECT alert_id FROM alerts
                WHERE item_id = %s
                AND alert_type = 'Anomaly'
                AND message LIKE %s
                AND status = 'Unread'
            """, (int(row["item_id"]),
                  f"%Movement ID {int(row['movement_id'])}%"))

            if not cursor.fetchone():
                severity = "High" if row["anomaly_score"] < -0.1 else "Medium"
                message  = (
                    f"Anomaly detected — Movement ID {int(row['movement_id'])} "
                    f"for '{row['item_name']}': "
                    f"{row['movement_type']} of {int(row['quantity'])} units "
                    f"(Prev: {int(row['previous_quantity'])}, "
                    f"New: {int(row['new_quantity'])})"
                )
                cursor.execute("""
                    INSERT INTO alerts (item_id, alert_type, severity, message)
                    VALUES (%s, 'Anomaly', %s, %s)
                """, (int(row["item_id"]), severity, message))
                inserted += 1

            anomaly_list.append({
                "movement_id"      : int(row["movement_id"]),
                "item_id"          : int(row["item_id"]),
                "item_name"        : row["item_name"],
                "movement_type"    : row["movement_type"],
                "quantity"         : int(row["quantity"]),
                "previous_quantity": int(row["previous_quantity"]),
                "new_quantity"     : int(row["new_quantity"]),
                "anomaly_score"    : round(float(row["anomaly_score"]), 4),
                "severity"         : "High" if row["anomaly_score"] < -0.1 else "Medium"
            })

        # Audit log
        cursor.execute("""
            INSERT INTO audit_logs
                (user_id, module, action, table_name, record_id, description, ip_address)
            VALUES (1, 'Anomaly Detection', 'SCAN', 'stock_movements', 0, %s, %s)
        """, (f"Anomaly scan: {len(df)} movements analyzed, "
              f"{len(anomalies)} anomalies found.",
              request.remote_addr))

        commit()
        return jsonify({
            "success"                 : True,
            "message"                 : "Anomaly detection complete.",
            "total_movements_analyzed": len(df),
            "anomalies_found"         : len(anomalies),
            "new_alerts_inserted"     : inserted,
            "anomalies"               : anomaly_list
        }), 200

    except Exception as e:
        rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/anomaly/alerts  — all anomaly alerts
# ─────────────────────────────────────────────────────────────
@anomaly_bp.route("/alerts", methods=["GET"])
def get_anomaly_alerts():
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                a.alert_id, a.item_id,
                i.item_name, i.item_code,
                a.alert_type, a.severity,
                a.message, a.status, a.created_at
            FROM alerts a
            LEFT JOIN inventory_items i ON a.item_id = i.item_id
            WHERE a.alert_type = 'Anomaly'
            ORDER BY
                FIELD(a.severity, 'High', 'Medium', 'Low'),
                a.created_at DESC
        """)
        data = cursor.fetchall()
        return jsonify({"success": True, "count": len(data), "anomaly_alerts": data}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/anomaly/summary  — anomaly count summary
# ─────────────────────────────────────────────────────────────
@anomaly_bp.route("/summary", methods=["GET"])
def anomaly_summary():
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT
                COUNT(*) AS total_anomalies,
                SUM(CASE WHEN severity = 'High'   THEN 1 ELSE 0 END) AS high,
                SUM(CASE WHEN severity = 'Medium' THEN 1 ELSE 0 END) AS medium,
                SUM(CASE WHEN status   = 'Unread' THEN 1 ELSE 0 END) AS unread
            FROM alerts
            WHERE alert_type = 'Anomaly'
        """)
        row = cursor.fetchone()
        return jsonify({
            "success": True,
            "summary": {
                "total_anomalies": row['total_anomalies'] or 0,
                "high"           : row['high']            or 0,
                "medium"         : row['medium']          or 0,
                "unread"         : row['unread']          or 0
            }
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
