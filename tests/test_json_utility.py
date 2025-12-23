import os
import json
import unittest
import sys
import tempfile
import shutil

# Add the project root to sys.path to import project_utilities
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from project_utilities.json_utility import JsonUtility

class TestJsonUtility(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_save_and_load_json(self):
        test_file = os.path.join(self.test_dir, "test.json")
        data = {"key": "value", "number": 123}
        
        # Test saving
        self.assertTrue(JsonUtility.save_to_json(test_file, data))
        self.assertTrue(os.path.exists(test_file))
        
        # Test loading
        loaded_data = JsonUtility.load_from_json(test_file)
        self.assertEqual(loaded_data, data)

    def test_load_non_existent_file(self):
        self.assertIsNone(JsonUtility.load_from_json("non_existent_file.json"))

    def test_load_corrupted_json(self):
        test_file = os.path.join(self.test_dir, "corrupted.json")
        with open(test_file, 'w') as f:
            f.write("{invalid json")
        
        self.assertIsNone(JsonUtility.load_from_json(test_file))

    def test_atomic_write_simulation(self):
        test_file = os.path.join(self.test_dir, "atomic.json")
        initial_data = {"version": 1}
        JsonUtility.save_to_json(test_file, initial_data)
        
        # Verify update
        new_data = {"version": 2}
        self.assertTrue(JsonUtility.save_to_json(test_file, new_data))
        
        loaded_data = JsonUtility.load_from_json(test_file)
        self.assertEqual(loaded_data, new_data)
        
        # Check for leftover temp files
        temp_files = [f for f in os.listdir(self.test_dir) if f.startswith(".tmp")]
        self.assertEqual(len(temp_files), 0)

    def test_save_to_new_directory(self):
        new_dir = os.path.join(self.test_dir, "subdir")
        test_file = os.path.join(new_dir, "test.json")
        data = {"key": "value"}
        
        self.assertTrue(JsonUtility.save_to_json(test_file, data))
        self.assertTrue(os.path.exists(test_file))
        self.assertEqual(JsonUtility.load_from_json(test_file), data)

if __name__ == "__main__":
    unittest.main()
