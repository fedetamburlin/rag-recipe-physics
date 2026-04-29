#!/usr/bin/env python3
"""
Query Analyzer - First step of RAG Recipe Pipeline.

Parses multilingual user queries:
1. Quick language detection (regex)
2. Translate to English (LLM with probable language hint)
3. Extract structured data (LLM + regex fallback/union)
4. Merge with priority: regex for quantities, LLM+union for text
"""

import re
import logging
import yaml
import json
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

OLLAMA_HOST = "http://localhost:11434"

# Language detection patterns
LANG_CHARS = {
    'it': 'àèéìòù',
    'fr': 'àâçéèêëîïôùûü',
    'es': 'áéíóúñ¿',
}
LANG_KEYWORDS = {
    'it': {'senza', 'per', 'con', 'pane', 'pasta', 'torta', 'persone', 'minuti'},
    'fr': {'sans', 'pour', 'avec', 'pain', 'gâteau', 'minutes', 'personnes'},
    'es': {'sin', 'para', 'con', 'pan', 'pastel', 'minutos', 'personas'},
}

# Diet tags (English) - for regex detection
DIET_TAGS = {'vegan', 'vegetarian', 'pescatarian', 'gluten-free', 'lactose-free',
             'dairy-free', 'sugar-free', 'keto', 'paleo', 'low-carb', 'high-protein'}

# Diet tag expansions to forbidden ingredients
DIET_TAG_EXPANSION = {
    'vegan': ['meat', 'fish', 'egg', 'dairy', 'honey', 'gelatin', 'lard', 'bacon', 'pork', 'chicken', 'beef'],
    'vegetarian': ['meat', 'fish', 'lard', 'bacon', 'pork', 'chicken', 'beef'],
    'pescatarian': ['meat', 'chicken', 'beef', 'pork', 'bacon', 'lard'],
    'gluten-free': ['gluten', 'wheat', 'flour', 'bread', 'pasta', 'barley', 'rye', 'semolina', 'malt', 'spelt'],
    'dairy-free': ['dairy', 'milk', 'cheese', 'butter', 'cream', 'yogurt', 'whey', 'ghee', 'parmesan'],
    'lactose-free': ['lactose', 'dairy', 'milk', 'cheese'],
    'sugar-free': ['sugar', 'honey', 'syrup', 'molasses', 'sweetener'],
    'keto': ['sugar', 'bread', 'pasta', 'rice', 'potato', 'carrots', 'corn'],
    'low-carb': ['bread', 'pasta', 'rice', 'potato', 'corn', 'sugar'],
    'paleo': ['dairy', 'grain', 'legume', 'soy', 'sugar'],
}

# Allergen terms (English) - for regex detection
ALLERGEN = {
    'gluten': 'gluten', 'wheat': 'gluten', 'flour': 'gluten', 'bread': 'gluten',
    'egg': 'egg', 'eggs': 'egg',
    'dairy': 'dairy', 'milk': 'dairy', 'cheese': 'dairy', 'butter': 'dairy',
    'cream': 'dairy', 'yogurt': 'dairy', 'lactose': 'lactose',
    'fish': 'fish', 'salmon': 'fish', 'tuna': 'fish', 'cod': 'fish',
    'crustaceans': 'crustaceans', 'shrimp': 'crustaceans', 'prawns': 'crustaceans', 'crab': 'crustaceans',
    'nuts': 'nuts', 'peanuts': 'peanut', 'walnuts': 'nuts', 'almonds': 'nuts', 'hazelnuts': 'nuts',
    'peanut': 'peanut', 'soy': 'soy', 'sesame': 'sesame', 'celery': 'celery',
    'mustard': 'mustard', 'sulphites': 'sulphites', 'molluscs': 'molluscs', 'lupin': 'lupin',
    'meat': 'meat', 'beef': 'meat', 'pork': 'meat', 'chicken': 'meat', 'lamb': 'meat',
    'sugar': 'sugar', 'honey': 'sugar', 'syrup': 'sugar',
}


def _detect_language_quick(query: str) -> str:
    """Quick language detection via chars and keywords."""
    q = query.lower()
    
    # Check accented chars
    for lang, chars in LANG_CHARS.items():
        if any(c in query for c in chars):
            return lang
    
    # Check keywords
    for lang, keywords in LANG_KEYWORDS.items():
        if sum(1 for w in keywords if w in q) >= 2:
            return lang
    
    return 'en'


