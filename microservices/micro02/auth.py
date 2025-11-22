from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from flask_jwt_extended.utils import decode_token
import redis
import os
import time
import pymysql
import hashlib
from db import get_conn

bp = Blueprint("auth", __name__)

# Redis connection
r = redis.Redis(
    host=os.getenv("REDIS_HOST", "127.0.0.1"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    db=int(os.getenv("REDIS_DB", "0")),
    decode_responses=True
)

def allow_key(token_type, jti):
    """Generate allowlist key for Redis."""
    return f"allow:{token_type}:{jti}"

def block_key(jti):
    """Generate blocklist key for Redis."""
    return f"block:{jti}"

def ttl_from_exp(exp):
    """Calculate TTL from expiration timestamp."""
    return max(1, exp - int(time.time()))

def store_allow(encoded, token_type, username):
    """Store token in allowlist with TTL."""
    dec = decode_token(encoded)
    jti, exp = dec["jti"], dec["exp"]
    r.hset(allow_key(token_type, jti), mapping={
        "u": username, 
        "t": token_type, 
        "exp": exp
    })
    r.expire(allow_key(token_type, jti), ttl_from_exp(exp))
    return jti

def is_revoked(jti):
    """Check if token is in blocklist."""
    return r.exists(block_key(jti)) == 1

def in_allow(jti):
    """Check if token is in allowlist."""
    return (r.exists(allow_key("access", jti)) == 1 or 
            r.exists(allow_key("refresh", jti)) == 1)

def revoke(jti, exp):
    """Revoke token by adding to blocklist and removing from allowlist."""
    r.setex(block_key(jti), ttl_from_exp(exp), "1")
    r.delete(allow_key("access", jti))
    r.delete(allow_key("refresh", jti))

@bp.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        # Hash password using SHA-256
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        # Store in database
        conn = get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO usuarios (username, password) VALUES (%s, %s)",
                (username, hashed_password)
            )
            conn.commit()
            return jsonify({'message': 'User registered successfully'}), 201
        except pymysql.IntegrityError:
            return jsonify({'error': 'Username already exists'}), 409
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/login', methods=['POST'])
def login():
    """Login user and generate tokens."""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        # Verify user credentials
        conn = get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT id, password FROM usuarios WHERE username = %s",
                (username,)
            )
            user = cursor.fetchone()
            
            if not user or hashlib.sha256(password.encode()).hexdigest() != user['password']:
                return jsonify({'error': 'Invalid credentials'}), 401
            
            # Generate tokens
            access_token = create_access_token(identity=username)
            refresh_token = create_refresh_token(identity=username)
            
            # Store tokens in allowlist
            store_allow(access_token, "access", username)
            store_allow(refresh_token, "refresh", username)
            
            return jsonify({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'username': username
            }), 200
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token."""
    try:
        current_user = get_jwt_identity()
        new_access_token = create_access_token(identity=current_user)
        
        # Store new token in allowlist
        store_allow(new_access_token, "access", current_user)
        
        return jsonify({
            'access_token': new_access_token
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user by revoking tokens."""
    try:
        jti = get_jwt()['jti']
        exp = get_jwt()['exp']
        
        # Revoke current token
        revoke(jti, exp)
        
        return jsonify({'message': 'Successfully logged out'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# JWT blocklist checker (to be used in main.py)
def check_if_token_revoked(jwt_header, jwt_payload):
    """Check if token is revoked or not in allowlist."""
    jti = jwt_payload["jti"]
    return is_revoked(jti) or (not in_allow(jti))
