from flask import Blueprint, request, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
import pymysql
from db import get_conn
from xml_utils import books_to_xml, create_error_xml, create_success_xml
from firebase_storage import get_image_url_by_isbn

bp = Blueprint("books", __name__)

@bp.route('/books', methods=['GET'])
@jwt_required()
def get_all_books():
    """Get all books.
    ---
    tags:
      - Books
    summary: Obtener todos los libros
    description: Retorna una lista de todos los libros ordenados por título. Requiere autenticación JWT.
    security:
      - Bearer: []
    produces:
      - application/xml
    responses:
      200:
        description: Lista de libros en formato XML
        schema:
          type: string
          example: |
            <?xml version="1.0" ?>
            <libros>
              <libro>
                <id>1</id>
                <isbn>1234567890</isbn>
                <titulo>El Quijote</titulo>
                <autor>Miguel de Cervantes</autor>
                <formato>Físico</formato>
                <precio>25.99</precio>
              </libro>
            </libros>
      401:
        description: No autenticado o token inválido
      500:
        description: Error interno del servidor
    """
    try:
        conn = get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM libros ORDER BY titulo")
            books = cursor.fetchall()
            
            # Skip Firebase image lookup for performance - images will be loaded client-side if needed
            # This makes the API response much faster
            # If you want to enable server-side image lookup, uncomment below:
            # for book in books:
            #     if 'isbn' in book and book['isbn']:
            #         if 'imagen_url' not in book or not book.get('imagen_url'):
            #             image_url = get_image_url_by_isbn(book['isbn'])
            #             if image_url:
            #                 book['imagen_url'] = image_url
            
            xml_response = books_to_xml(books)
            return Response(xml_response, mimetype='application/xml')
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        error_xml = create_error_xml(f"Error retrieving books: {str(e)}")
        return Response(error_xml, mimetype='application/xml'), 500

@bp.route('/books/ISBN', methods=['GET'])
@jwt_required()
def get_book_by_isbn():
    """Get book by ISBN.
    ---
    tags:
      - Books
    summary: Buscar libro por ISBN
    description: Retorna un libro específico basado en su ISBN. Requiere autenticación JWT.
    security:
      - Bearer: []
    parameters:
      - in: query
        name: isbn
        type: string
        required: true
        description: ISBN del libro a buscar
        example: "1234567890"
    produces:
      - application/xml
    responses:
      200:
        description: Libro encontrado en formato XML
        schema:
          type: string
          example: |
            <?xml version="1.0" ?>
            <libros>
              <libro>
                <id>1</id>
                <isbn>1234567890</isbn>
                <titulo>El Quijote</titulo>
                <autor>Miguel de Cervantes</autor>
                <formato>Físico</formato>
                <precio>25.99</precio>
              </libro>
            </libros>
      400:
        description: Parámetro ISBN faltante
      401:
        description: No autenticado o token inválido
      404:
        description: Libro no encontrado
      500:
        description: Error interno del servidor
    """
    try:
        isbn = request.args.get('isbn')
        if not isbn:
            error_xml = create_error_xml("ISBN parameter is required")
            return Response(error_xml, mimetype='application/xml'), 400
        
        conn = get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM libros WHERE isbn = %s", (isbn,))
            book = cursor.fetchone()
            
            if book:
                # Skip Firebase lookup for performance - images loaded client-side
                xml_response = books_to_xml([book])
                return Response(xml_response, mimetype='application/xml')
            else:
                error_xml = create_error_xml("Book not found")
                return Response(error_xml, mimetype='application/xml'), 404
                
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        error_xml = create_error_xml(f"Error retrieving book: {str(e)}")
        return Response(error_xml, mimetype='application/xml'), 500

