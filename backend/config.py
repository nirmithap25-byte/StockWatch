# config.py

import os

# ── Database ──────────────────────────────────────────────────
MYSQL_HOST     = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_USER     = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_DB       = os.getenv('MYSQL_DB', 'inventory_monitoring_system')

# ── App ───────────────────────────────────────────────────────
SECRET_KEY = os.getenv('SECRET_KEY', 'stockwatch-secret-key-2025')
DEBUG      = os.getenv('DEBUG', 'true').lower() == 'true'

# ── JWT ───────────────────────────────────────────────────────
JWT_EXPIRY_HOURS = 24

# ── Alerts ───────────────────────────────────────────────────
LOW_STOCK_CHECK_ENABLED = True

# ── Invoice ──────────────────────────────────────────────────
INVOICE_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'invoices')

# ── Anomaly Detection ────────────────────────────────────────
ANOMALY_CONTAMINATION = 0.05   # 5% of movements flagged as anomalies
ANOMALY_MIN_SAMPLES   = 10     # minimum rows needed to run ML model