"""
RAG + preprocessing instructions + persistent disk ingestion.
The first execution does encoding and saves everything in cache/.
Subsequent executions load directly from disk — zero re-encoding.
"""

import os
import re
import sys
import time
import json
import hashlib
import argparse
from pathlib import Path
import numpy as np
import ollama
from datasets import load_dataset
from sentence_transformers import SentenceTransformer, CrossEncoder
import torch
from transformers import AutoTokenizer
import warnings
from transformers import logging as hf_logging
from huggingface_hub.utils import logging as hf_hub_logging
import ast
import csv
import psutil
from datetime import datetime

hf_hub_logging.set_verbosity_error()
hf_logging.set_verbosity_error()
warnings.filterwarnings("ignore")
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

# ══════════════════════════════════════════════
#  PARSE ARGS PRIMA DI TUTTO
# ══════════════════════════════════════════════

parser = argparse.ArgumentParser(description="Chef's RAG Recipe Generator")
parser.add_argument("--debug", action="store_true", help="Modalità debug (mostra prompt aumentato, tempistiche dettagliate)")
parser.add_argument("--user", action="store_true", help="Modalità utente (output pulito)")
args = parser.parse_args()

DEFAULT_DEBUG_MODE = False
DEBUG_MODE = args.debug if args.debug or args.user else DEFAULT_DEBUG_MODE
USER_MODE = args.user and not args.debug

VERBOSE = not USER_MODE  # Messaggi tecnici solo se NON in modalità user

import gc, torch; gc.collect(); torch.cuda.empty_cache() # clean ram e vram

def check_hardware_and_select_model() -> str:
    if torch.cuda.is_available():
        if VERBOSE:
            print(f"[HARDWARE] GPU detected: {torch.cuda.get_device_name(0)} → using gemma2:9b")
        return "gemma2:9b"
    
    ram_gb = psutil.virtual_memory().total / (1024**3)
    if VERBOSE:
        print(f"[HARDWARE] Total RAM: {ram_gb:.1f} GB")
    
    if ram_gb >= 12:
        if VERBOSE:
            print("[HARDWARE] → using gemma2:9b")
        return "gemma2:9b"
    else:
        if VERBOSE:
            print("[HARDWARE] → using gemma2:2b")
        return "gemma2:2b"

def ensure_ollama_model(model_name: str) -> None:
    try:
        installed_models = [m.model for m in ollama.list().models]
    except Exception as e:
        if VERBOSE:
            print(f"[OLLAMA] Error reading installed models: {e}")

    print("[OLLAMA] Pulling model...")

    print(f"[OLLAMA] Model '{model_name}' not installed. Downloading...")

    print(f"[OLLAMA] '{model_name}' installed successfully!")

    print(f"[OLLAMA] Model '{model_name}' already installed.")

LLM_MODEL = check_hardware_and_select_model()
ensure_ollama_model(LLM_MODEL)

# ══════════════════════════════════════════════
#  MODALITÀ DEBUG / UTENTE
# ══════════════════════════════════════════════

parser = argparse.ArgumentParser(description="Chef's RAG Recipe Generator")
parser.add_argument("--debug", action="store_true", help="Modalità debug (mostra prompt aumentato, tempistiche dettagliate)")
parser.add_argument("--user", action="store_true", help="Modalità utente (output pulito)")
args = parser.parse_args()

DEFAULT_DEBUG_MODE = False
DEBUG_MODE = args.debug if args.debug or args.user else DEFAULT_DEBUG_MODE
USER_MODE = args.user and not args.debug

VERBOSE = not USER_MODE  # Messaggi tecnici solo se NON in modalità user

DATASET_SIZE  = 100000   # numero di dati utilizzati per il dataset RAG
FIRST_STAGE_K = 30      # first step retriver
FINAL_K       = 3       # reranker
CACHE_DIR     = Path("cache")   # cartella dove salvare embedding + metadati
OVEN_MODEL_PATH = "./recipe_emb_2"

# Add oven model directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / OVEN_MODEL_PATH))

import fineTune_emb_colab2 as ft

