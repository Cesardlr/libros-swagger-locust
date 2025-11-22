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
    """Register a new user.
    ---
    tags:
      - Authentication
    summary: Registrar un nuevo usuario
    description: Crea un nuevo usuario en el sistema. La contraseña se hashea con SHA-256 antes de almacenarse.
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        description: Datos del usuario a registrar
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              description: Nombre de usuario (único)
              example: "usuario123"
            password:
              type: string
              description: Contraseña del usuario
              example: "password123"
    responses:
      201:
        description: Usuario registrado exitosamente
        schema:
          type: object
          properties:
            message:
              type: string
              example: "User registered successfully"
      400:
        description: Datos faltantes o inválidos
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Username and password required"
      409:
        description: El nombre de usuario ya existe
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Username already exists"
      500:
        description: Error interno del servidor
    """
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
    """Login user and generate tokens.
    ---
    tags:
      - Authentication
    summary: Iniciar sesión
    description: Autentica un usuario y genera tokens JWT (access y refresh). Los tokens se almacenan en Redis.
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        description: Credenciales de acceso
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              description: Nombre de usuario
              example: "usuario123"
            password:
              type: string
              description: Contraseña del usuario
              example: "password123"
    responses:
      200:
        description: Login exitoso, tokens generados
        schema:
          type: object
          properties:
            access_token:
              type: string
              description: Token JWT de acceso (válido por 15 minutos por defecto)
              example: "eyJ0eXAiOiJKV1QiLCJhbGc..."
            refresh_token:
              type: string
              description: Token JWT de refresco (válido por 30 días por defecto)
              example: "eyJ0eXAiOiJKV1QiLCJhbGc..."
            username:
              type: string
              example: "usuario123"
      400:
        description: Datos faltantes
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Username and password required"
      401:
        description: Credenciales inválidas
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Invalid credentials"
      500:
        description: Error interno del servidor
    """
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
    """Refresh access token.
    ---
    tags:
      - Authentication
    summary: Renovar token de acceso
    description: Genera un nuevo token de acceso usando el refresh token. Requiere autenticación con refresh token.
    security:
      - Bearer: []
    produces:
      - application/json
    responses:
      200:
        description: Nuevo token de acceso generado
        schema:
          type: object
          properties:
            access_token:
              type: string
              description: Nuevo token JWT de acceso
              example: "eyJ0eXAiOiJKV1QiLCJhbGc..."
      401:
        description: Token inválido o expirado
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Token has been revoked"
      500:
        description: Error interno del servidor
    """
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
    """Logout user by revoking tokens.
    ---
    tags:
      - Authentication
    summary: Cerrar sesión
    description: Revoca los tokens del usuario actual, agregándolos a la blocklist de Redis.
    security:
      - Bearer: []
    produces:
      - application/json
    responses:
      200:
        description: Sesión cerrada exitosamente
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Successfully logged out"
      401:
        description: Token inválido o no autenticado
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Token has been revoked"
      500:
        description: Error interno del servidor
    """
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
