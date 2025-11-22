import os
import firebase_admin
from firebase_admin import credentials, storage
from dotenv import load_dotenv

load_dotenv()

# Initialize Firebase Admin SDK
_firebase_app = None

def get_firebase_app():
    """Initialize and return Firebase app instance."""
    global _firebase_app
    
    if _firebase_app is None:
        # Check if Firebase credentials are provided via environment variable
        cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH')
        
        if cred_path and os.path.exists(cred_path):
            try:
                cred = credentials.Certificate(cred_path)
                _firebase_app = firebase_admin.initialize_app(cred, {
                    'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
                })
            except Exception as e:
                print(f"Warning: Could not initialize Firebase with credentials file: {str(e)}")
                return None
        else:
            # Try to use default credentials (for Google Cloud environments)
            try:
                _firebase_app = firebase_admin.initialize_app()
            except (ValueError, Exception) as e:
                # If already initialized, try to get the existing app
                try:
                    _firebase_app = firebase_admin.get_app()
                except ValueError:
                    # Firebase not configured - this is OK, we'll work without it
                    print(f"Info: Firebase not configured: {str(e)}")
                    return None
    
    return _firebase_app

def get_image_url(image_path):
    """
    Get a public URL for an image stored in Firebase Storage.
    
    Args:
        image_path: Path to the image in Firebase Storage (e.g., 'books/isbn123.jpg')
    
    Returns:
        Public URL string or None if image doesn't exist
    """
    try:
        app = get_firebase_app()
        if app is None:
            return None  # Firebase not configured
        
        bucket = storage.bucket()
        blob = bucket.blob(image_path)
        
        # Check if blob exists
        if not blob.exists():
            return None
        
        # Generate a signed URL that lasts for 1 year
        url = blob.generate_signed_url(
            expiration=31536000,  # 1 year in seconds
            method='GET'
        )
        return url
    except Exception as e:
        # Silently fail - Firebase not configured or image doesn't exist
        return None

def get_image_url_by_isbn(isbn):
    """
    Get image URL for a book by its ISBN.
    Assumes images are stored as 'books/{isbn}.jpg' or 'books/{isbn}.png'
    
    Args:
        isbn: Book ISBN
    
    Returns:
        Public URL string or None if image doesn't exist
    """
    # Try common image extensions
    extensions = ['.jpg', '.jpeg', '.png', '.webp']
    
    for ext in extensions:
        image_path = f'books/{isbn}{ext}'
        url = get_image_url(image_path)
        if url:
            return url
    
    return None

def upload_image(file_data, image_path, content_type='image/jpeg'):
    """
    Upload an image to Firebase Storage.
    
    Args:
        file_data: Binary file data
        image_path: Path where to store the image (e.g., 'books/isbn123.jpg')
        content_type: MIME type of the image
    
    Returns:
        Public URL string or None if upload fails
    """
    try:
        app = get_firebase_app()
        if app is None:
            return None  # Firebase not configured
        
        bucket = storage.bucket()
        blob = bucket.blob(image_path)
        
        blob.upload_from_string(file_data, content_type=content_type)
        blob.make_public()
        
        return blob.public_url
    except Exception as e:
        # Silently fail - Firebase not configured
        return None