@bp.route('/books/format/', methods=['GET'])
@jwt_required()
def get_books_by_format():
    """Get books by format.
    ---
    tags:
      - Books
    summary: Buscar libros por formato
    description: Retorna libros filtrados por formato (Físico, Digital, Audiolibro). Requiere autenticación JWT.
    security:
      - Bearer: []
    parameters:
      - in: query
        name: format
        type: string
        required: true
        enum: [Físico, Digital, Audiolibro]
        description: Formato del libro
        example: "Físico"
    produces:
      - application/xml
    responses:
      200:
        description: Lista de libros en formato XML
      400:
        description: Parámetro format faltante
      401:
        description: No autenticado o token inválido
      500:
        description: Error interno del servidor
    """
    try:
        format_type = request.args.get('format')
        if not format_type:
            error_xml = create_error_xml("Format parameter is required")
            return Response(error_xml, mimetype='application/xml'), 400
        
        conn = get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM libros WHERE formato = %s ORDER BY titulo", (format_type,))
            books = cursor.fetchall()
            
            # Skip Firebase lookup for performance - images loaded client-side
            xml_response = books_to_xml(books)
            return Response(xml_response, mimetype='application/xml')
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        error_xml = create_error_xml(f"Error retrieving books by format: {str(e)}")
        return Response(error_xml, mimetype='application/xml'), 500

@bp.route('/books/autor/', methods=['GET'])
@jwt_required()
def get_books_by_author():
    """Get books by author name.
    ---
    tags:
      - Books
    summary: Buscar libros por autor
    description: Retorna libros filtrados por nombre de autor (búsqueda parcial). Requiere autenticación JWT.
    security:
      - Bearer: []
    parameters:
      - in: query
        name: name
        type: string
        required: true
        description: Nombre del autor (búsqueda parcial)
        example: "Cervantes"
    produces:
      - application/xml
    responses:
      200:
        description: Lista de libros en formato XML
      400:
        description: Parámetro name faltante
      401:
        description: No autenticado o token inválido
      500:
        description: Error interno del servidor
    """
    try:
        author_name = request.args.get('name')
        if not author_name:
            error_xml = create_error_xml("Name parameter is required")
            return Response(error_xml, mimetype='application/xml'), 400
        
        conn = get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM libros WHERE autor LIKE %s ORDER BY titulo", (f"%{author_name}%",))
            books = cursor.fetchall()
            
            # Skip Firebase lookup for performance - images loaded client-side
            xml_response = books_to_xml(books)
            return Response(xml_response, mimetype='application/xml')
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        error_xml = create_error_xml(f"Error retrieving books by author: {str(e)}")
        return Response(error_xml, mimetype='application/xml'), 500

