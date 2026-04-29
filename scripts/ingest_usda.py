#!/usr/bin/env python3
"""Ingest USDA FoodData Central datasets into SQLite."""

import csv
import sqlite3
from pathlib import Path
from tqdm import tqdm

BASE_DIR = Path(__file__).parent.parent / "raw_database"
DB_PATH = Path(__file__).parent.parent / "data" / "usda_nutrients.db"

FOUNDATION_DIR = BASE_DIR / "foundation" / "FoodData_Central_foundation_food_csv_2025-12-18"
SR_LEGACY_DIR = BASE_DIR / "sr_legacy" / "FoodData_Central_sr_legacy_food_csv_2018-04"

BATCH_SIZE = 1000


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ingest_nutrients(data_dir: Path, source: str):
    """Ingest nutrients from nutrient.csv."""
    print(f"\n[INGEST] Nutrients from {source}...")
    nutrient_file = data_dir / "nutrient.csv"
    
    if not nutrient_file.exists():
        print(f"  Skipping - file not found: {nutrient_file}")
        return 0
    
    conn = get_connection()
    cursor = conn.cursor()
    
    count = 0
    batch = []
    
    with open(nutrient_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                nbr = int(float(row['nutrient_nbr'])) if row.get('nutrient_nbr') else None
            except (ValueError, TypeError):
                nbr = None
            
            batch.append((
                int(row['id']),
                row['name'],
                row.get('unit_name', ''),
                nbr,
                float(row['rank']) if row.get('rank') else None
            ))
            
            if len(batch) >= BATCH_SIZE:
                cursor.executemany(
                    "INSERT OR IGNORE INTO nutrients (id, name, unit_name, nutrient_nbr, rank) VALUES (?, ?, ?, ?, ?)",
                    batch
                )
                count += len(batch)
                batch = []
        
        if batch:
            cursor.executemany(
                "INSERT OR IGNORE INTO nutrients (id, name, unit_name, nutrient_nbr, rank) VALUES (?, ?, ?, ?, ?)",
                batch
            )
            count += len(batch)
    
    conn.commit()
    conn.close()
    print(f"  Inserted {count} nutrients")
    return count


def ingest_food_categories(data_dir: Path, source: str):
    """Ingest food categories."""
    print(f"[INGEST] Food categories from {source}...")
    category_file = data_dir / "food_category.csv"
    
    if not category_file.exists():
        print(f"  Skipping - file not found: {category_file}")
        return 0
    
    conn = get_connection()
    cursor = conn.cursor()
    
    count = 0
    batch = []
    
    with open(category_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            batch.append((
                int(row['id']),
                row.get('description', '')
            ))
            
            if len(batch) >= BATCH_SIZE:
                cursor.executemany(
                    "INSERT OR IGNORE INTO food_category (id, description) VALUES (?, ?)",
                    batch
                )
                count += len(batch)
                batch = []
        
        if batch:
            cursor.executemany(
                "INSERT OR IGNORE INTO food_category (id, description) VALUES (?, ?)",
                batch
            )
            count += len(batch)
    
    conn.commit()
    conn.close()
    print(f"  Inserted {count} categories")
    return count


def ingest_foods(data_dir: Path, source: str):
    """Ingest foods."""
    print(f"[INGEST] Foods from {source}...")
    food_file = data_dir / "food.csv"
    
    if not food_file.exists():
        print(f"  Skipping - file not found: {food_file}")
        return 0
    
    conn = get_connection()
    cursor = conn.cursor()
    
    count = 0
    batch = []
    
    with open(food_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in tqdm(reader, desc=f"  Foods ({source})"):
            batch.append((
                int(row['fdc_id']),
                row['description'],
                row.get('data_type', ''),
                int(row['food_category_id']) if row.get('food_category_id') else None,
                source
            ))
            
            if len(batch) >= BATCH_SIZE:
                cursor.executemany(
                    "INSERT OR REPLACE INTO foods (fdc_id, description, data_type, category_id, source) VALUES (?, ?, ?, ?, ?)",
                    batch
                )
                count += len(batch)
                batch = []
        
        if batch:
            cursor.executemany(
                "INSERT OR REPLACE INTO foods (fdc_id, description, data_type, category_id, source) VALUES (?, ?, ?, ?, ?)",
                batch
            )
            count += len(batch)
    
    conn.commit()
    conn.close()
    print(f"  Inserted {count} foods")
    return count


def ingest_food_nutrients(data_dir: Path, source: str):
    """Ingest food nutrients."""
    print(f"[INGEST] Food nutrients from {source}...")
    fn_file = data_dir / "food_nutrient.csv"
    
    if not fn_file.exists():
        print(f"  Skipping - file not found: {fn_file}")
        return 0
    
    conn = get_connection()
    cursor = conn.cursor()
    
    count = 0
    batch = []
    
    with open(fn_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in tqdm(reader, desc=f"  Nutrients ({source})"):
            try:
                batch.append((
                    int(row['id']),
                    int(row['fdc_id']),
                    int(row['nutrient_id']),
                    float(row['amount']) if row.get('amount') else None,
                    int(row['derivation_id']) if row.get('derivation_id') else None
                ))
            except (KeyError, ValueError) as e:
                continue
            
            if len(batch) >= BATCH_SIZE:
                cursor.executemany(
                    "INSERT OR IGNORE INTO food_nutrients (id, fdc_id, nutrient_id, amount, derivation_id) VALUES (?, ?, ?, ?, ?)",
                    batch
                )
                count += len(batch)
                batch = []
        
        if batch:
            cursor.executemany(
                "INSERT OR IGNORE INTO food_nutrients (id, fdc_id, nutrient_id, amount, derivation_id) VALUES (?, ?, ?, ?, ?)",
                batch
            )
            count += len(batch)
    
    conn.commit()
    conn.close()
    print(f"  Inserted {count} food-nutrient associations")
    return count


def main():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.nutrition.db import init_db
    
    print("=" * 60)
    print("USDA FoodData Central Ingestion")
    print("=" * 60)
    
    init_db()
    
    stats = {}
    
    stats['nutrients_fnd'] = ingest_nutrients(FOUNDATION_DIR, "foundation")
    stats['categories_fnd'] = ingest_food_categories(FOUNDATION_DIR, "foundation")
    stats['foods_fnd'] = ingest_foods(FOUNDATION_DIR, "foundation")
    stats['food_nutrients_fnd'] = ingest_food_nutrients(FOUNDATION_DIR, "foundation")
    
    stats['nutrients_leg'] = ingest_nutrients(SR_LEGACY_DIR, "sr_legacy")
    stats['categories_leg'] = ingest_food_categories(SR_LEGACY_DIR, "sr_legacy")
    stats['foods_leg'] = ingest_foods(SR_LEGACY_DIR, "sr_legacy")
    stats['food_nutrients_leg'] = ingest_food_nutrients(SR_LEGACY_DIR, "sr_legacy")
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM nutrients")
    print(f"Total nutrients: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM foods")
    print(f"Total foods: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM food_nutrients")
    print(f"Total food-nutrient links: {cursor.fetchone()[0]}")
    
    conn.close()
    print(f"\nDatabase: {DB_PATH}")


if __name__ == "__main__":
    main()