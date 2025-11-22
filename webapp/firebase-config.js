// Firebase Configuration
// Import the functions you need from the SDKs you need
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import {
  getStorage,
  ref,
  uploadBytes,
  getDownloadURL,
} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-storage.js";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyB9mW2lbuy-hqlbXjR-hqUMPu0fqcithl0",
  authDomain: "micros-integracion-apps-libros.firebaseapp.com",
  projectId: "micros-integracion-apps-libros",
  storageBucket: "micros-integracion-apps-libros.firebasestorage.app",
  messagingSenderId: "109357092582",
  appId: "1:109357092582:web:bc64a96def494687693527",
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const storage = getStorage(app);

// Make Firebase functions available globally
window.firebaseStorage = {
  uploadImage: async (file, isbn) => {
    try {
      const fileExtension = file.name.split(".").pop();
      const imagePath = `books/${isbn}.${fileExtension}`;
      const storageRef = ref(storage, imagePath);

      // Upload file
      await uploadBytes(storageRef, file);

      // Get download URL
      const downloadURL = await getDownloadURL(storageRef);
      return downloadURL;
    } catch (error) {
      console.error("Error uploading image:", error);
      throw error;
    }
  },
  getImageUrl: async (isbn) => {
    // Try different extensions
    const extensions = ["jpg", "jpeg", "png", "webp"];
    for (const ext of extensions) {
      try {
        const imagePath = `books/${isbn}.${ext}`;
        const storageRef = ref(storage, imagePath);
        const url = await getDownloadURL(storageRef);
        return url;
      } catch (error) {
        // Check if it's a 404 (file not found) - this is normal, continue silently
        // Other errors might be logged for debugging
        if (error.code !== "storage/object-not-found") {
          console.warn(
            `Error checking for image ${isbn}.${ext}:`,
            error.message
          );
        }
        // Continue to next extension
        continue;
      }
    }
    return null;
  },
};
