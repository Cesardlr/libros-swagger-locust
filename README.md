# Sistema de Gestión de Libros - Microservicio Flask

Este proyecto implementa un sistema de gestión de libros con autenticación JWT, Redis para manejo de sesiones, y una interfaz web moderna.

## Estructura del Proyecto

```
/microservices/
  /micro02/                 # Backend Flask (con Redis para sesiones)
    main.py                 # Aplicación principal Flask
    requirements.txt        # Dependencias Python
    .env.example           # Variables de entorno de ejemplo
    db.py                  # Helper conexión MariaDB
    auth.py                # Módulo de autenticación JWT + Redis
    books.py               # API de libros (todas protegidas)
    xml_utils.py           # Utilidades para serialización XML
/webapp/                   # Cliente web estático
  index.html               # Interfaz principal
  style.css                # Estilos CSS
  script.js                # Lógica JavaScript
README.md                  # Este archivo
```

## Características

- **Autenticación JWT** con tokens de acceso y refresh
- **Redis** para manejo de sesiones (allowlist/denylist)
- **MariaDB** para almacenamiento de datos
- **Firebase Storage** para imágenes de libros
- **API REST** con respuestas en formato XML
- **Interfaz web moderna** con funcionalidades CRUD
- **CORS** configurado para desarrollo local
- **Auto-refresh** de tokens en el cliente
- **Imágenes de libros** desde Firebase Storage bucket

## Requisitos Previos

- Python 3.8+
- MariaDB/MySQL
- Redis Server
- Firebase Project con Storage habilitado
- Navegador web moderno

## Instalación y Configuración

### 1. Configurar Base de Datos

Crear la base de datos y tabla de usuarios:

```sql
CREATE DATABASE Libros;
USE Libros;

CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE libros (
    id INT AUTO_INCREMENT PRIMARY KEY,
    isbn VARCHAR(20) UNIQUE NOT NULL,
    titulo VARCHAR(255) NOT NULL,
    autor VARCHAR(255) NOT NULL,
    formato ENUM('Físico', 'Digital', 'Audiolibro') NOT NULL,
    precio DECIMAL(10,2) NOT NULL,
    descripcion TEXT,
    imagen_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. Configurar Variables de Entorno

```bash
cd microservices/micro02
cp .env.example .env
```

Editar `.env` con tus configuraciones:

```env
# Flask
FLASK_ENV=development
JWT_SECRET=tu_clave_secreta_muy_larga_y_segura
JWT_ACCESS_MIN=15
JWT_REFRESH_DAYS=30

# MariaDB
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASS=tu_password_mariadb
DB_NAME=Libros
DB_CHARSET=utf8mb4

# Redis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0

# CORS
CORS_ORIGINS=http://127.0.0.1:8080,http://localhost:8080

# Firebase Storage (Opcional - para imágenes de libros)
FIREBASE_CREDENTIALS_PATH=path/to/firebase-service-account.json
FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
```

### 3. Configurar Firebase Storage (Opcional)

1. Crear un proyecto en [Firebase Console](https://console.firebase.google.com/)
2. Habilitar Firebase Storage en tu proyecto
3. Descargar las credenciales de la cuenta de servicio:
   - Ir a Project Settings > Service Accounts
   - Generar nueva clave privada
   - Guardar el archivo JSON en un lugar seguro
4. Configurar las variables de entorno en `.env`:
   - `FIREBASE_CREDENTIALS_PATH`: Ruta al archivo JSON de credenciales
   - `FIREBASE_STORAGE_BUCKET`: Nombre del bucket (ej: `mi-proyecto.appspot.com`)

**Nota**: Si no configuras Firebase, el sistema funcionará normalmente pero no mostrará imágenes de libros. Las imágenes se buscarán automáticamente en Firebase Storage usando el patrón `books/{isbn}.jpg` (o .png, .jpeg, .webp).

### 4. Instalar Dependencias del Backend

```bash
cd microservices/micro02
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 5. Ejecutar el Backend

```bash
# Windows PowerShell
$env:FLASK_APP="main.py"
flask run -p 5000 --host=0.0.0.0

# macOS/Linux
export FLASK_APP=main.py
flask run -p 5000 --host=0.0.0.0
```

### 6. Ejecutar el Frontend

```bash
cd webapp
python -m http.server 8080
```

Abrir en el navegador: http://localhost:8080

## API Endpoints