@bp.route('/books/create', methods=['POST'])
@jwt_required()
def create_book():
    """Create a new book.
    ---
    tags:
      - Books
    summary: Crear un nuevo libro
    description: Crea un nuevo libro en el sistema. Requiere autenticación JWT.
    security:
      - Bearer: []
    consumes:
      - application/json
    produces:
      - application/xml
    parameters:
      - in: body
        name: body
        description: Datos del libro a crear
        required: true
        schema:
          type: object
          required:
            - isbn
            - titulo
            - autor
            - formato
            - precio
          properties:
            isbn:
              type: string
              description: ISBN único del libro
              example: "1234567890"
            titulo:
              type: string
              description: Título del libro
              example: "El Quijote"
            autor:
              type: string
              description: Nombre del autor
              example: "Miguel de Cervantes"
            formato:
              type: string
              enum: [Físico, Digital, Audiolibro]
              description: Formato del libro
              example: "Físico"
            precio:
              type: number
              format: float
              description: Precio del libro
              example: 25.99
            descripcion:
              type: string
              description: Descripción del libro (opcional)
              example: "Una novela clásica de la literatura española"
            imagen_url:
              type: string
              description: URL de la imagen del libro (opcional)
              example: "https://example.com/image.jpg"
    responses:
      201:
        description: Libro creado exitosamente
        schema:
          type: string
          example: |
            <?xml version="1.0" ?>
            <success>Book created successfully</success>
      400:
        description: Datos faltantes o inválidos
      401:
        description: No autenticado o token inválido
      409:
        description: Libro con este ISBN ya existe
      500:
        description: Error interno del servidor
    """
    try:
        data = request.get_json()
        
        required_fields = ['isbn', 'titulo', 'autor', 'formato', 'precio']
        for field in required_fields:
            if field not in data:
                error_xml = create_error_xml(f"Field '{field}' is required")
                return Response(error_xml, mimetype='application/xml'), 400
        
        conn = get_conn()
        cursor = conn.cursor()
        
        try:
            # Get image URL from Firebase Storage if not provided (skip if not configured)
            imagen_url = data.get('imagen_url')
            # Skip Firebase lookup for performance - images can be uploaded via frontend
            # if not imagen_url:
            #     imagen_url = get_image_url_by_isbn(data['isbn'])
            
            # Try to insert with imagen_url, fallback if column doesn't exist
            try:
                cursor.execute("""
                    INSERT INTO libros (isbn, titulo, autor, formato, precio, descripcion, imagen_url)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    data['isbn'],
                    data['titulo'],
                    data['autor'],
                    data['formato'],
                    data['precio'],
                    data.get('descripcion', ''),
                    imagen_url or ''
                ))
            except pymysql.OperationalError as e:
                # If imagen_url column doesn't exist, insert without it
                if 'imagen_url' in str(e).lower():
                    cursor.execute("""
                        INSERT INTO libros (isbn, titulo, autor, formato, precio, descripcion)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        data['isbn'],
                        data['titulo'],
                        data['autor'],
                        data['formato'],
                        data['precio'],
                        data.get('descripcion', '')
                    ))
                else:
                    raise
            
            conn.commit()
            
            success_xml = create_success_xml("Book created successfully")
            return Response(success_xml, mimetype='application/xml'), 201
            
        except pymysql.IntegrityError:
            error_xml = create_error_xml("Book with this ISBN already exists")
            return Response(error_xml, mimetype='application/xml'), 409
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        error_xml = create_error_xml(f"Error creating book: {str(e)}")
        return Response(error_xml, mimetype='application/xml'), 500

