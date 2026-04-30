#!/usr/bin/env python3
"""
USDA FoodData Central Ingestion Script
=======================================
Ingest selettivo di 44 nutrienti con:
- Rimozione codici vuoti
- Rimozione duplicati con dati incompleti
- Calcolo ENERGY mancante
- Logging completo delle operazioni
"""

import csv
import sqlite3
import json
from pathlib import Path
from tqdm import tqdm
from collections import defaultdict

BASE_DIR = Path(__file__).parent.parent / "raw_database"
DB_PATH = Path(__file__).parent.parent / "data" / "usda_nutrients.db"

FOUNDATION_DIR = BASE_DIR / "foundation" / "FoodData_Central_foundation_food_csv_2025-12-18"
SR_LEGACY_DIR = BASE_DIR / "sr_legacy" / "FoodData_Central_sr_legacy_food_csv_2018-04"

BATCH_SIZE = 1000

NUTRIENT_NBR_MAP = {
    208: "ENERGY", 203: "PROTEIN", 205: "CARB", 204: "FAT",
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


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_nutrient_id_map(data_dir: Path) -> dict:
    """Build mapping from nutrient.id (USDA) to code by reading nutrient.csv."""
    nutrient_file = data_dir / "nutrient.csv"
    id_to_code = {}
    if not nutrient_file.exists():
        return id_to_code
    with open(nutrient_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                nbr = int(float(row['nutrient_nbr'])) if row.get('nutrient_nbr') else None
            except (ValueError, TypeError):
                nbr = None
            if nbr and nbr in NUTRIENT_NBR_MAP:
                code = NUTRIENT_NBR_MAP[nbr]
                nutrient_id = int(row['id'])
                if nutrient_id not in id_to_code:
                    id_to_code[nutrient_id] = code
    return id_to_code


def ingest_nutrients(data_dir: Path, source: str, id_to_code: dict):
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
            nutrient_id = int(row['id'])
            if nutrient_id not in id_to_code:
                continue
            code = id_to_code[nutrient_id]
            batch.append((nutrient_id, code, row['name'], row.get('unit_name', '')))
            if len(batch) >= BATCH_SIZE:
                cursor.executemany(
                    "INSERT OR IGNORE INTO nutrients (id, code, name, unit_name) VALUES (?, ?, ?, ?)",
                    batch
                )
                count += len(batch)
                batch = []
        if batch:
            cursor.executemany(
                "INSERT OR IGNORE INTO nutrients (id, code, name, unit_name) VALUES (?, ?, ?, ?)",
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
            batch.append((int(row['id']), row.get('description', '')))
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


def ingest_food_nutrients(data_dir: Path, source: str, allowed_nutrient_ids: set):
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
                nutrient_id = int(row['nutrient_id'])
            except (KeyError, ValueError):
                continue
            if nutrient_id not in allowed_nutrient_ids:
                continue
            try:
                batch.append((
                    int(row['id']),
                    int(row['fdc_id']),
                    nutrient_id,
                    float(row['amount']) if row.get('amount') else None,
                    int(row['derivation_id']) if row.get('derivation_id') else None
                ))
            except (KeyError, ValueError):
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


def post_process(conn: sqlite3.Connection):
    """Post-processing: filter empty codes, remove incomplete duplicates, calculate ENERGY."""
    cursor = conn.cursor()
    stats = {"empty_codes": 0, "duplicates_removed": 0, "energy_calculated": 0, "two_macro_removed": 0}

    # === 1. REMOVE EMPTY NUTRIENT CODES ===
    print("\n[POST] Removing empty nutrient codes...")
    empty_codes = ['ALCOHOL', 'ASH', 'CR', 'LUTEIN', 'OMEGA3', 'OMEGA6',
                   'POLY_FAT', 'SAT_FAT', 'STARCH', 'TRANS_FAT']

    for code in empty_codes:
        cursor.execute("DELETE FROM nutrients WHERE code = ?", (code,))
        deleted = cursor.rowcount
        if deleted > 0:
            cursor.execute(
                "INSERT INTO ingest_log (operation, code, rule_applied) VALUES (?, ?, ?)",
                ("FILTER_EMPTY_CODE", code, f"Rimosso codice senza dati: {code}")
            )
            stats["empty_codes"] += 1

    conn.commit()
    print(f"  Removed {stats['empty_codes']} empty codes")

    # === 2. REMOVE INCOMPLETE DUPLICATES ===
    # Per ogni descrizione duplicata: tiene solo quello con più macronutrienti
    print("\n[POST] Removing incomplete duplicates...")

    # Get macro completeness for each food
    cursor.execute("""
        SELECT fdc_id,
               SUM(CASE WHEN n.code = 'ENERGY' THEN 1 ELSE 0 END) as has_energy,
               SUM(CASE WHEN n.code = 'PROTEIN' THEN 1 ELSE 0 END) as has_protein,
               SUM(CASE WHEN n.code = 'CARB' THEN 1 ELSE 0 END) as has_carb,
               SUM(CASE WHEN n.code = 'FAT' THEN 1 ELSE 0 END) as has_fat
        FROM food_nutrients fn
        JOIN nutrients n ON fn.nutrient_id = n.id
        WHERE n.code IN ('ENERGY', 'PROTEIN', 'CARB', 'FAT')
        GROUP BY fdc_id
    """)
    food_macros = {r[0]: sum([r[1], r[2], r[3], r[4]]) for r in cursor.fetchall()}

    # Get foods with descriptions
    cursor.execute("SELECT fdc_id, description, LOWER(description) as desc_lower FROM foods")
    fdc_info = {}  # fdc_id -> (description, desc_lower)
    desc_to_fdc = defaultdict(list)
    for r in cursor.fetchall():
        fdc_info[r[0]] = (r[1], r[2])
        desc_to_fdc[r[2]].append(r[0])

    # For each duplicate group:
    # 1. Keep foods with 3+ macros first
    # 2. If tie, keep shortest/most generic name
    fdc_to_remove = []
    keep_fdc_ids = set()

    for desc, fdcs in desc_to_fdc.items():
        if len(fdcs) < 2:
            continue

        # Score: (macro_count, -name_length, fdc_id)
        scored = []
        for fdc_id in fdcs:
            macros = food_macros.get(fdc_id, 0)
            desc_len = len(fdc_info.get(fdc_id, ('', ''))[0])
            # Prefer shorter names (more generic), then lower fdc_id as tiebreaker
            scored.append((macros, -desc_len, fdc_id))

        scored.sort(reverse=True)
        keep_fdc = scored[0][2]
        keep_fdc_ids.add(keep_fdc)

        for _, _, fdc_id in scored[1:]:
            fdc_to_remove.append(fdc_id)

    # Remove duplicates
    if fdc_to_remove:
        # Log sample
        for fdc_id in fdc_to_remove[:5]:
            desc = fdc_info.get(fdc_id, ('', ''))[0]
            macros = food_macros.get(fdc_id, 0)
            cursor.execute(
                "INSERT INTO ingest_log (operation, fdc_id, description, details, rule_applied) VALUES (?, ?, ?, ?, ?)",
                ("REMOVE_DUPLICATE", fdc_id, desc[:50], f"{macros} macros", f"Duplicato rimosso")
            )

        # Delete from food_nutrients first
        placeholders = ','.join(['?'] * len(fdc_to_remove))
        cursor.execute(f"DELETE FROM food_nutrients WHERE fdc_id IN ({placeholders})", fdc_to_remove)

        # Delete from foods
        cursor.execute(f"DELETE FROM foods WHERE fdc_id IN ({placeholders})", fdc_to_remove)

        stats["duplicates_removed"] = len(fdc_to_remove)
        conn.commit()
    print(f"  Removed {stats['duplicates_removed']} incomplete duplicates")

    # === 3. CALCULATE MISSING ENERGY ===
    # Formula: ENERGY = PROTEIN*4 + CARB*4 + FAT*9 (Atwater)
    print("\n[POST] Calculating missing ENERGY...")

    cursor.execute("SELECT id, code FROM nutrients WHERE code IN ('ENERGY', 'PROTEIN', 'CARB', 'FAT')")
    nutrient_ids = {r[1]: r[0] for r in cursor.fetchall()}

    energy_id = nutrient_ids['ENERGY']
    protein_id = nutrient_ids['PROTEIN']
    carb_id = nutrient_ids['CARB']
    fat_id = nutrient_ids['FAT']

    # Find foods with macros but without ENERGY
    cursor.execute(f"""
        SELECT fdc_id FROM food_nutrients
        WHERE nutrient_id IN (?, ?, ?)
        AND fdc_id NOT IN (SELECT fdc_id FROM food_nutrients WHERE nutrient_id = ?)
        GROUP BY fdc_id
    """, (protein_id, carb_id, fat_id, energy_id))

    foods_without_energy = [r[0] for r in cursor.fetchall()]

    new_records = []
    cursor.execute("SELECT MAX(id) FROM food_nutrients")
    max_id = (cursor.fetchone()[0] or 0) + 1

    for fdc_id in foods_without_energy:
        cursor.execute(
            "SELECT nutrient_id, amount FROM food_nutrients WHERE fdc_id = ? AND nutrient_id IN (?, ?, ?)",
            (fdc_id, protein_id, carb_id, fat_id)
        )
        macros = {r[0]: r[1] or 0 for r in cursor.fetchall()}

        protein = macros.get(protein_id, 0)
        carb = macros.get(carb_id, 0)
        fat = macros.get(fat_id, 0)

        energy = round(protein * 4 + carb * 4 + fat * 9, 1)

        max_id += 1
        new_records.append((max_id, fdc_id, energy_id, energy, None))

        # Log first 5
        if len(new_records) <= 5:
            cursor.execute(
                "INSERT INTO ingest_log (operation, fdc_id, details, rule_applied) VALUES (?, ?, ?, ?)",
                ("CALCULATE_ENERGY", fdc_id, f"P={protein:.1f},C={carb:.1f},F={fat:.1f},E={energy}",
                 "Calcolato da macronutrienti: PRO*4 + CARB*4 + FAT*9")
            )

    if new_records:
        cursor.executemany(
            "INSERT INTO food_nutrients (id, fdc_id, nutrient_id, amount, derivation_id) VALUES (?, ?, ?, ?, ?)",
            new_records
        )
        stats["energy_calculated"] = len(new_records)
        conn.commit()

    print(f"  Calculated ENERGY for {stats['energy_calculated']} foods")

    return stats


def main():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.nutrition.db import init_db

    print("=" * 60)
    print("USDA FoodData Central Ingestion (44 nutrients + cleanup)")
    print("=" * 60)

    init_db()

    stats = {}

    print("\n[LOAD] Building nutrient ID maps...")
    id_map_fnd = load_nutrient_id_map(FOUNDATION_DIR)
    id_map_leg = load_nutrient_id_map(SR_LEGACY_DIR)
    all_ids = set(id_map_fnd.keys()) | set(id_map_leg.keys())
    print(f"  Found {len(all_ids)} nutrient IDs to ingest")

    stats['nutrients_fnd'] = ingest_nutrients(FOUNDATION_DIR, "foundation", id_map_fnd)
    stats['categories_fnd'] = ingest_food_categories(FOUNDATION_DIR, "foundation")
    stats['foods_fnd'] = ingest_foods(FOUNDATION_DIR, "foundation")
    stats['food_nutrients_fnd'] = ingest_food_nutrients(FOUNDATION_DIR, "foundation", all_ids)

    stats['nutrients_leg'] = ingest_nutrients(SR_LEGACY_DIR, "sr_legacy", id_map_leg)
    stats['categories_leg'] = ingest_food_categories(SR_LEGACY_DIR, "sr_legacy")
    stats['foods_leg'] = ingest_foods(SR_LEGACY_DIR, "sr_legacy")
    stats['food_nutrients_leg'] = ingest_food_nutrients(SR_LEGACY_DIR, "sr_legacy", all_ids)

    # Post-processing
    conn = get_connection()
    post_stats = post_process(conn)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM nutrient_codes")
    print(f"Nutrient codes: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM nutrients")
    print(f"Total nutrients: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM foods")
    print(f"Total foods: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM food_nutrients")
    print(f"Total food-nutrient links: {cursor.fetchone()[0]}")

    print("\n--- POST-PROCESSING ---")
    print(f"  Empty codes removed: {post_stats['empty_codes']}")
    print(f"  Duplicates removed: {post_stats['duplicates_removed']}")
    print(f"  ENERGY calculated: {post_stats['energy_calculated']}")

    print("\n--- INGEST LOG SAMPLE ---")
    cursor.execute("SELECT operation, code, fdc_id, rule_applied FROM ingest_log LIMIT 10")
    for r in cursor.fetchall():
        print(f"  {r[0]:20} | code={r[1] or ''} | fdc_id={r[2] or ''} | {r[3][:50]}")

    conn.close()
    print(f"\nDatabase: {DB_PATH}")


if __name__ == "__main__":
    main()