### Autenticación

- `POST /auth/register` - Registrar nuevo usuario
- `POST /auth/login` - Iniciar sesión
- `POST /auth/refresh` - Renovar token de acceso
- `POST /auth/logout` - Cerrar sesión

### Libros (Todos protegidos con JWT)

- `GET /api/books` - Obtener todos los libros
- `GET /api/books/ISBN?isbn=...` - Buscar por ISBN
- `GET /api/books/format/?format=...` - Buscar por formato
- `GET /api/books/autor/?name=...` - Buscar por autor
- `POST /api/books/create` - Crear nuevo libro
- `PUT /api/books/update` - Actualizar libro
- `DELETE /api/books/delete?isbn=...` - Eliminar libro

## Funcionalidades del Cliente Web

- **Registro y Login** de usuarios
- **Gestión completa de libros** (CRUD)
- **Búsquedas avanzadas** por ISBN, autor y formato
- **Auto-refresh** de tokens JWT
- **Logs en tiempo real** del sistema
- **Interfaz responsive** y moderna

## Seguridad

- **JWT con Redis**: Tokens almacenados en allowlist con TTL
- **Revocación de tokens**: Sistema de denylist para logout
- **Validación estricta**: Solo tokens en allowlist son válidos
- **CORS configurado**: Solo orígenes permitidos
- **Contraseñas hasheadas**: Usando SHA-256

## Solución de Problemas

### Error 401 con token válido

- Verificar que Redis esté ejecutándose
- Comprobar que el token esté en allowlist: `allow:access:<jti>`

### Error de conexión a base de datos

- Verificar credenciales en `.env`
- Usar `127.0.0.1` en lugar de `localhost`
- Confirmar que MariaDB esté ejecutándose

### Error CORS

- Verificar configuración en `main.py`
- Asegurar que el frontend esté en puerto 8080

### Redis no responde

- Verificar que `redis-server` esté ejecutándose en puerto 6379
- Comprobar configuración de Redis en `.env`

## Flujo de Pruebas

1. **Registrar usuario**: POST `/auth/register`
2. **Iniciar sesión**: POST `/auth/login` → recibe tokens
3. **Acceder a libros**: GET `/api/books` con Authorization header
4. **Renovar token**: POST `/auth/refresh` cuando sea necesario
5. **Cerrar sesión**: POST `/auth/logout` → revoca tokens

## Tecnologías Utilizadas

- **Backend**: Flask, Flask-JWT-Extended, PyMySQL, Redis, Firebase Admin SDK
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Base de datos**: MariaDB/MySQL
- **Cache/Sesión**: Redis
- **Almacenamiento de imágenes**: Firebase Storage
- **Autenticación**: JWT con SHA-256
- **Formato de datos**: XML para respuestas de API

## Imágenes de Libros

El sistema busca automáticamente imágenes de libros en Firebase Storage usando el patrón:

- `books/{isbn}.jpg`
- `books/{isbn}.jpeg`
- `books/{isbn}.png`
- `books/{isbn}.webp`

### Configuración de Firebase Storage

1. **Habilitar Storage en Firebase Console**

   - Ve a Firebase Console > Storage
   - Crea un bucket si no existe

2. **Configurar Reglas de Seguridad**

   En Firebase Console > Storage > Rules, configura las siguientes reglas:

   ```javascript
   rules_version = '2';
   service firebase.storage {
     match /b/{bucket}/o {
       // Permitir lectura pública de imágenes de libros
       match /books/{isbn}.{extension} {
         allow read: if true;
         allow write: if request.auth != null; // Requiere autenticación para escribir
       }
     }
   }
   ```

   **Nota**: Para desarrollo, puedes usar reglas más permisivas temporalmente:

   ```javascript
   allow read, write: if true;
   ```

3. **Subir Imágenes**

   **Opción A - Desde la Web App:**

   - Al crear un libro, usa el botón "📷 Subir Imagen del Libro"
   - Selecciona una imagen (máx. 5MB)
   - La imagen se subirá automáticamente a Firebase Storage

   **Opción B - Manualmente:**

   - Sube las imágenes a Firebase Storage en la carpeta `books/`
   - Nombra cada imagen con el ISBN del libro (ej: `9781234567890.jpg`)
   - El sistema las encontrará automáticamente al cargar los libros

También puedes proporcionar una URL de imagen personalizada al crear o actualizar un libro.