@bp.route('/books/update', methods=['PUT'])
@jwt_required()
def update_book():
    """Update an existing book.
    ---
    tags:
      - Books
    summary: Actualizar un libro existente
    description: Actualiza los campos de un libro existente. Requiere autenticación JWT.
    security:
      - Bearer: []
    consumes:
      - application/json
    produces:
      - application/xml
    parameters:
      - in: body
        name: body
        description: Datos del libro a actualizar
        required: true
        schema:
          type: object
          required:
            - isbn
          properties:
            isbn:
              type: string
              description: ISBN del libro a actualizar
              example: "1234567890"
            titulo:
              type: string
              description: Nuevo título (opcional)
              example: "El Quijote - Edición Especial"
            autor:
              type: string
              description: Nuevo autor (opcional)
            formato:
              type: string
              enum: [Físico, Digital, Audiolibro]
              description: Nuevo formato (opcional)
            precio:
              type: number
              format: float
              description: Nuevo precio (opcional)
            descripcion:
              type: string
              description: Nueva descripción (opcional)
            imagen_url:
              type: string
              description: Nueva URL de imagen (opcional)
    responses:
      200:
        description: Libro actualizado exitosamente
        schema:
          type: string
          example: |
            <?xml version="1.0" ?>
            <success>Book updated successfully</success>
      400:
        description: ISBN faltante o ningún campo para actualizar
      401:
        description: No autenticado o token inválido
      404:
        description: Libro no encontrado
      500:
        description: Error interno del servidor
    """
    try:
        data = request.get_json()
        
        if 'isbn' not in data:
            error_xml = create_error_xml("ISBN is required for update")
            return Response(error_xml, mimetype='application/xml'), 400
        
        conn = get_conn()
        cursor = conn.cursor()
        
        try:
            # Check if book exists
            cursor.execute("SELECT id FROM libros WHERE isbn = %s", (data['isbn'],))
            if not cursor.fetchone():
                error_xml = create_error_xml("Book not found")
                return Response(error_xml, mimetype='application/xml'), 404
            
            # Update book
            update_fields = []
            values = []
            
            # Handle imagen_url - skip Firebase lookup for performance
            imagen_url = data.get('imagen_url', '')
            # Skip Firebase lookup - images can be uploaded via frontend
            # if not imagen_url:
            #     imagen_url = get_image_url_by_isbn(data['isbn'])
            
            for field in ['titulo', 'autor', 'formato', 'precio', 'descripcion', 'imagen_url']:
                if field in data or (field == 'imagen_url' and imagen_url):
                    update_fields.append(f"{field} = %s")
                    if field == 'imagen_url' and field not in data:
                        values.append(imagen_url or '')
                    else:
                        values.append(data.get(field, ''))
            
            if not update_fields:
                error_xml = create_error_xml("No fields to update")
                return Response(error_xml, mimetype='application/xml'), 400
            
            values.append(data['isbn'])
            
            # Try to update with imagen_url, fallback if column doesn't exist
            try:
                query = f"UPDATE libros SET {', '.join(update_fields)} WHERE isbn = %s"
                cursor.execute(query, values)
            except pymysql.OperationalError as e:
                # If imagen_url column doesn't exist, remove it from update
                if 'imagen_url' in str(e).lower():
                    update_fields_filtered = [f for f in update_fields if 'imagen_url' not in f]
                    values_filtered = [v for i, v in enumerate(values[:-1]) if 'imagen_url' not in update_fields[i]]
                    values_filtered.append(values[-1])  # Add ISBN back
                    
                    if update_fields_filtered:
                        query = f"UPDATE libros SET {', '.join(update_fields_filtered)} WHERE isbn = %s"
                        cursor.execute(query, values_filtered)
                    else:
                        error_xml = create_error_xml("No fields to update")
                        return Response(error_xml, mimetype='application/xml'), 400
                else:
                    raise
            
            conn.commit()
            
            success_xml = create_success_xml("Book updated successfully")
            return Response(success_xml, mimetype='application/xml'), 200
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        error_xml = create_error_xml(f"Error updating book: {str(e)}")
        return Response(error_xml, mimetype='application/xml'), 500

@bp.route('/books/delete', methods=['DELETE'])
@jwt_required()
def delete_book():
    """Delete a book by ISBN.
    ---
    tags:
      - Books
    summary: Eliminar un libro
    description: Elimina un libro del sistema usando su ISBN. Requiere autenticación JWT.
    security:
      - Bearer: []
    parameters:
      - in: query
        name: isbn
        type: string
        required: true
        description: ISBN del libro a eliminar
        example: "1234567890"
    produces:
      - application/xml
    responses:
      200:
        description: Libro eliminado exitosamente
        schema:
          type: string
          example: |
            <?xml version="1.0" ?>
            <success>Book deleted successfully</success>
      400:
        description: Parámetro ISBN faltante
      401:
        description: No autenticado o token inválido
      404:
        description: Libro no encontrado
      500:
        description: Error interno del servidor
    """
    try:
        isbn = request.args.get('isbn')
        if not isbn:
            error_xml = create_error_xml("ISBN parameter is required")
            return Response(error_xml, mimetype='application/xml'), 400
        
        conn = get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM libros WHERE isbn = %s", (isbn,))
            conn.commit()
            
            if cursor.rowcount == 0:
                error_xml = create_error_xml("Book not found")
                return Response(error_xml, mimetype='application/xml'), 404
            
            success_xml = create_success_xml("Book deleted successfully")
            return Response(success_xml, mimetype='application/xml'), 200
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        error_xml = create_error_xml(f"Error deleting book: {str(e)}")
        return Response(error_xml, mimetype='application/xml'), 500