@dataclass
class QueryAnalysis:
    """Parsed query data for RAG pipeline."""
    raw_query: str
    normalized_query: str
    source_language: str
    target_language: str
    
    target_servings: Optional[int] = None
    target_weight_grams: Optional[float] = None
    forbidden_ingredients: list[str] = field(default_factory=list)
    diets: list[str] = field(default_factory=list)
    max_time_minutes: Optional[int] = None


class LLMQueryParser:
    """Ollama-based query parser."""
    
    def __init__(self, model: str = "qwen2.5:3b"):
        self.model = model
        if not _check_ollama():
            raise RuntimeError("Ollama not running")
    
    def _call(self, prompt: str, max_tokens: int = 300) -> str:
        import urllib.request
        url = f"{OLLAMA_HOST}/api/generate"
        data = {"model": self.model, "prompt": prompt, "stream": False,
                "options": {"temperature": 0.1, "num_predict": max_tokens}}
        req = urllib.request.Request(url, data=json.dumps(data).encode(),
                                      headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())["response"].strip()
    
    def translate(self, query: str, probable_lang: str) -> tuple[str, str]:
        """Translate to English with language hint."""
        result = self._call(
            f'The probable language is "{probable_lang}". Translate to English culinary terms. '
            f'Return ONLY valid JSON: {{"source_language": "it|en|fr|es|de|pt", "translation": "English text"}}. '
            f'Query: {query}\nJSON:'
        )
        try:
            for line in result.split('\n'):
                if '{' in line:
                    data = json.loads(line.strip())
                    return data.get('translation', query), data.get('source_language', probable_lang)
        except Exception:
            pass
        return query, probable_lang
    
    def extract_info(self, query: str) -> dict:
        """Extract info from English query."""
        result = self._call(
            f'Extract from English query. Return ONLY JSON: '
            f'{{"servings": null, "weight_grams": null, "max_time_minutes": null, '
            f'"diets": [], "forbidden_ingredients": []}}. '
            f'Query: {query}\nJSON:'
        )
        try:
            cleaned = result.strip()
            if cleaned.startswith('```'):
                parts = cleaned.split('```')
                cleaned = parts[1] if len(parts) > 1 else cleaned
                if cleaned.startswith('json'):
                    cleaned = cleaned[4:]
            for line in cleaned.split('\n'):
                if line.strip().startswith('{'):
                    return json.loads(line.strip())
        except Exception as e:
            logger.warning(f"JSON parse failed: {e}")
        return {"servings": None, "weight_grams": None, "max_time_minutes": None,
                "diets": [], "forbidden_ingredients": []}


