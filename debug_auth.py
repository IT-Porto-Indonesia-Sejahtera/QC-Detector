import sys
import os
from app.utils.auth_utils import AuthUtils

def main():
    """Debug utility to generate hashes for settings/admin passwords."""
    print("QC-Detector Password Hash Debugger")
    print("----------------------------------")
    
    # Check if salt and key are set
    salt = AuthUtils.get_salt()
    key = AuthUtils.get_key()
    
    print(f"Using Salt: {salt}")
    print(f"Using Key:  {key}")
    print("----------------------------------")
    
    while True:
        password = input("\nEnter password to hash (or 'q' to quit): ")
        if password.lower() == 'q':
            break
            
        hashed = AuthUtils.hash_password(password)
        print(f"Generated Hash: {hashed}")
        print("\nAdd this hash to your .env file as:")
        print(f"SETTING_PASS_HASH={hashed}")
        print("OR")
        print(f"ADMIN_PASS_HASH={hashed}")

if __name__ == "__main__":
    main()
