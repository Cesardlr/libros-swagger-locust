from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flasgger import Swagger
import os
from dotenv import load_dotenv
from auth import bp as auth_bp, check_if_token_revoked
from books import bp as books_bp

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)

# Configure JWT
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET', 'your-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = int(os.getenv('JWT_ACCESS_MIN', 15)) * 60  # Convert to seconds
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = int(os.getenv('JWT_REFRESH_DAYS', 30)) * 24 * 60 * 60  # Convert to seconds

# Initialize JWT
jwt = JWTManager(app)

# Configure CORS
cors_origins = os.getenv('CORS_ORIGINS', 'http://127.0.0.1:8080,http://localhost:8080').split(',')
CORS(app, origins=cors_origins, supports_credentials=True)

# JWT blocklist loader
@jwt.token_in_blocklist_loader
def check_if_token_in_blocklist(jwt_header, jwt_payload):
    return check_if_token_revoked(jwt_header, jwt_payload)

# Configure Swagger
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api-docs"
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "Books API - Sistema de Gestión de Libros",
        "description": "API REST para gestión de libros con autenticación JWT y almacenamiento de imágenes en Firebase Storage",
        "version": "1.0.0",
        "contact": {
            "name": "API Support"
        }
    },
    "basePath": "/",
    "schemes": ["http", "https"],
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Authorization header using the Bearer scheme. Example: \"Authorization: Bearer {token}\""
        }
    },
    "tags": [
        {
            "name": "Authentication",
            "description": "Endpoints de autenticación y gestión de usuarios"
        },
        {
            "name": "Books",
            "description": "Endpoints para gestión de libros (CRUD)"
        }
    ]
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(books_bp, url_prefix='/api')

@app.route('/')
def health_check():
    return {'status': 'OK', 'message': 'Microservice is running'}

@app.route('/health')
def health():
    return {'status': 'healthy'}

@app.route('/ping')
def ping():
    return {'status': 'pong', 'message': 'Server is alive'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

