# routes/auth.py

from flask import Blueprint, request, jsonify
import jwt
import datetime
import hashlib
from database import get_cursor, commit, rollback
import config

auth_bp = Blueprint('auth', __name__)


# ── Helper: hash password ─────────────────────────────────────
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# ── Helper: generate JWT token ────────────────────────────────
def generate_token(user):
    payload = {
        'user_id'  : user['user_id'],
        'email'    : user['email'],
        'role'     : user['role'],
        'exp'      : datetime.datetime.utcnow() +
                     datetime.timedelta(hours=config.JWT_EXPIRY_HOURS)
    }
    return jwt.encode(payload, config.SECRET_KEY, algorithm='HS256')


# ── Helper: write audit log ───────────────────────────────────
def write_audit(cursor, user_id, action, description, ip):
    cursor.execute("""
        INSERT INTO audit_logs
            (user_id, module, action, table_name, record_id, description, ip_address)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (user_id, 'Auth', action, 'users', user_id, description, ip))


# ─────────────────────────────────────────────────────────────
# POST /api/auth/login
# ─────────────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['POST'])
def login():
    data     = request.get_json()
    email    = data.get('email', '').strip()
    password = data.get('password', '').strip()
    ip       = request.remote_addr

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    cursor = None
    try:
        cursor = get_cursor()

        # Fetch user by email only first
        cursor.execute("""
            SELECT u.user_id, u.full_name, u.email, u.password,
                   u.role, u.status, u.phone,
                   u.department_id, d.department_name
            FROM users u
            LEFT JOIN departments d ON u.department_id = d.department_id
            WHERE u.email = %s
        """, (email,))
        user = cursor.fetchone()

        # Check user exists
        if not user:
            return jsonify({"error": "Invalid email or password"}), 401

        # Check account is active
        if user['status'] != 'Active':
            return jsonify({"error": "Account is inactive. Contact admin."}), 403

        # Verify password (support both plain text legacy + hashed)
        hashed = hash_password(password)
        if user['password'] != password and user['password'] != hashed:
            return jsonify({"error": "Invalid email or password"}), 401

        # Write audit log
        write_audit(cursor, user['user_id'], 'LOGIN',
                    f"{user['full_name']} logged in", ip)
        commit()

        # Generate token
        token = generate_token(user)

        return jsonify({
            "message" : "Login successful",
            "token"   : token,
            "user"    : {
                "user_id"         : user['user_id'],
                "full_name"       : user['full_name'],
                "email"           : user['email'],
                "role"            : user['role'],
                "department_id"   : user['department_id'],
                "department_name" : user['department_name']
            }
        }), 200

    except Exception as e:
        rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/auth/users  — list all users (Admin only)
# ─────────────────────────────────────────────────────────────
@auth_bp.route('/users', methods=['GET'])
def get_users():
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT u.user_id, u.full_name, u.email, u.phone,
                   u.role, u.status, u.created_at,
                   d.department_name
            FROM users u
            LEFT JOIN departments d ON u.department_id = d.department_id
            ORDER BY u.created_at DESC
        """)
        users = cursor.fetchall()
        return jsonify({"users": users}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# POST /api/auth/register  — add new user (Admin only)
# ─────────────────────────────────────────────────────────────
@auth_bp.route('/register', methods=['POST'])
def register():
    data          = request.get_json()
    full_name     = data.get('full_name', '').strip()
    email         = data.get('email', '').strip()
    password      = data.get('password', '').strip()
    phone         = data.get('phone', '')
    role          = data.get('role', '')
    department_id = data.get('department_id')
    ip            = request.remote_addr

    # Validate required fields
    if not all([full_name, email, password, role]):
        return jsonify({"error": "full_name, email, password, role are required"}), 400

    valid_roles = ['Admin', 'Inventory Manager', 'Department Head', 'Auditor']
    if role not in valid_roles:
        return jsonify({"error": f"Role must be one of {valid_roles}"}), 400

    cursor = None
    try:
        cursor = get_cursor()

        # Check email already exists
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({"error": "Email already registered"}), 409

        # Hash password
        hashed = hash_password(password)

        # Insert user
        cursor.execute("""
            INSERT INTO users (full_name, email, password, phone, role, department_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (full_name, email, hashed, phone, role, department_id))

        new_user_id = cursor.lastrowid

        # Audit log
        write_audit(cursor, new_user_id, 'REGISTER',
                    f"New user registered: {full_name} ({role})", ip)
        commit()

        return jsonify({
            "message" : "User registered successfully",
            "user_id" : new_user_id
        }), 201

    except Exception as e:
        rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# PUT /api/auth/users/<id>  — update user status (Admin only)
# ─────────────────────────────────────────────────────────────
@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    data   = request.get_json()
    status = data.get('status')
    phone  = data.get('phone')
    role   = data.get('role')
    ip     = request.remote_addr

    cursor = None
    try:
        cursor = get_cursor()

        # Check user exists
        cursor.execute("SELECT user_id, full_name FROM users WHERE user_id = %s",
                       (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Build dynamic update
        fields, values = [], []
        if status:
            if status not in ['Active', 'Inactive']:
                return jsonify({"error": "Status must be Active or Inactive"}), 400
            fields.append("status = %s"); values.append(status)
        if phone:
            fields.append("phone = %s");  values.append(phone)
        if role:
            valid_roles = ['Admin','Inventory Manager','Department Head','Auditor']
            if role not in valid_roles:
                return jsonify({"error": f"Invalid role"}), 400
            fields.append("role = %s");   values.append(role)

        if not fields:
            return jsonify({"error": "Nothing to update"}), 400

        values.append(user_id)
        cursor.execute(f"UPDATE users SET {', '.join(fields)} WHERE user_id = %s",
                       values)

        # Audit log
        write_audit(cursor, user_id, 'UPDATE',
                    f"User {user['full_name']} updated", ip)
        commit()

        return jsonify({"message": "User updated successfully"}), 200

    except Exception as e:
        rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/auth/users/<id>  — get single user
# ─────────────────────────────────────────────────────────────
@auth_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT u.user_id, u.full_name, u.email, u.phone,
                   u.role, u.status, u.created_at,
                   d.department_name
            FROM users u
            LEFT JOIN departments d ON u.department_id = d.department_id
            WHERE u.user_id = %s
        """, (user_id,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({"user": user}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()


# ─────────────────────────────────────────────────────────────
# GET /api/auth/audit-logs  — list all audit logs
# ─────────────────────────────────────────────────────────────
@auth_bp.route('/audit-logs', methods=['GET'])
def get_audit_logs():
    cursor = None
    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT a.log_id, a.module, a.action, a.table_name,
                   a.record_id, a.description, a.ip_address, a.log_time,
                   u.full_name AS performed_by, u.role AS user_role
            FROM audit_logs a
            LEFT JOIN users u ON a.user_id = u.user_id
            ORDER BY a.log_time DESC
        """)
        logs = cursor.fetchall()
        return jsonify({"success": True, "data": logs}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        if cursor:
            cursor.close()