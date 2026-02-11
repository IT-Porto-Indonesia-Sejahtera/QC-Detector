import hashlib
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AuthUtils:
    """Utility class for password hashing and verification."""
    
    @staticmethod
    def get_salt():
        """Retrieve salt from environment variables."""
        return os.getenv("PASS_SALT", "default_salt_value")
    
    @staticmethod
    def get_key():
        """Retrieve secret key from environment variables."""
        return os.getenv("PASS_KEY", "default_secret_key")

    @staticmethod
    def hash_password(password):
        """
        Generate a salted SHA-256 hash of the password.
        Uses both PASS_SALT and PASS_KEY for integrated security.
        """
        salt = AuthUtils.get_salt()
        key = AuthUtils.get_key()
        
        # Combine salt, key, and password
        data = f"{salt}{password}{key}".encode('utf-8')
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def verify_password(password, stored_hash):
        """Verify if the provided password matches the stored hash."""
        if not stored_hash:
            return False
        return AuthUtils.hash_password(password) == stored_hash

    @staticmethod
    def get_setting_hash():
        """Get the hash for settings access from environment."""
        return os.getenv("SETTING_PASS_HASH")

    @staticmethod
    def get_admin_hash():
        """Get the hash for admin/preset access from environment."""
        return os.getenv("ADMIN_PASS_HASH")
