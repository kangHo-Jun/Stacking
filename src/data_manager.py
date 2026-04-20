from __future__ import annotations

import time
import threading
import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path
import csv
import math
from exceptions import DataInvalidError

# Constants
CACHE_TTL_SECONDS = 600  # 10 minutes
SHEET_ID = "1QrMhSpTttOP1AaOSJoSrY_z5HuExSBxB8mdSxzSKPE8"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
KEY_PATH = PROJECT_ROOT / "docs" / "stacking-492708-e1c7e3daef8d.json"
VEHICLE_CSV_PATH = PROJECT_ROOT / "data" / "차량정보.csv"

# Scopes for Google Sheets API
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

class DataManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DataManager, cls).__new__(cls)
                cls._instance._init_manager()
            return cls._instance

    def _init_manager(self):
        self._material_cache = {}
        self._vehicle_cache = []
        self._material_last_updated = 0
        self._vehicle_last_updated = 0
        self._cache_lock = threading.Lock()

    def _parse_number(self, value: str) -> float | None:
        if not value:
            return None
        cleaned = str(value).strip().replace(",", "")
        if cleaned in {"", "-", "—"}:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _calculate_unit_volume_m3(self, spec: str, thickness: float | None) -> float | None:
        if not spec or thickness is None:
            return None
        # Robust parsing: remove whitespace and normalize "x", "*", or "×"
        spec_clean = str(spec).lower().replace(" ", "").replace("*", "x").replace("×", "x")
        parts = spec_clean.split("x")
        if len(parts) != 2:
            return None
        try:
            width_mm = float(parts[0])
            length_mm = float(parts[1])
            return (width_mm * length_mm * thickness) / 1_000_000_000
        except ValueError:
            return None

    def _build_material_key(self, name: str, spec: str, thickness: str) -> str:
        return f"{str(name).strip()}_{str(spec).strip()}_{str(thickness).strip()}"

    def get_material_db(self) -> dict[str, dict[str, object]]:
        current_time = time.time()
        with self._cache_lock:
            if current_time - self._material_last_updated > CACHE_TTL_SECONDS:
                self._refresh_materials()
            return self._material_cache

    def get_vehicle_db(self) -> list[dict[str, object]]:
        current_time = time.time()
        with self._cache_lock:
            if current_time - self._vehicle_last_updated > CACHE_TTL_SECONDS:
                self._refresh_vehicles()
            return self._vehicle_cache

    def _refresh_materials(self):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Refreshing materials from Google Sheets...")
        try:
            credentials = Credentials.from_service_account_file(str(KEY_PATH), scopes=SCOPES)
            gc = gspread.authorize(credentials)
            sh = gc.open_by_key(SHEET_ID)
            worksheet = sh.get_worksheet(0)
            records = worksheet.get_all_records()

            new_cache = {}
            for row in records:
                name = str(row.get("자재명", ""))
                spec = str(row.get("규격(mm)", "")).strip()
                
                # Fallback: Extract spec from name if empty (e.g. "900*1800" or "900x1800" or "900×1800")
                if not spec:
                    import re
                    # Look for WxL pattern
                    match = re.search(r"(\d+[\.\d+]*)\s*[xX*×]\s*(\d+[\.\d+]*)", name)
                    if match:
                        spec = f"{match.group(1)}x{match.group(2)}"

                thickness_str = str(row.get("두께(mm)", ""))
                width = self._parse_number(str(row.get("가로(mm)", ""))) or 1000.0
                length = self._parse_number(str(row.get("세로(mm)", ""))) or 1000.0
                thickness = self._parse_number(thickness_str)
                
                key = self._build_material_key(name, f"{width:.0f}x{length:.0f}", thickness_str)
                
                new_cache[key] = {
                    "key": key,
                    "자재명": name,
                    "width_mm": width,
                    "length_mm": length,
                    "thickness_mm": thickness or 0.0,
                    "낱장무게(kg)": self._parse_number(str(row.get("낱장무게(kg)", ""))),
                    "낱장부피(m3)": (width * length * (thickness or 0.0)) / 1_000_000_000,
                    "팔레트당적재수": int(self._parse_number(str(row.get("팔레트당적재수", "1"))) or 1),
                    "팔레트무게(kg)": self._parse_number(str(row.get("팔레트무게(kg)", ""))),
                    "취급등급": str(row.get("취급등급", "B")).strip(),
                    "stack_limit": int(self._parse_number(str(row.get("stack_limit", "1"))) or 1),
                    "delivery_group": int(self._parse_number(str(row.get("하차그룹", "0"))) or 0),
                    "mix_group": str(row.get("혼적그룹", "")).strip(),
                    "is_dead_space": str(row.get("dead_space", "N")).strip().upper() == "Y",
                    "priority": int(self._parse_number(str(row.get("priority", "3"))) or 3),
                    "적재위치": str(row.get("적재위치", "")).strip(),
                }
            
            self._material_cache = new_cache
            self._material_last_updated = time.time()
            print(f"Successfully loaded {len(new_cache)} materials.")
        except Exception as e:
            print(f"Error refreshing materials: {e}")
            raise DataInvalidError(f"CRITICAL: Failed to load material data from Google Sheets: {e}")

    def _refresh_vehicles(self):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Refreshing vehicles from CSV...")
        try:
            vehicles = []
            if not VEHICLE_CSV_PATH.exists():
                print(f"Vehicle CSV not found at {VEHICLE_CSV_PATH}")
                return

            with VEHICLE_CSV_PATH.open("r", encoding="utf-8-sig", newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    length_mm = self._parse_number(row.get("적재함길이(mm)", "0")) or 0.0
                    width_mm = self._parse_number(row.get("적재함너비(mm)", "0")) or 0.0
                    height_mm = self._parse_number(row.get("적재함높이(mm)", "0")) or 0.0
                    cargo_volume_m3 = (length_mm * width_mm * height_mm) / 1_000_000_000

                    vehicles.append({
                        "vehicle_name": row.get("차량명", "").strip(),
                        "max_weight_kg": self._parse_number(row.get("최대적재중량(kg)", "0")) or 0.0,
                        "cargo_length_mm": length_mm,
                        "cargo_width_mm": width_mm,
                        "cargo_height_mm": height_mm,
                        "cargo_volume_m3": cargo_volume_m3,
                        "axles": int(self._parse_number(row.get("축수", "1")) or 1),
                        "freight_cost_krw": int(self._parse_number(row.get("운임(원)", "0")) or 0),
                    })
            
            self._vehicle_cache = vehicles
            self._vehicle_last_updated = time.time()
            print(f"Successfully loaded {len(vehicles)} vehicles.")
        except Exception as e:
            print(f"Error refreshing vehicles: {e}")
            raise DataInvalidError(f"CRITICAL: Failed to load vehicle data from CSV: {e}")

# Global instance for ease of use
data_manager = DataManager()
