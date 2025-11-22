// API Configuration
const API_BASE_URL = "http://127.0.0.1:5000";
let accessToken = localStorage.getItem("accessToken");
let refreshToken = localStorage.getItem("refreshToken");
let currentUser = localStorage.getItem("currentUser");

// Initialize app
document.addEventListener("DOMContentLoaded", function () {
  if (accessToken && currentUser) {
    showMainContent();
    loadBooks();
  } else {
    showLoginForm();
  }

  // Set up automatic token refresh
  setInterval(refreshTokenIfNeeded, 5 * 60 * 1000); // Check every 5 minutes
});

// Utility functions
function log(message, type = "info") {
  const logContent = document.getElementById("log-content");
  const timestamp = new Date().toLocaleTimeString();
  const logEntry = document.createElement("div");
  logEntry.className = `log-entry log-${type}`;
  logEntry.textContent = `[${timestamp}] ${message}`;
  logContent.appendChild(logEntry);
  logContent.scrollTop = logContent.scrollHeight;
}

function showLoginForm() {
  document.getElementById("login-form").style.display = "block";
  document.getElementById("register-form").style.display = "none";
  document.getElementById("user-info").style.display = "none";
  document.getElementById("main-content").style.display = "none";
}

function showRegisterForm() {
  document.getElementById("login-form").style.display = "none";
  document.getElementById("register-form").style.display = "block";
  document.getElementById("user-info").style.display = "none";
  document.getElementById("main-content").style.display = "none";
}

function showMainContent() {
  document.getElementById("login-form").style.display = "none";
  document.getElementById("register-form").style.display = "none";
  document.getElementById("user-info").style.display = "block";
  document.getElementById("main-content").style.display = "block";
  document.getElementById(
    "welcome-user"
  ).textContent = `Bienvenido, ${currentUser}`;
}

function showLogin() {
  showLoginForm();
}

function showRegister() {
  showRegisterForm();
}

// Authentication functions
async function login() {
  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;

  if (!username || !password) {
    log("Por favor, complete todos los campos", "error");
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, password }),
    });

    const data = await response.json();

    if (response.ok) {
      accessToken = data.access_token;
      refreshToken = data.refresh_token;
      currentUser = data.username;

      localStorage.setItem("accessToken", accessToken);
      localStorage.setItem("refreshToken", refreshToken);
      localStorage.setItem("currentUser", currentUser);

      log(`Login exitoso para usuario: ${currentUser}`, "success");
      showMainContent();
      loadBooks();
    } else {
      log(`Error en login: ${data.error}`, "error");
    }
  } catch (error) {
    log(`Error de conexión: ${error.message}`, "error");
  }
}

async function register() {
  const username = document.getElementById("reg-username").value;
  const password = document.getElementById("reg-password").value;

  if (!username || !password) {
    log("Por favor, complete todos los campos", "error");
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, password }),
    });

    const data = await response.json();

    if (response.ok) {
      log(`Usuario registrado exitosamente: ${username}`, "success");
      showLoginForm();
      document.getElementById("username").value = username;
    } else {
      log(`Error en registro: ${data.error}`, "error");
    }
  } catch (error) {
    log(`Error de conexión: ${error.message}`, "error");
  }
}