class QueryAnalyzer:
    """Main query parser with LLM + regex merge."""
    
    def __init__(self, config_path: str = "config/pipeline.yaml"):
        cfg = {}
        if Path(config_path).exists():
            with open(config_path) as f:
                cfg = yaml.safe_load(f) or {}
        model = cfg.get('query_parser', {}).get('llm_model', 'qwen2.5:3b')
        self.rewriter = LLMQueryParser(model)
        
        # Regex patterns for fallback
        self._servings_pat = re.compile(r'(?:for|per)\s*(\d+)\s*(?:people|persons?|porzioni?)?', re.I)
        self._weight_pat = re.compile(r'(\d+(?:\.\d+)?)\s*(g|grams?|gr)\b', re.I)
        self._kg_pat = re.compile(r'(\d+(?:\.\d+)?)\s*(kg|kilograms?)\b', re.I)
        self._time_pat = re.compile(r'(?:within|under|less than)\s*(\d+(?:\.\d+)?)\s*(h|hours?|min|minutes?)\b', re.I)
        self._forbidden_pat = re.compile(r'(?:without|no|free|exclude)\s+(.+?)(?:\s+and\s+|$)', re.I)
    
    def _regex_servings(self, query: str) -> Optional[int]:
        m = self._servings_pat.search(query)
        return int(m.group(1)) if m and 1 <= int(m.group(1)) <= 50 else None
    
    def _regex_weight(self, query: str) -> Optional[float]:
        m = self._weight_pat.search(query)
        if m:
            return float(m.group(1))
        m = self._kg_pat.search(query)
        return float(m.group(1)) * 1000 if m else None
    
    def _regex_time(self, query: str) -> Optional[int]:
        m = self._time_pat.search(query)
        if m:
            val = float(m.group(1))
            unit = m.group(2).lower()
            return int(val * 60 if unit.startswith('h') else val)
        return None
    
    def _regex_forbidden(self, query: str) -> list[str]:
        """Extract forbidden from negation patterns + diet expansions."""
        forbidden = []
        q_lower = query.lower()
        
        # 1. Extract from negation patterns (e.g., "without eggs", "no dairy")
        for m in self._forbidden_pat.finditer(q_lower):
            phrase = m.group(1).strip()
            for token in re.split(r'[,\s]+|and', phrase):
                token = token.strip().lower()
                if token and len(token) > 2:
                    # Map to standard allergen
                    if token in ALLERGEN:
                        forbidden.append(ALLERGEN[token])
                    else:
                        forbidden.append(token)
        
        # 2. Expand diet tags to forbidden ingredients
        for diet, ingredients in DIET_TAG_EXPANSION.items():
            if diet.replace('-', ' ') in q_lower or diet in q_lower:
                forbidden.extend(ingredients)
        
        # 3. Check individual allergen words in query
        for allergen, standard in ALLERGEN.items():
            if allergen in q_lower:
                forbidden.append(standard)
        
        return list(set(forbidden))
    
    def _regex_diets(self, query: str) -> list[str]:
        """Detect diet tags from query."""
        q_lower = query.lower()
        diets = []
        
        for diet in DIET_TAGS:
            if diet.replace('-', ' ') in q_lower or diet in q_lower:
                diets.append(diet)
        
        return list(set(diets))
    
    def parse(self, query: str) -> QueryAnalysis:
        """Parse with LLM + regex merge."""
        # 1. Quick language detection (trust this for final lang)
        probable_lang = _detect_language_quick(query)
        
        # 2. LLM translation with language hint
        normalized, _ = self.rewriter.translate(query, probable_lang)
        
        # 3. LLM extraction
        llm_info = self.rewriter.extract_info(normalized)
        
        # 4. Regex fallback for quantities
        reg_servings = self._regex_servings(normalized)
        reg_weight = self._regex_weight(normalized)
        reg_time = self._regex_time(normalized)
        reg_forbidden = self._regex_forbidden(normalized)
        
        # 5. Merge with priority
        # Quantities: regex first, then LLM
        target_servings = reg_servings or llm_info.get('servings')
        target_weight = reg_weight or llm_info.get('weight_grams')
        max_time = reg_time or llm_info.get('max_time_minutes')
        
        # Text: union LLM + regex for both forbidden and diets
        llm_forbidden = llm_info.get('forbidden_ingredients', [])
        forbidden = list(set(llm_forbidden + reg_forbidden))
        
        # Diets: union LLM + regex
        reg_diets = self._regex_diets(normalized)
        llm_diets = llm_info.get('diets', [])
        diets = list(set(llm_diets + reg_diets))
        
        return QueryAnalysis(
            raw_query=query,
            normalized_query=normalized,
            source_language=probable_lang,
            target_language=probable_lang,
            target_servings=target_servings,
            target_weight_grams=target_weight,
            forbidden_ingredients=forbidden,
            diets=diets,
            max_time_minutes=max_time
        )


def _check_ollama() -> bool:
    import urllib.request
    try:
        urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=5).close()
        return True
    except Exception:
        return False


if __name__ == "__main__":
    analyzer = QueryAnalyzer()
    tests = [
        "Pane senza glutine per 4 persone",
        "Vegan chocolate cake without sugar",
        "Gluten-free bread within 2 hours",
        "500g cake without dairy",
        "Low-carb dinner under 30 minutes",
    ]
    for q in tests:
        r = analyzer.parse(q)
        print(f"[{r.source_language}] {q} → {r.normalized_query}")
        print(f"  serv:{r.target_servings} w:{r.target_weight_grams} t:{r.max_time_minutes}")
        print(f"  diets:{r.diets} forbidden:{r.forbidden_ingredients}")
        print()