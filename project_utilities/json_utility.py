
import json
import os
import tempfile
from typing import Any, Dict, Optional

class JsonUtility:
    @staticmethod
    def save_to_json(path: str, data: Any) -> bool:
        """
        Save data to a JSON file atomically.
        Creates directories if they don't exist.
        Returns True if successful, False otherwise.
        """
        try:
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            # Use a temporary file for atomic write
            fd, temp_path = tempfile.mkstemp(dir=directory, prefix=".tmp", suffix=".json")
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                
                # Atomically replace the target file
                os.replace(temp_path, path)
                return True
            except Exception as e:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise e
                
        except Exception as e:
            print(f"Error saving to JSON {path}: {e}")
            return False

    @staticmethod
    def load_from_json(path: str) -> Optional[Any]:
        """
        Load data from a JSON file.
        Returns the data if successful, None otherwise.
        """
        if not os.path.exists(path):
            return None
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"JSON format error in {path}: {e}")
            return None
        except Exception as e:
            print(f"Error loading from JSON {path}: {e}")
            return None