async function logout() {
  try {
    await fetch(`${API_BASE_URL}/auth/logout`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
  } catch (error) {
    log(`Error en logout: ${error.message}`, "warning");
  }

  // Clear local storage
  localStorage.removeItem("accessToken");
  localStorage.removeItem("refreshToken");
  localStorage.removeItem("currentUser");

  accessToken = null;
  refreshToken = null;
  currentUser = null;

  log("Sesión cerrada", "info");
  showLoginForm();
}

async function refreshTokenIfNeeded() {
  if (!refreshToken) return;

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${refreshToken}`,
      },
    });

    if (response.ok) {
      const data = await response.json();
      accessToken = data.access_token;
      localStorage.setItem("accessToken", accessToken);
      log("Token de acceso renovado automáticamente", "info");
    } else {
      log(
        "Error al renovar token, será necesario volver a iniciar sesión",
        "warning"
      );
    }
  } catch (error) {
    log(`Error al renovar token: ${error.message}`, "error");
  }
}

// API request helper
async function makeAuthenticatedRequest(url, options = {}) {
  const defaultOptions = {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
      ...options.headers,
    },
  };

  const response = await fetch(url, { ...defaultOptions, ...options });

  if (response.status === 401) {
    log("Token expirado, intentando renovar...", "warning");
    await refreshTokenIfNeeded();

    if (accessToken) {
      // Retry with new token
      defaultOptions.headers["Authorization"] = `Bearer ${accessToken}`;
      return await fetch(url, { ...defaultOptions, ...options });
    } else {
      log("No se pudo renovar el token, redirigiendo al login", "error");
      logout();
      return null;
    }
  }

  return response;
}

// Book management functions
async function loadBooks() {
  try {
    log("Solicitando libros al servidor...", "info");
    const response = await makeAuthenticatedRequest(
      `${API_BASE_URL}/api/books`
    );

    if (!response) {
      log("No se recibió respuesta del servidor", "error");
      return;
    }

    log(`Respuesta recibida: Status ${response.status}`, "info");

    const xmlText = await response.text();
    log(
      `XML recibido (${xmlText.length} caracteres): ${xmlText.substring(
        0,
        200
      )}...`,
      "info"
    );

    if (!response.ok) {
      log(`Error del servidor: ${response.status} - ${xmlText}`, "error");
      return;
    }

    const books = parseXMLBooks(xmlText);
    log(`Libros parseados: ${books.length}`, "info");
    log(`Datos de libros: ${JSON.stringify(books)}`, "info");

    if (books && books.length > 0) {
      displayBooks(books);
      log(`Cargados ${books.length} libros exitosamente`, "success");
    } else {
      log("No se encontraron libros o hubo un error al parsear", "warning");
      document.getElementById("books-list").innerHTML =
        "<p>No se encontraron libros</p>";
    }
  } catch (error) {
    log(`Error al cargar libros: ${error.message}`, "error");
    console.error("Error completo:", error);
  }
}

async function searchByISBN() {
  const isbn = document.getElementById("search-isbn").value;
  if (!isbn) {
    log("Por favor, ingrese un ISBN", "error");
    return;
  }

  try {
    const response = await makeAuthenticatedRequest(
      `${API_BASE_URL}/api/books/ISBN?isbn=${encodeURIComponent(isbn)}`
    );
    if (!response) return;

    const xmlText = await response.text();
    const books = parseXMLBooks(xmlText);

    displayBooks(books);
    log(`Búsqueda por ISBN: ${isbn} - ${books.length} resultados`, "info");
  } catch (error) {
    log(`Error en búsqueda por ISBN: ${error.message}`, "error");
  }
}

async function searchByAuthor() {
  const author = document.getElementById("search-author").value;
  if (!author) {
    log("Por favor, ingrese un nombre de autor", "error");
    return;
  }

  try {
    const response = await makeAuthenticatedRequest(
      `${API_BASE_URL}/api/books/autor/?name=${encodeURIComponent(author)}`
    );
    if (!response) return;

    const xmlText = await response.text();
    const books = parseXMLBooks(xmlText);

    displayBooks(books);
    log(`Búsqueda por autor: ${author} - ${books.length} resultados`, "info");
  } catch (error) {
    log(`Error en búsqueda por autor: ${error.message}`, "error");
  }
}

async function searchByFormat() {
  const format = document.getElementById("search-format").value;
  if (!format) {
    log("Por favor, seleccione un formato", "error");
    return;
  }

  try {
    const response = await makeAuthenticatedRequest(
      `${API_BASE_URL}/api/books/format/?format=${encodeURIComponent(format)}`
    );
    if (!response) return;

    const xmlText = await response.text();
    const books = parseXMLBooks(xmlText);

    displayBooks(books);
    log(`Búsqueda por formato: ${format} - ${books.length} resultados`, "info");
  } catch (error) {
    log(`Error en búsqueda por formato: ${error.message}`, "error");
  }
}

async function createBook() {
  try {
    log("Iniciando creación de libro...", "info");

    // Get all field values
    const isbnElement = document.getElementById("create-isbn");
    const titleElement = document.getElementById("create-title");
    const authorElement = document.getElementById("create-author");
    const formatElement = document.getElementById("create-format");
    const priceElement = document.getElementById("create-price");
    const descriptionElement = document.getElementById("create-description");
    const imageUrlElement = document.getElementById("create-image-url");
    const imageFileElement = document.getElementById("create-image-file");

    // Check if elements exist
    if (
      !isbnElement ||
      !titleElement ||
      !authorElement ||
      !formatElement ||
      !priceElement
    ) {
      log("Error: No se pudieron encontrar los campos del formulario", "error");
      console.error("Elementos faltantes:", {
        isbn: !!isbnElement,
        title: !!titleElement,
        author: !!authorElement,
        format: !!formatElement,
        price: !!priceElement,
      });
      return;
    }

    const isbn = isbnElement.value.trim();
    const title = titleElement.value.trim();
    const author = authorElement.value.trim();
    const format = formatElement.value;
    const price = priceElement.value.trim();
    const description = descriptionElement
      ? descriptionElement.value.trim()
      : "";
    const imageUrl = imageUrlElement ? imageUrlElement.value.trim() : "";
    const imageFile = imageFileElement ? imageFileElement.files[0] : null;

    // Debug: Log all field values with detailed info
    log(`=== Validando Campos ===`, "info");
    log(`ISBN: "${isbn}" (longitud: ${isbn.length})`, "info");
    log(`Título: "${title}" (longitud: ${title.length})`, "info");
    log(`Autor: "${author}" (longitud: ${author.length})`, "info");
    log(`Formato: "${format}" (seleccionado: ${format !== ""})`, "info");
    log(
      `Precio: "${price}" (tipo: ${typeof price}, numérico: ${!isNaN(
        parseFloat(price)
      )})`,
      "info"
    );

    // Check each field individually and log which one is missing
    const missingFields = [];

    if (!isbn || isbn.length === 0) {
      missingFields.push("ISBN");
    }
    if (!title || title.length === 0) {
      missingFields.push("Título");
    }
    if (!author || author.length === 0) {
      missingFields.push("Autor");
    }
    if (!format || format === "" || format === "Seleccionar Formato") {
      missingFields.push("Formato");
    }
    if (
      !price ||
      price.length === 0 ||
      isNaN(parseFloat(price)) ||
      parseFloat(price) <= 0
    ) {
      missingFields.push("Precio");
    }

    if (missingFields.length > 0) {
      log(
        `Error: Faltan los siguientes campos: ${missingFields.join(", ")}`,
        "error"
      );
      return;
    }

    // Check if user is authenticated
    if (!accessToken) {
      log("Debe iniciar sesión para crear libros", "error");
      showLoginForm();
      return;
    }

    let finalImageUrl = imageUrl;

    // Upload image file to Firebase Storage if provided
    if (imageFile) {
      if (window.firebaseStorage && window.firebaseStorage.uploadImage) {
        try {
          log("Subiendo imagen a Firebase Storage...", "info");
          finalImageUrl = await window.firebaseStorage.uploadImage(
            imageFile,
            isbn
          );
          log("Imagen subida exitosamente", "success");
        } catch (error) {
          log(`Error al subir imagen: ${error.message}`, "error");
          // Continue with book creation even if image upload fails
        }
      } else {
        log(
          "Firebase Storage no está disponible. Continuando sin imagen...",
          "warning"
        );
      }
    }

    const bookData = {
      isbn,
      titulo: title,
      autor: author,
      formato: format,
      precio: parseFloat(price),
      descripcion: description,
    };

    // Add image URL if provided
    if (finalImageUrl) {
      bookData.imagen_url = finalImageUrl;
    }

    log(`Enviando datos del libro: ${JSON.stringify(bookData)}`, "info");

    const response = await makeAuthenticatedRequest(
      `${API_BASE_URL}/api/books/create`,
      {
        method: "POST",
        body: JSON.stringify(bookData),
      }
    );

    if (!response) {
      log("No se recibió respuesta del servidor", "error");
      return;
    }

    const xmlText = await response.text();

    if (response.ok) {
      log("Libro creado exitosamente", "success");
      clearCreateForm();
      loadBooks();
    } else {
      const error = parseXMLError(xmlText);
      log(`Error al crear libro: ${error}`, "error");
    }
  } catch (error) {
    log(`Error al crear libro: ${error.message}`, "error");
    console.error("Error completo:", error);
  }
}

async function updateBook(isbn) {
  // This would open a form to edit the book
  // For simplicity, we'll just show a prompt
  const newTitle = prompt("Nuevo título:", "");
  if (!newTitle) return;

  const bookData = {
    isbn,
    titulo: newTitle,
  };

  try {
    const response = await makeAuthenticatedRequest(
      `${API_BASE_URL}/api/books/update`,
      {
        method: "PUT",
        body: JSON.stringify(bookData),
      }
    );

    if (!response) return;

    const xmlText = await response.text();

    if (response.ok) {
      log("Libro actualizado exitosamente", "success");
      loadBooks();
    } else {
      const error = parseXMLError(xmlText);
      log(`Error al actualizar libro: ${error}`, "error");
    }
  } catch (error) {
    log(`Error al actualizar libro: ${error.message}`, "error");
  }
}

async function deleteBook(isbn) {
  if (!confirm("¿Está seguro de que desea eliminar este libro?")) {
    return;
  }

  try {
    const response = await makeAuthenticatedRequest(
      `${API_BASE_URL}/api/books/delete?isbn=${encodeURIComponent(isbn)}`,
      {
        method: "DELETE",
      }
    );

    if (!response) return;

    const xmlText = await response.text();

    if (response.ok) {
      log("Libro eliminado exitosamente", "success");
      loadBooks();
    } else {
      const error = parseXMLError(xmlText);
      log(`Error al eliminar libro: ${error}`, "error");
    }
  } catch (error) {
    log(`Error al eliminar libro: ${error.message}`, "error");
  }
}

// UI helper functions
function showSearchForm() {
  document.getElementById("search-form").style.display = "block";
  document.getElementById("create-form").style.display = "none";
}

function showCreateForm() {
  document.getElementById("search-form").style.display = "none";
  document.getElementById("create-form").style.display = "block";
}

function clearCreateForm() {
  document.getElementById("create-isbn").value = "";
  document.getElementById("create-title").value = "";
  document.getElementById("create-author").value = "";
  document.getElementById("create-format").value = "";
  document.getElementById("create-price").value = "";
  document.getElementById("create-description").value = "";
  document.getElementById("create-image-url").value = "";
  document.getElementById("create-image-file").value = "";
  clearImagePreview();
}

function handleImageFileSelect(event) {
  const file = event.target.files[0];
  if (file) {
    // Validate file type
    if (!file.type.startsWith("image/")) {
      log("Por favor, seleccione un archivo de imagen válido", "error");
      event.target.value = "";
      return;
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      log("La imagen es demasiado grande. Máximo 5MB", "error");
      event.target.value = "";
      return;
    }

    // Show preview
    const reader = new FileReader();
    reader.onload = function (e) {
      const preview = document.getElementById("image-preview");
      const container = document.getElementById("image-preview-container");
      preview.src = e.target.result;
      container.style.display = "block";
    };
    reader.readAsDataURL(file);
  }
}

function clearImagePreview() {
  const container = document.getElementById("image-preview-container");
  const preview = document.getElementById("image-preview");
  container.style.display = "none";
  preview.src = "";
}

function displayBooks(books) {
  const booksList = document.getElementById("books-list");
  booksList.innerHTML = "";

  if (books.length === 0) {
    booksList.innerHTML = "<p>No se encontraron libros</p>";
    return;
  }

  // First, display all books immediately with placeholders
  for (const book of books) {
    const imageUrl = book.imagen_url || book.imagenUrl || "";
    
    const bookDiv = document.createElement("div");
    bookDiv.className = "book-item";
    bookDiv.dataset.isbn = book.isbn || "";

    const imageHtml = imageUrl
      ? `<div class="book-image-container">
           <img src="${imageUrl}" alt="${
          book.titulo || "Book cover"
        }" class="book-image" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
           <div class="book-image-placeholder" style="display: none;">📚</div>
           </div>`
      : `<div class="book-image-container">
           <div class="book-image-placeholder">📚</div>
           </div>`;

    bookDiv.innerHTML = `
            ${imageHtml}
            <div class="book-info">
              <h4>${book.titulo || "Sin título"}</h4>
              <p><strong>ISBN:</strong> ${book.isbn || "N/A"}</p>
              <p><strong>Autor:</strong> ${book.autor || "N/A"}</p>
              <p><strong>Formato:</strong> ${book.formato || "N/A"}</p>
              <p><strong>Precio:</strong> $${book.precio || "0"}</p>
              ${
                book.descripcion
                  ? `<p><strong>Descripción:</strong> ${book.descripcion}</p>`
                  : ""
              }
              <div class="book-actions">
                  <button class="edit-btn" onclick="updateBook('${
                    book.isbn
                  }')">Editar</button>
                  <button class="delete-btn" onclick="deleteBook('${
                    book.isbn
                  }')">Eliminar</button>
              </div>
            </div>
        `;
    booksList.appendChild(bookDiv);
  }

  // Then, asynchronously load images from Firebase for books without images
  // This doesn't block the display
  if (window.firebaseStorage && window.firebaseStorage.getImageUrl) {
    loadImagesAsync(books);
  }
}

// Load images asynchronously without blocking
async function loadImagesAsync(books) {
  // Process images in parallel with a limit to avoid overwhelming Firebase
  const imagePromises = [];
  
  for (const book of books) {
    const imageUrl = book.imagen_url || book.imagenUrl || "";
    
    // Only try to load if no image URL exists and ISBN is available
    if (!imageUrl && book.isbn) {
      const promise = window.firebaseStorage.getImageUrl(book.isbn)
        .then(url => {
          if (url) {
            // Find the book element and update its image
            const bookElement = document.querySelector(`[data-isbn="${book.isbn}"]`);
            if (bookElement) {
              const imageContainer = bookElement.querySelector('.book-image-container');
              if (imageContainer) {
                const placeholder = imageContainer.querySelector('.book-image-placeholder');
                if (placeholder) {
                  placeholder.style.display = 'none';
                  const img = document.createElement('img');
                  img.src = url;
                  img.alt = book.titulo || "Book cover";
                  img.className = "book-image";
                  img.onerror = function() {
                    this.style.display = 'none';
                    if (placeholder) placeholder.style.display = 'flex';
                  };
                  imageContainer.insertBefore(img, placeholder);
                }
              }
            }
          }
        })
        .catch(error => {
          // Silently fail - placeholder will remain
          console.log(`No image found for ISBN ${book.isbn}`);
        });
      
      imagePromises.push(promise);
    }
  }
  
  // Wait for all images to load (but don't block the UI)
  await Promise.allSettled(imagePromises);
}

// XML parsing functions
function parseXMLBooks(xmlText) {
  try {
    log(`Parseando XML: ${xmlText.substring(0, 500)}...`, "info");

    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(xmlText, "text/xml");

    // Check for parsing errors
    const parserError = xmlDoc.querySelector("parsererror");
    if (parserError) {
      log(`Error de parsing XML: ${parserError.textContent}`, "error");
      log(`XML completo: ${xmlText}`, "error");
      return [];
    }

    const libros = xmlDoc.getElementsByTagName("libro");
    log(`Encontrados ${libros.length} elementos <libro> en el XML`, "info");

    const books = [];

    for (let i = 0; i < libros.length; i++) {
      const libro = libros[i];
      const book = {};

      // Get all child elements
      for (let j = 0; j < libro.children.length; j++) {
        const child = libro.children[j];
        book[child.tagName] = child.textContent;
      }

      log(`Libro ${i + 1} parseado: ${JSON.stringify(book)}`, "info");
      books.push(book);
    }

    return books;
  } catch (error) {
    log(`Error al parsear XML: ${error.message}`, "error");
    console.error("Error completo de parsing:", error);
    console.error("XML que causó el error:", xmlText);
    return [];
  }
}

function parseXMLError(xmlText) {
  try {
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(xmlText, "text/xml");
    const errorElement = xmlDoc.getElementsByTagName("error")[0];
    return errorElement ? errorElement.textContent : "Error desconocido";
  } catch (error) {
    return "Error al parsear mensaje de error";
  }
}