# DATASET_NAME = "AkashPS11/recipes_data_food.com"
DATASET_NAME = "nuhuibrahim/recifine"

batch_size_emb = 64    # batch size per ingestion

USE_LLM_FORBIDDEN = False  # scegli se usare un LLM per ricavere dalla query principale parole negative (es: "evita formaggio")
PRINT_AUG_QUERY = True #False

# Parametri LLM rag
temp = 0.1  # temperatura (creatività) del modello generativo LLM del rag
num_ctx = 700  # dimensioni contesto input
num_predict = 500 # dimensioni ricetta generata
num_thread = 2  # numero di processori/core

penalty_forb1 = 1.0         # retriver penalità parole negate
penalty_forb2 = 0.5         # cross-encoder penalità parole negate

# FEEDBACK SYSTEM
RECIPES_FILE = "recipes.json"              # JSON file for structured recipe storage
FEEDBACK_BATCH_SIZE = 50                # dopo quanti feedback eseguire il retraining
FEEDBACK_BOOST_WEIGHT = 0.2             # quanto pesa il punteggio nel ranking (0 = nessun boost)

# ERROR HANDLING
MAX_RETRIES = 3                         # max retries for Ollama generation
RETRY_DELAY = 2                         # seconds between retries

# Prompt di sistema: definisce comportamento ruolo e limiti
SYSTEM_PROMPT = (
    "You are a cooking assistant. Generate exactly one recipe.\n\n"
    "Rules:\n"
    "- Draw inspiration from the context recipes; \n"
    "- Never use forbidden ingredients.\n"
    "- Do NOT add notes, greetings\n"
    "- The recipe MUST strictly be an oven-baked preparation.\n\n"
    "OUTPUT FORMAT (strict):\n"
    "**Title:** <max 5 words>\n"
    "**Ingredients:** <comma-separated list>\n"
    "**Instructions:**\n"
    "1. <step>\n"
    "2. <step>\n"
)

