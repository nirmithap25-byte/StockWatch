from flask import Flask, jsonify
from flask_cors import CORS
from database import mysql
import config

app = Flask(__name__)
CORS(app)

# ── MySQL config ──────────────────────────────────────────────
app.config['MYSQL_HOST']     = config.MYSQL_HOST
app.config['MYSQL_USER']     = config.MYSQL_USER
app.config['MYSQL_PASSWORD'] = config.MYSQL_PASSWORD
app.config['MYSQL_DB']       = config.MYSQL_DB
app.config['SECRET_KEY']     = config.SECRET_KEY   

mysql.init_app(app)

# ── Blueprints ────────────────────────────────────────────────
from routes.auth      import auth_bp
from routes.inventory import inventory_bp
from routes.stock     import stock_bp
from routes.purchase  import purchase_bp
from routes.alerts    import alerts_bp
from routes.dashboard import dashboard_bp
from routes.approvals import approvals_bp
from routes.qr        import qr_bp
from routes.anomaly   import anomaly_bp
from routes.invoices  import invoice_bp       

app.register_blueprint(auth_bp,      url_prefix='/api/auth')
app.register_blueprint(inventory_bp, url_prefix='/api/inventory')
app.register_blueprint(stock_bp,     url_prefix='/api/stock')
app.register_blueprint(purchase_bp,  url_prefix='/api/purchase')
app.register_blueprint(alerts_bp,    url_prefix='/api/alerts')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
app.register_blueprint(approvals_bp, url_prefix='/api/approvals')
app.register_blueprint(qr_bp,        url_prefix='/api/qr')
app.register_blueprint(anomaly_bp,   url_prefix='/api/anomaly')
app.register_blueprint(invoice_bp,   url_prefix='/api/invoices')  

# ── Health check ──────────────────────────────────────────────
@app.route('/')
def home():
    return jsonify({"message": "StockWatch API running", "status": "ok"})

# ── Global error handlers ─────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405

# ── Entry point ───────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=config.DEBUG)