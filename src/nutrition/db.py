import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent.parent.parent / "data" / "usda_nutrients.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nutrients (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            unit_name TEXT,
            nutrient_nbr INTEGER,
            rank REAL
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
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_foods_desc ON foods(description)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_food_nutrients_fdc ON food_nutrients(fdc_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_food_nutrients_nutrient ON food_nutrients(nutrient_id)")
    
    conn.commit()
    conn.close()
    print(f"Database initialized at: {DB_PATH}")


def reset_db():
    if DB_PATH.exists():
        DB_PATH.unlink()
    init_db()


if __name__ == "__main__":
    init_db()