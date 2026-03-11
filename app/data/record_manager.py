"""
RecordManager — per-preset record persistence.
Each record stores a snapshot of WO info + granular counts.
Records are independent from presets: deleting a preset does NOT delete its record.
"""

import os
import uuid
from datetime import datetime
from project_utilities.json_utility import JsonUtility

RECORDS_FILE = os.path.join("output", "settings", "records.json")

# Default empty counts structure
DEFAULT_COUNTS = {
    "GOOD 1": 0,
    "GOOD 2": 0,
    "OVEN 1": 0,
    "OVEN 2": 0,
    "REJECT (UNDER)": 0,
    "REJECT (OVER)": 0,
    "TOTAL GOOD": 0,
    "TOTAL OVEN": 0,
    "TOTAL BS": 0,
}


class RecordManager:
    """Manages per-preset QC records (good/oven/bs counts)."""

    @staticmethod
    def _load():
        try:
            return JsonUtility.load_from_json(RECORDS_FILE) or []
        except Exception:
            return []

    @staticmethod
    def _save(records):
        JsonUtility.save_to_json(RECORDS_FILE, records)

    @classmethod
    def get_all_records(cls):
        return cls._load()

    @classmethod
    def get_record_by_preset_id(cls, preset_id):
        """Find the active/latest record for a preset."""
        if not preset_id:
            return None
        records = cls._load()
        for r in records:
            if r.get("preset_id") == preset_id:
                return r
        return None

    @classmethod
    def get_or_create_record(cls, preset):
        """Get existing record for a preset, or create a new one from WO snapshot."""
        if not preset:
            return None

        preset_id = preset.get("id")
        if not preset_id:
            return None

        existing = cls.get_record_by_preset_id(preset_id)
        if existing:
            return existing

        # Create new record with WO snapshot
        record = {
            "id": str(uuid.uuid4()),
            "preset_id": preset_id,
            "wo_number": preset.get("wo_number", preset.get("name", "Untitled")),
            "machine": preset.get("machine", ""),
            "plant": preset.get("plant", ""),
            "shift": preset.get("shift", ""),
            "production_date": preset.get("production_date", ""),
            "mps": preset.get("mps", ""),
            "status": "active",
            "started_at": datetime.now().strftime("%d/%m/%Y, %H:%M:%S"),
            "finished_at": None,
            "counts": dict(DEFAULT_COUNTS),
        }

        records = cls._load()
        records.append(record)
        cls._save(records)
        return record

    @classmethod
    def update_counts(cls, preset_id, counts, per_sku_counts=None):
        """Update the counts dict for a preset's record."""
        if not preset_id:
            return
        records = cls._load()
        for r in records:
            if r.get("preset_id") == preset_id:
                r["counts"] = dict(counts)
                if per_sku_counts is not None:
                    r["per_sku_counts"] = dict(per_sku_counts)
                break
        cls._save(records)

    @classmethod
    def finalize_record(cls, preset_id):
        """Mark a record as done with a finished_at timestamp."""
        if not preset_id:
            return
        records = cls._load()
        for r in records:
            if r.get("preset_id") == preset_id:
                r["status"] = "done"
                r["finished_at"] = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
                break
        cls._save(records)

    @classmethod
    def delete_record(cls, record_id):
        """Delete a record by its own ID (not preset_id)."""
        if not record_id:
            return
        records = cls._load()
        records = [r for r in records if r.get("id") != record_id]
        cls._save(records)
