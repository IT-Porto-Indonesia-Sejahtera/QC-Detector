
import json
import os
from typing import Any, Dict, Optional

class JsonUtility:
    @staticmethod
    def save_to_json(path: str, data: Any) -> bool:
        """
        Save data to a JSON file.
        Creates directories if they don't exist.
        Returns True if successful, False otherwise.
        """
        try:
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
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
        except Exception as e:
            print(f"Error loading from JSON {path}: {e}")
            return None
