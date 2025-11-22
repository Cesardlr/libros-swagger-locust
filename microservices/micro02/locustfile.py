"""
Locust load testing configuration for Books API
Run with: locust -f locustfile.py --host=http://127.0.0.1:5000
Access web UI at: http://localhost:8089
"""

from locust import HttpUser, task, between
import random
import string
import json


class BooksAPIUser(HttpUser):
    """Simulates a user interacting with the Books API."""
    
    wait_time = between(1, 3)  # Wait between 1 and 3 seconds between tasks
    
    def on_start(self):
        """Called when a simulated user starts. Performs login."""
        self.access_token = None
        self.refresh_token = None
        self.username = None
        self.test_isbn = None
        
        # Register and login
        self.register_and_login()
    
    def register_and_login(self):
        """Register a new user and login."""
        # Generate random username
        self.username = f"testuser_{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"
        password = "testpass123"
        
        # Register
        register_response = self.client.post(
            "/auth/register",
            json={"username": self.username, "password": password},
            name="Register User"
        )
        
        if register_response.status_code in [201, 409]:  # Created or already exists
            # Login
            login_response = self.client.post(
                "/auth/login",
                json={"username": self.username, "password": password},
                name="Login"
            )
            
            if login_response.status_code == 200:
                data = login_response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
    
    @task(3)
    def get_all_books(self):
        """Get all books - most common operation."""
        if self.access_token:
            self.client.get(
                "/api/books",
                headers={"Authorization": f"Bearer {self.access_token}"},
                name="Get All Books"
            )
    
    @task(2)
    def get_book_by_isbn(self):
        """Get a book by ISBN."""
        if self.access_token and self.test_isbn:
            self.client.get(
                f"/api/books/ISBN?isbn={self.test_isbn}",
                headers={"Authorization": f"Bearer {self.access_token}"},
                name="Get Book by ISBN"
            )
    
    @task(2)
    def get_books_by_format(self):
        """Get books by format."""
        if self.access_token:
            formats = ["Físico", "Digital", "Audiolibro"]
            format_type = random.choice(formats)
            self.client.get(
                f"/api/books/format/?format={format_type}",
                headers={"Authorization": f"Bearer {self.access_token}"},
                name="Get Books by Format"
            )
    
    @task(1)
    def get_books_by_author(self):
        """Get books by author."""
        if self.access_token:
            authors = ["García", "Martínez", "López", "González", "Pérez"]
            author = random.choice(authors)
            self.client.get(
                f"/api/books/autor/?name={author}",
                headers={"Authorization": f"Bearer {self.access_token}"},
                name="Get Books by Author"
            )
    
    @task(1)
    def create_book(self):
        """Create a new book."""
        if self.access_token:
            # Generate random ISBN
            isbn = ''.join(random.choices(string.digits, k=13))
            self.test_isbn = isbn  # Store for later use
            
            book_data = {
                "isbn": isbn,
                "titulo": f"Libro de Prueba {random.randint(1, 1000)}",
                "autor": f"Autor {random.choice(['García', 'Martínez', 'López'])}",
                "formato": random.choice(["Físico", "Digital", "Audiolibro"]),
                "precio": round(random.uniform(10.0, 100.0), 2),
                "descripcion": "Libro creado durante prueba de carga"
            }
            
            response = self.client.post(
                "/api/books/create",
                json=book_data,
                headers={"Authorization": f"Bearer {self.access_token}"},
                name="Create Book"
            )
            
            # If successful, we can use this ISBN for other operations
            if response.status_code == 201:
                self.test_isbn = isbn
    
    @task(1)
    def update_book(self):
        """Update an existing book."""
        if self.access_token and self.test_isbn:
            update_data = {
                "isbn": self.test_isbn,
                "titulo": f"Libro Actualizado {random.randint(1, 1000)}",
                "precio": round(random.uniform(10.0, 100.0), 2)
            }
            
            self.client.put(
                "/api/books/update",
                json=update_data,
                headers={"Authorization": f"Bearer {self.access_token}"},
                name="Update Book"
            )
    
    @task(1)
    def delete_book(self):
        """Delete a book (less frequent operation)."""
        if self.access_token and self.test_isbn:
            # Only delete occasionally to avoid deleting all test books
            if random.random() < 0.1:  # 10% chance
                self.client.delete(
                    f"/api/books/delete?isbn={self.test_isbn}",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    name="Delete Book"
                )
                self.test_isbn = None  # Clear ISBN after deletion
    
    @task(1)
    def refresh_token(self):
        """Refresh access token."""
        if self.refresh_token:
            self.client.post(
                "/auth/refresh",
                headers={"Authorization": f"Bearer {self.refresh_token}"},
                name="Refresh Token"
            )


class UnauthenticatedUser(HttpUser):
    """Simulates unauthenticated requests (should fail)."""
    
    wait_time = between(2, 5)
    weight = 1  # Lower weight - fewer unauthenticated users
    
    @task
    def try_access_protected_endpoint(self):
        """Try to access protected endpoint without auth (should fail)."""
        self.client.get("/api/books", name="Unauthenticated Access (Expected 401)")


# Configuration for different test scenarios
class QuickTestUser(BooksAPIUser):
    """Faster test scenario."""
    wait_time = between(0.5, 1.5)
    weight = 2


class SlowTestUser(BooksAPIUser):
    """Slower, more realistic test scenario."""
    wait_time = between(3, 7)
    weight = 1

