"""
USDA Nutrition Database Schema
===============================
Nutrient codes: 44 (only those with actual food data)
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "usda_nutrients.db"

NUTRIENT_CODES = {
    "ENERGY": {"display_name": "Energy", "unit": "KCAL", "category": "macronutrient"},
    "PROTEIN": {"display_name": "Protein", "unit": "G", "category": "macronutrient"},
    "CARB": {"display_name": "Carbohydrate, by difference", "unit": "G", "category": "macronutrient"},
    "FAT": {"display_name": "Total lipid (fat)", "unit": "G", "category": "macronutrient"},
    "FIBER": {"display_name": "Fiber, total dietary", "unit": "G", "category": "macronutrient"},
    "WATER": {"display_name": "Water", "unit": "G", "category": "macronutrient"},
    "SUGAR": {"display_name": "Total Sugars", "unit": "G", "category": "carbohydrate"},
    "SUCROSE": {"display_name": "Sucrose", "unit": "G", "category": "carbohydrate"},
    "GLUCOSE": {"display_name": "Glucose", "unit": "G", "category": "carbohydrate"},
    "FRUCTOSE": {"display_name": "Fructose", "unit": "G", "category": "carbohydrate"},
    "LACTOSE": {"display_name": "Lactose", "unit": "G", "category": "carbohydrate"},
    "MALTOSE": {"display_name": "Maltose", "unit": "G", "category": "carbohydrate"},
    "CAFFEINE": {"display_name": "Caffeine", "unit": "MG", "category": "other"},
    "CHOLESTEROL": {"display_name": "Cholesterol", "unit": "MG", "category": "fatty_acid"},
    "MONO_FAT": {"display_name": "Fatty acids, total monounsaturated", "unit": "G", "category": "fatty_acid"},
    "VITA_RAE": {"display_name": "Vitamin A, RAE", "unit": "UG", "category": "vitamin"},
    "VITB12": {"display_name": "Vitamin B-12", "unit": "UG", "category": "vitamin"},
    "VITB6": {"display_name": "Vitamin B-6", "unit": "MG", "category": "vitamin"},
    "BIOTIN": {"display_name": "Biotin", "unit": "UG", "category": "vitamin"},
    "CHOLINE": {"display_name": "Choline, total", "unit": "MG", "category": "vitamin"},
    "FOLATE": {"display_name": "Folate, total", "unit": "UG", "category": "vitamin"},
    "NIACIN": {"display_name": "Niacin", "unit": "MG", "category": "vitamin"},
    "PANTOTHENIC": {"display_name": "Pantothenic acid", "unit": "MG", "category": "vitamin"},
    "RIBOFLAVIN": {"display_name": "Riboflavin", "unit": "MG", "category": "vitamin"},
    "THIAMIN": {"display_name": "Thiamin", "unit": "MG", "category": "vitamin"},
    "VITC": {"display_name": "Vitamin C, total ascorbic acid", "unit": "MG", "category": "vitamin"},
    "VITD": {"display_name": "Vitamin D (D2 + D3)", "unit": "UG", "category": "vitamin"},
    "VITE": {"display_name": "Vitamin E (alpha-tocopherol)", "unit": "MG", "category": "vitamin"},
    "VITK": {"display_name": "Vitamin K (phylloquinone)", "unit": "UG", "category": "vitamin"},
    "BETA_CAROTENE": {"display_name": "Carotene, beta", "unit": "UG", "category": "vitamin"},
    "LYCOPENE": {"display_name": "Lycopene", "unit": "UG", "category": "vitamin"},
    "CA": {"display_name": "Calcium, Ca", "unit": "MG", "category": "mineral"},
    "FE": {"display_name": "Iron, Fe", "unit": "MG", "category": "mineral"},
    "K": {"display_name": "Potassium, K", "unit": "MG", "category": "mineral"},
    "MG": {"display_name": "Magnesium, Mg", "unit": "MG", "category": "mineral"},
    "NA": {"display_name": "Sodium, Na", "unit": "MG", "category": "mineral"},
    "P": {"display_name": "Phosphorus, P", "unit": "MG", "category": "mineral"},
    "ZN": {"display_name": "Zinc, Zn", "unit": "MG", "category": "mineral"},
    "CU": {"display_name": "Copper, Cu", "unit": "MG", "category": "mineral"},
    "MN": {"display_name": "Manganese, Mn", "unit": "MG", "category": "mineral"},
    "SE": {"display_name": "Selenium, Se", "unit": "UG", "category": "mineral"},
    "I": {"display_name": "Iodine, I", "unit": "UG", "category": "mineral"},
    "MO": {"display_name": "Molybdenum, Mo", "unit": "UG", "category": "mineral"},
    "F": {"display_name": "Fluoride, F", "unit": "UG", "category": "mineral"},
}

NUTRIENT_CODE_MAP = {
    1008: "ENERGY", 203: "PROTEIN", 205: "CARB", 204: "FAT",
    291: "FIBER", 255: "WATER", 269: "SUGAR", 210: "SUCROSE",
    211: "GLUCOSE", 212: "FRUCTOSE", 213: "LACTOSE", 214: "MALTOSE",
    263: "CAFFEINE", 221: "CHOLESTEROL", 207: "MONO_FAT",
    320: "VITA_RAE", 418: "VITB12", 415: "VITB6", 416: "BIOTIN",
    421: "CHOLINE", 417: "FOLATE", 406: "NIACIN", 410: "PANTOTHENIC",
    405: "RIBOFLAVIN", 404: "THIAMIN", 401: "VITC", 328: "VITD",
    323: "VITE", 430: "VITK", 321: "BETA_CAROTENE", 337: "LYCOPENE",
    301: "CA", 303: "FE", 306: "K", 304: "MG", 307: "NA",
    305: "P", 309: "ZN", 312: "CU", 315: "MN", 317: "SE",
    314: "I", 316: "MO", 313: "F",
}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nutrient_codes (
            code TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            standard_unit TEXT NOT NULL,
            category TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nutrients (
            id INTEGER PRIMARY KEY,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            unit_name TEXT,
            FOREIGN KEY (code) REFERENCES nutrient_codes(code)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_category (
            id INTEGER PRIMARY KEY,
            description TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS foods (
            fdc_id INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            data_type TEXT,
            category_id INTEGER,
            source TEXT,
            FOREIGN KEY (category_id) REFERENCES food_category(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_nutrients (
            id INTEGER PRIMARY KEY,
            fdc_id INTEGER NOT NULL,
            nutrient_id INTEGER NOT NULL,
            amount REAL,
            derivation_id INTEGER,
            FOREIGN KEY (fdc_id) REFERENCES foods(fdc_id),
            FOREIGN KEY (nutrient_id) REFERENCES nutrients(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ingest_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            operation TEXT NOT NULL,
            code TEXT,
            fdc_id INTEGER,
            description TEXT,
            details TEXT,
            rule_applied TEXT
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_foods_desc ON foods(description)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_food_nutrients_fdc ON food_nutrients(fdc_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_food_nutrients_nutrient ON food_nutrients(nutrient_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_nutrients_code ON nutrients(code)")

    for code, data in NUTRIENT_CODES.items():
        cursor.execute("""
            INSERT OR IGNORE INTO nutrient_codes (code, display_name, standard_unit, category)
            VALUES (?, ?, ?, ?)
        """, (code, data["display_name"], data["unit"], data["category"]))

    conn.commit()
    conn.close()
    print(f"Database initialized at: {DB_PATH}")


def reset_db():
    if DB_PATH.exists():
        DB_PATH.unlink()
    init_db()


if __name__ == "__main__":
    init_db()