def save_validated_recipe(query: str, generated_recipe: str, rating: int, predicted_temp: str, predicted_time: str) -> None:
    """
    Salva il feedback dell'utente su una ricetta generata per miglioramenti futuri.
    """
    import csv
    from datetime import datetime

    # Crea il file CSV con header se non esiste
    file_exists = False
    try:
        with open(FEEDBACK_FILE, 'r', newline='', encoding='utf-8'):
            file_exists = True
    except FileNotFoundError:
        pass

    # Scrivi i dati nel file CSV
    with open(FEEDBACK_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Scrivi l'header se il file è nuovo
        if not file_exists:
            writer.writerow(['timestamp', 'query', 'generated_recipe', 'rating', 'predicted_temperature', 'predicted_time'])

        # Scrivi i dati del feedback
        writer.writerow([
            datetime.now().isoformat(),
            query,
            generated_recipe,
            rating,
            predicted_temp,
            predicted_time
        ])

def parse_recipe_output(text: str) -> dict:
    """Parse LLM recipe output into structured fields."""
    import re
    
    result = {
        "title": "",
        "ingredients": [],
        "instructions": [],
    }
    
    # Extract title
    title_match = re.search(r'\*\*Title:\*\*\s*(.+?)(?:\n|$)', text)
    if title_match:
        result["title"] = title_match.group(1).strip()
    
    # Extract ingredients
    ing_match = re.search(r'\*\*Ingredients:\*\*\s*(.+?)(?:\*\*Instructions:|$)', text, re.DOTALL)
    if ing_match:
        ing_text = ing_match.group(1).strip()
        result["ingredients"] = [i.strip() for i in ing_text.split(',') if i.strip()]
    
    # Extract instructions (numbered steps)
    instr_match = re.search(r'\*\*Instructions:\*\*\s*(.+?)$', text, re.DOTALL)
    if instr_match:
        steps = instr_match.group(1).strip()
        for line in steps.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                step = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
                if step:
                    result["instructions"].append(step)
    
    return result

def save_validated_recipe_json(query: str, generated_recipe: str, rating: int, predicted_temp: str, predicted_time: str, retrieval_scores: list = None) -> None:
    """
    Save recipe in structured JSON format.
    """
    import json
    from datetime import datetime
    import hashlib
    
    # Parse the generated recipe
    parsed = parse_recipe_output(generated_recipe)
    
    # Create recipe object
    recipe = {
        "id": hashlib.md5(f"{query}{datetime.now().isoformat()}".encode()).hexdigest()[:12],
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "title": parsed.get("title", ""),
        "ingredients": parsed.get("ingredients", []),
        "instructions": parsed.get("instructions", []),
        "full_text": generated_recipe,
        "predicted_temp": predicted_temp,
        "predicted_time": predicted_time,
        "rating": rating,
        "model": "gemma2:9b",
        "retrieval_scores": retrieval_scores or []
    }
    
    # Load existing recipes
    recipes = []
    try:
        with open(RECIPES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            recipes = data.get("recipes", [])
    except (FileNotFoundError, json.JSONDecodeError):
        recipes = []
    
    # Add new recipe
    recipes.append(recipe)
    
    # Save back
    with open(RECIPES_FILE, 'w', encoding='utf-8') as f:
        json.dump({"recipes": recipes, "count": len(recipes)}, f, indent=2, ensure_ascii=False)

# query nuove in ingresso per valutare il modello con query tipo ideate da cuoco
prompts = [
    "healthy chicken recipe with garlic",
    "High-protein vegan dinner ready in under 30 minutes",
    "Creamy potato soup without dairy or gluten",
    "Spicy dessert combining dark chocolate, citrus, and chili peppers",
    "Slow-braised beef using only root vegetables and no alcohol",
    "Breakfast recipe using exactly three ingredients including eggs",
    "Japanese style tacos with fish and spicy mayo",
]

# test_query = prompts[1]
test_query = "Rice Case Pies"

# ══════════════════════════════════════════════
#  PARSING & PREPROCESSING
# ══════════════════════════════════════════════

def parse_list(s: str) -> str:
    """Estrae stringhe da formato tipo c("a", "b", "c")."""
    if not isinstance(s, str):
        return ""
    items = re.findall(r'"([^"]*)"', s) or [s.strip()]
    return ", ".join(i.strip() for i in items if i.strip())

def preprocess_instructions(raw: str, max_steps: int = 10, max_chars: int = 128) -> str:
    """
    Riduce le istruzioni a pochi step brevi.

    Regole:
    - Se formato lista c("step1","step2"): estrae gli item
    - Se testo libero: splitta per frase
    - Prende solo i primi max_steps
    - Tronca ogni step a max_chars caratteri
    """
    if not isinstance(raw, str) or not raw.strip():
        return ""

    steps = re.findall(r'"([^"]*)"', raw)
    if not steps:
        steps = re.split(r'(?<=[.!?])\s+|;\s*', raw.strip())

    steps = [s.strip() for s in steps if len(s.strip()) > 8][:max_steps]
    steps = [s[:max_chars] + ("..." if len(s) > max_chars else "") for s in steps]
    return " ".join(steps)

# ══════════════════════════════════════════════
#  CACHE — ingestion persistente
# ══════════════════════════════════════════════

def cache_key(dataset_size: int) -> str:
    """Chiave univoca basata sui parametri di ingestion."""
    tag = f"recipes_{dataset_size}"
    return hashlib.md5(tag.encode()).hexdigest()[:8]

def load_cache(key: str):
    """Carica embedding e metadati da disco. Ritorna None se non esistono."""
    emb_path  = CACHE_DIR / f"{key}_embeddings.npy"
    meta_path = CACHE_DIR / f"{key}_metadata.json"
    doc_path  = CACHE_DIR / f"{key}_documents.json"

    if not (emb_path.exists() and meta_path.exists() and doc_path.exists()):
        return None

    print(f"Cache found ({key}) — loading from disk, skip encoding.")
    embeddings = np.load(emb_path)
    with open(meta_path) as f:
        metadata = json.load(f)
    with open(doc_path) as f:
        documents = json.load(f)
    return embeddings, metadata, documents

def save_cache(key: str, embeddings: np.ndarray, metadata: list, documents: list):
    """Salva embedding e metadati su disco."""
    CACHE_DIR.mkdir(exist_ok=True)
    np.save(CACHE_DIR / f"{key}_embeddings.npy", embeddings)
    with open(CACHE_DIR / f"{key}_metadata.json", "w") as f:
        json.dump(metadata, f, ensure_ascii=False)
    with open(CACHE_DIR / f"{key}_documents.json", "w") as f:
        json.dump(documents, f, ensure_ascii=False)
    print(f"Cache saved in {CACHE_DIR}/ ({key})")

# ══════════════════════════════════════════════
#  INGESTION
# ══════════════════════════════════════════════

def ingest(embedder: SentenceTransformer):
    """
    Carica dataset, preprocessa, embeds.
    Se la cache esiste la usa, altrimenti la crea.
    """
    key = cache_key(DATASET_SIZE)
    cached = load_cache(key)

    # Se presente cache la carica
    if cached is not None:
        return cached  # (embeddings, metadata, documents)

    # Prima esecuzione: ingestion completa
    print(f"Ingesting dataset ({DATASET_SIZE} recipes)...")
    dataset = load_dataset(
        DATASET_NAME,
        split=f"train[:{DATASET_SIZE}]"
    )

    # FILTER
    if DATASET_NAME == "nuhuibrahim/recifine":
        def is_oven_recifine(row):
            try:
                directions_list = ast.literal_eval(row.get("directions") or "[]")
                temp_c, time_m = ft.extract_oven_ground_truth(directions_list)
                return temp_c > 0 and time_m > 0   # stessa condizione di process_row
            except Exception:
                return False
        dataset = dataset.filter(is_oven_recifine)
        print(f"Oven recipes found: {len(dataset)}")

    documents = []
    metadata  = []

    for row in dataset:
        if DATASET_NAME == "nuhuibrahim/recifine":
            title = (row.get("title") or "").strip() or "N/A"
            ner_raw = row.get("NER") or row.get("ingredients") or ""
            ingredients = parse_list(ner_raw)
            try:
                dir_list = ast.literal_eval(row.get("directions") or "[]")
                instructions_raw = " ".join(dir_list)
            except Exception:
                instructions_raw = row.get("directions") or ""
        elif DATASET_NAME=="AkashPS11/recipes_data_food.com":
            title       = (row.get("Name") or "").strip() or "N/A"
            ingredients = parse_list(row.get("RecipeIngredientParts") or "")
            instructions_raw = row.get("RecipeInstructions") or ""
            # calories = row.get("Calories") or ""
            # fats = row.get("FatContent") or ""
            # proteins = row.get("ProteinContent") or ""
            # carbs = row.get("CarbohydrateContent") or ""
            # fibers = row.get("FiberContent") or ""
            # total_time =row.get("TotalTime") or ""

        # Versione compressa per l'embedding (meno RAM, documento più corto)
        instructions_short = preprocess_instructions(instructions_raw, max_steps=5, max_chars=64)
        # Versione più ricca per il prompt LLM
        instructions_full = preprocess_instructions(instructions_raw, max_steps=8, max_chars=128)

        # Documento per retrieval: titolo + ingredienti + istruzioni brevi
        documents.append(
            f"Title: {title}. "
            f"Ingredients: {ingredients}. "
            f"Method: {instructions_short}"
        )

        # Metadati separati per il prompt LLM (non entrano nell'embedding, utili per altri step)
        metadata.append({
            "title":        title,
            "ingredients":  ingredients,
            "instructions": instructions_full,
        })
    
    print(f"Encoding {len(documents)} documents...")
    t0 = time.time()
    embeddings = embedder.encode(documents, batch_size=batch_size_emb, show_progress_bar=True, convert_to_numpy=True, normalize_embeddings=True)
    print(f"Encoding completed in {time.time()-t0:.1f}s")
    save_cache(key, embeddings, metadata, documents)
    return embeddings, metadata, documents

# ══════════════════════════════════════════════
#  FORBIDDEN
# ══════════════════════════════════════════════

NEGATE_WORDS = {"no", "without", "free", "avoid", "exclude", "non"}

FORBIDDEN_EXPANSIONS = {
    "dairy":       ["cheese", "milk", "cream", "butter", "yogurt", "whey", "cheddar", "parmesan", "ghee"],
    "gluten":      ["flour", "wheat", "bread", "pasta", "barley", "rye", "semolina", "malt", "spelt"],
    "alcohol":     ["wine", "beer", "vodka", "rum", "whiskey", "brandy", "liquor"],
    "meat":        ["chicken", "beef", "pork", "lamb", "bacon", "turkey", "sausage", "duck", "venison", "lard"],
    "fish":        ["salmon", "tuna", "cod", "anchovy", "sardine", "shrimp", "crab", "lobster", "shellfish", "seafood"],
    "sugar":       ["honey", "syrup", "molasses", "sweetener", "fructose"],
    "egg":         ["eggs", "yolk", "albumen"],
    "nuts":        ["almond", "walnut", "cashew", "peanut", "hazelnut", "pecan"],
    # diet tags — espandono direttamente negli ingredienti vietati
    "vegan":       ["chicken", "beef", "pork", "lamb", "duck", "turkey", "bacon", "lard", "gelatin",
                    "fish", "shellfish", "seafood", "shrimp", "crab", "lobster",
                    "milk", "cheese", "butter", "cream", "yogurt", "whey", "ghee",
                    "eggs", "egg", "yolk", "honey"],
    "vegetarian":  ["chicken", "beef", "pork", "lamb", "duck", "turkey", "bacon", "lard", "gelatin",
                    "fish", "shellfish", "seafood", "shrimp", "crab", "lobster"],
    "pescatarian": ["chicken", "beef", "pork", "lamb", "duck", "turkey", "bacon", "lard", "gelatin"],
}

DIET_TAGS = {"vegan", "vegetarian", "pescatarian"}

NOISE = {"the", "a", "an", "and", "or", "no", "not", "any", "none", "ingredients", "foods"}

def expand_forbidden(forbidden: list[str]) -> list[str]:
    """
    Assegna a delle parole proibite altre parole collegate (hard coded)
    """
    expanded = list(forbidden)
    for f in forbidden:
        expanded += FORBIDDEN_EXPANSIONS.get(f.lower(), [])
    return list(set(expanded))

def extract_forbidden(query: str) -> list[str]:
    """
    Estre parole proibile hard coded
    in base a parole di negazione nella query
    """
    tokens = re.sub(r"[,;.]", "", query.lower()).split()
    forbidden = []
    negate_active = False
    just_took = False
    for tok in tokens:
        if tok in DIET_TAGS:            # "vegan dinner" -> forbidden implicito senza negazione
            forbidden.append(tok)
            just_took = False
        elif tok in NEGATE_WORDS:
            negate_active = True
            just_took = False
        elif tok in {"or", "and"} and just_took:
            negate_active = True
            just_took = False
        elif negate_active:
            forbidden.append(tok)
            negate_active = False
            just_took = True
        else:
            just_took = False

    return forbidden

def extract_forbidden_llm(query: str) -> list[str]:
    """
    Cattura esclusioni che con un LLM
    """
    resp = ollama.chat(
        model = LLM_MODEL,
        messages = [{"role": "user", "content": (
            "List ingredients to EXCLUDE from this recipe request. "
            "Reply with comma-separated single words only. "
            "If nothing to exclude, reply: none\n"
            f"Request: {query}\n"
            "Exclusions:"
        )}],
        options = {"num_ctx": 96, "temperature": 0.0, "num_predict": 24}
    )
    raw = resp["message"]["content"].strip().lower()
    if not raw or raw.startswith("none"):
        return []
    return [w.strip() for w in raw.split(",") if w.strip() and w.strip() not in NOISE]

def split_query(query: str) -> tuple[str, list[str]]:
    """
    Genera:
    * Una lista di parole negate nella query
    * Query pulita (senza parole negate)
    """
    forbidden_rule = extract_forbidden(query)
    forbidden_llm  = extract_forbidden_llm(query) if USE_LLM_FORBIDDEN else []
    llm_extra      = [f for f in forbidden_llm if f not in forbidden_rule] # LLM come safety net: tieni solo ciò che rule-based non ha già
    forbidden_raw  = list(set(forbidden_rule + llm_extra))

    print(f"  forbidden — rule:{forbidden_rule} llm_extra:{llm_extra}")

    tokens = re.sub(r"[,;.]", "", query).split()
    # togli le parole originali della query che negavano (senza espansioni)
    skip   = set(forbidden_raw) | NEGATE_WORDS | {"or", "and"} | DIET_TAGS
    clean  = " ".join(t for t in tokens if t.lower() not in skip)
    return clean, forbidden_raw

# ══════════════════════════════════════════════
#  RETRIEVAL
# ══════════════════════════════════════════════

def retrieve(query, embedder, reranker, doc_embeddings, documents, metadata):
    """
    Retriver del RAG
    """
    clean_query, forbidden = split_query(query)
    forbidden_expanded = expand_forbidden(forbidden) if forbidden else []
    #print(f"Forbidden: {forbidden} | Expanded: {forbidden_expanded} | Clean: {clean_query}")

    # Emedding query pulita
    q_emb = embedder.encode([clean_query], convert_to_numpy=True, normalize_embeddings=True)

    # Cerca similitudine con dot product
    sims  = np.dot(q_emb, doc_embeddings.T).flatten()

    # Penalizza parole negate nella query
    if forbidden_expanded:
        f_embs = embedder.encode(forbidden_expanded, convert_to_numpy=True, normalize_embeddings=True)
        penalty = np.max(np.dot(f_embs, doc_embeddings.T), axis=0)*0.7 + \
                    np.mean(np.dot(f_embs, doc_embeddings.T), axis=0)*0.3
        sims -= penalty_forb1 * penalty

    # Prendi i più simili
    top_idx = np.argsort(sims)[::-1][:FIRST_STAGE_K]
    candidates   = [documents[i] for i in top_idx]

    # Reranker
    cross_scores = reranker.predict([[clean_query , doc] for doc in candidates])
    cross_scores = (cross_scores - cross_scores.mean()) / (cross_scores.std() + 1e-8)

    # Penalizza nel RR parole negate
    if forbidden_expanded:
        forbidden_query  = f"This recipe contains: {', '.join(forbidden_expanded)}"
        forbidden_scores = reranker.predict([[forbidden_query, doc] for doc in candidates])
        cross_scores    -= penalty_forb2 * np.clip(forbidden_scores, 0, None)

    # TOP RICETTE
    best_local = np.argsort(cross_scores)[::-1][:FINAL_K]

    return [
        {
            "rank":        rank,
            "bi_score":    float(sims[top_idx[li]]),
            "cross_score": float(cross_scores[li]),
            "meta":        metadata[top_idx[li]],
            "forbidden": forbidden,
            "forbidden_exp":   forbidden_expanded
        }
        for rank, li in enumerate(best_local)
    ]

# ══════════════════════════════════════════════
#  GENERAZIONE
# ══════════════════════════════════════════════

def build_prompt(query: str, results: list) -> str:
    """
    Crea prompt per LLM del RAG, concatena le parti: ricette, query, retrived, regole generazione
    """
    # Calcola numero medio ingredienti delle ricette retrieved
    avg_ing = round(sum(
        len([i for i in r["meta"]["ingredients"].split(",") if i.strip()]) for r in results
        ) / len(results))

    parts = []
    for r in results: # Pesca le ricette più simili e le formatta
        m = r["meta"]
        f_exp = r["forbidden_exp"]
        parts.append(
            f"[RECIPE {r['rank']}]{' BEST MATCH' if r['rank'] == 0 else ''}\n"
            f"TITLE: {m['title']}\n"
            f"INGREDIENTS: {m['ingredients']}\n"
            f"INSTRUCTIONS: {m['instructions']}"
            )

    context = "\n\n---\n\n".join(parts)

    # Regole finali USER prompt
    prompt = (
        f"Context:\n\n{context}\n\n---\n\n"
        f"Create a hybrid recipe using about {avg_ing} ingredients.\n"
    )

    if len(f_exp) > 0:
        prompt += f"FORBIDDEN INGREDIENTS (strictly avoid): {', '.join(f_exp)}.\n"

    prompt += (
        "\nTASK:\n"
        f"Create a new recipe that STRICTLY satisfies: {query}.\n"
    )
    return prompt

def generate(query: str, results: list) -> str:

    usr_prompt = build_prompt(query, results)

    if DEBUG_MODE:
        print(f"[DEBUG] SYSTEM PROMPT:\n{SYSTEM_PROMPT}\n")
        print(f"[DEBUG] AUGMENTED QUERY:\n{usr_prompt}")
        print(f"\n[DEBUG] Generazione con {LLM_MODEL}:\n")
    else:
        print(f"\nGenerazione con {LLM_MODEL}:\n")

    # Interroga LLM per la generazione nuova ricetta
    stream = ollama.chat(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": usr_prompt},
        ],
        stream=True,
        options={"num_ctx": num_ctx,
                 "temperature": temp,
                 "num_predict": num_predict,
                 "num_thread": num_thread}
    )

    # Plot stream
    full = ""
    for chunk in stream:
        token = chunk["message"]["content"]
        print(token, end="", flush=True)
        full += token
    print()
    return full

# ══════════════════════════════════════════════
#  PIPELINE RAG
# ══════════════════════════════════════════════

def rag(query, embedder, reranker, doc_embeddings, documents, metadata):
    print(f"\n{'═'*60}\nQuery: {query}\n{'─'*60}")

    t0 = time.time()
    results = retrieve(query, embedder, reranker, doc_embeddings, documents, metadata) # RETRIVER
    t_ret = time.time() - t0

    print(f"Retrieval ({t_ret:.2f}s) — top {FINAL_K}:")
    for r in results:
        print(f"  [{r['rank']}] {r['meta']['title']:<40} cross={r['cross_score']:+.3f}")

    # Libera RAM prima di caricare il LLM
    del embedder, reranker, doc_embeddings
    gc.collect()
    time.sleep(1)  # lascia tempo all'OS di reclaimare la memoria

    t1 = time.time()
    answer = generate(query, results) # PROMPT e LLM
    print(f"\n{'─'*60}")
    print(f"Retrieval: {t_ret:.2f}s | Generation: {time.time()-t1:.2f}s")
    print(f"{'═'*60}")
    return answer

# ══════════════════════════════════════════════
#  METRICS
# ══════════════════════════════════════════════

def predict_oven_parameters(generated_recipe: str, model: torch.nn.Module, tokenizer: AutoTokenizer, device: torch.device) -> tuple:
    """
    Esegue la predizione di temperatura e tempo sulla ricetta generata dal RAG.
    """
    model.eval()

    # Normalizzazione sintattica per allineamento con i tensori di training
    text_normalized = generated_recipe.replace("**Title:**", "TITLE:") \
                                      .replace("**Ingredients:**", "| INGREDIENTS:") \
                                      .replace("**Instructions:**", "| DIRECTIONS:") \
                                      .replace("\n", " ")

    # Mascheramento esplicito come in fase di training
    masked_text = ft.mask_oven_parameters(text_normalized)

    enc = tokenizer(masked_text, padding=True, truncation=True, max_length=512, return_tensors="pt").to(device)

    with torch.no_grad():
        output = model(**enc)
        logits = output["logits"] if isinstance(output, dict) else output

    p_temp = logits[:, :ft.N_TEMP_CLASSES].argmax(-1).item()
    p_time = logits[:, ft.N_TEMP_CLASSES:].argmax(-1).item()

    return ft.TEMP_ID2LABEL[p_temp], ft.TIME_ID2LABEL[p_time]

# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════

if __name__ == "__main__":

    # RAG ---------------------------------------------------

    if VERBOSE:
        print("Loading retrieval models...")

    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    embeddings, metadata, documents = ingest(embedder)

    print(f"Loading oven classification model from {OVEN_MODEL_PATH}...")
    gc.collect()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    oven_tokenizer = AutoTokenizer.from_pretrained(OVEN_MODEL_PATH)
    oven_model = ft.DualHeadOvenModelV2("roberta-base", vocab_size=len(oven_tokenizer), 
                                      n_temp_classes=ft.N_TEMP_CLASSES, n_time_classes=ft.N_TIME_CLASSES)
    oven_model.load_state_dict(torch.load(f"{OVEN_MODEL_PATH}/model_weights.pt", map_location=device), strict=False)
    oven_model.to(device).eval()

    print("\n" + "="*60)
    print("👨‍🍳 CHEF'S RAG RECIPE GENERATOR 👨‍🍳")
    print("="*60)
    if USER_MODE:
        print("Mode: USER | Exit: 'exit'")
    else:
        print("Mode: DEBUG")
    print("Examples: 'vegan recipe without gluten', 'spicy chocolate dessert'")
    print("-"*60)

    # Ciclo principale per interazione con lo chef
    while True:
        try:
            # Get query from chef
            try:
                query = input("\n🔍 Enter your recipe request: ").strip()
            except EOFError:
                print("\n👋 Input ended. Goodbye!")
                break

            if query.lower() in ['exit', 'quit', 'chiudi', '']:
                print("\n👋 Goodbye! Happy cooking!")
                break

            if not query:
                continue

            if DEBUG_MODE:
                print(f"\n{'═'*60}\n[DEBUG] Query: {query}\n{'─'*60}")

            # Esegui pipeline RAG
            t0 = time.time()
            results = retrieve(query, embedder, reranker, embeddings, documents, metadata)
            t_ret = time.time() - t0

            if DEBUG_MODE:
                print(f"[DEBUG] Retrieval ({t_ret:.2f}s) — top {FINAL_K}:")
                for r in results:
                    print(f"  [{r['rank']}] {r['meta']['title']:<40} cross={r['cross_score']:+.3f}")

            t1 = time.time()
            # Generate with retry logic
            answer = None
            last_error = None
            for attempt in range(MAX_RETRIES):
                try:
                    answer = generate(query, results)
                    break
                except Exception as e:
                    last_error = e
                    if attempt < MAX_RETRIES - 1:
                        print(f"⚠️ Generation attempt {attempt+1} failed: {e}. Retrying in {RETRY_DELAY}s...")
                        time.sleep(RETRY_DELAY)
                    continue
            
            if answer is None:
                print(f"❌ Generation failed after {MAX_RETRIES} attempts: {last_error}")
                print("Please try a different query.")
                continue
            
            t_gen = time.time() - t1

            if DEBUG_MODE:
                print(f"\n{'─'*60}")
                print(f"[DEBUG] Retrieval: {t_ret:.2f}s | Generation: {t_gen:.2f}s")
                print(f"{'═'*60}")

            # PREDIZIONE PARAMETRI sulla ricetta generata
            pred_temp, pred_time = predict_oven_parameters(answer, oven_model, oven_tokenizer, device)

            if USER_MODE:
                print(f"\n{'═'*60}")
                print("🍳 BAKING ESTIMATES:")
                print(f"  Temperature: {pred_temp}")
                print(f"  Time:        {pred_time}")
                print(f"{'═'*60}")
            else:
                print(f"\n🍳 OVEN PARAMETERS PREDICTION:")
                print(f"  - Estimated Temperature: {pred_temp}")
                print(f"  - Estimated Time:        {pred_time}")
                print(f"\n{'═'*60}")

            # Ask for feedback on the generated recipe
            retrieval_scores = [r['cross_score'] for r in results]
            try:
                feedback = input("\n📝 Rate this recipe (1-5) or press Enter to skip: ").strip()
                if feedback and feedback.isdigit() and 1 <= int(feedback) <= 5:
                    rating = int(feedback)
                    save_validated_recipe_json(query, answer, rating, pred_temp, pred_time, retrieval_scores)
                    print(f"💾 Recipe saved with rating {rating}/5 for future improvements!")
                elif feedback:
                    print("⚠️   Please enter a number between 1-5 or press Enter to skip.")
            except (EOFError, KeyboardInterrupt):
                print("\n👋 Skipping feedback...")
            except Exception as e:
                print(f"⚠️   Could not save feedback: {e}")

            print(f"\n{'═'*60}")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye! Happy cooking!")
            break
        except Exception as e:
            print(f"\n❌ Error during processing: {e}")
            print("Please try a different query.")
            continue