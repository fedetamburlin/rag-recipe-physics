import re
import logging
from dataclasses import dataclass
from typing import Optional
import yaml

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False


logger = logging.getLogger(__name__)


@dataclass
class ParsedQuantity:
    value: float
    unit: str
    raw_match: str


@dataclass
class ParsedTemperature:
    value: float
    unit: str
    raw_match: str


@dataclass
class ParsedTime:
    value: float
    unit: str
    raw_match: str
    is_max: bool = False
    is_min: bool = False


@dataclass
class QueryAnalysis:
    raw_query: str
    normalized_query: str
    source_language: str
    normalized_language: str
    forbidden_extracted: list[str]
    forbidden_expanded: list[str]
    quantities: list[ParsedQuantity]
    temperatures: list[ParsedTemperature]
    times: list[ParsedTime]
    category_hints: list[str]
    is_valid: bool
    validation_messages: list[str]
    language_detected: str


NEGATE_WORDS = {'no', 'without', 'free', 'senza'}

DIET_TAGS = {'vegan', 'vegetarian', 'pescatarian', 'gluten-free', 'lactose-free', 'dairy-free', 'sugar-free', 'keto', 'paleo'}

DIET_TAG_EXPANSION = {
    'vegan': ['meat', 'fish', 'egg', 'dairy', 'honey', 'gelatin', 'lard'],
    'vegetarian': ['meat', 'fish', 'lard'],
    'pescatarian': ['meat'],
}

ALLERGEN_EU = {
    'glutine': 'gluten',
    'crostacei': 'crustaceans',
    'uova': 'egg',
    'pesce': 'fish',
    'arachidi': 'peanut',
    'soia': 'soy',
    'latte': 'dairy',
    'frutta a guscio': 'nuts',
    'sedano': 'celery',
    'senape': 'mustard',
    'sesamo': 'sesame',
    'anidride solforosa': 'sulphites',
    'molluschi': 'molluscs',
    'lupino': 'lupin',
}

ALLERGEN_COMMON = {
    'latticini': 'dairy',
    'formaggio': 'dairy',
    'uovo': 'egg',
    'carne': 'meat',
    'noci': 'nuts',
    'mais': 'corn',
    'lievito': 'yeast',
}


class QueryRewriter:
    """LLM per translate/correct query to EN"""
    
    def __init__(self, model: str = 'qwen2.5:3b'):
        self.model = model
        self._available = OLLAMA_AVAILABLE
    
    def translate_to_en(self, query: str, source_lang: str = 'en') -> tuple[str, str]:
        """Translate to EN. Returns (normalized_query, detected_lang).
        
        ALWAYS attempts translation for better RAG results."""
        if not self._available:
            return query, 'en'
        
        if source_lang == 'en':
            return query, 'en'
        
        prompt = f"""Translate this recipe query to English.
Use standard culinary English terms. For example:
- "pane" -> "bread"
- "pasta" -> "pasta"  
 - "senza glutine" -> "gluten-free"

Query: {query}

English translation:"""

        try:
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={'temperature': 0.1, 'num_predict': 100}
            )
            result = response['response'].strip()
            
            for prefix in ['it:', 'en:', 'es:', 'fr:', 'de:', 'pt:', 'English:', 'Translation:']:
                if result.strip().lower().startswith(prefix.lower()):
                    result = result.strip()[len(prefix):].strip()
                    break
            
            if result and len(result) > 3:
                return result, source_lang
            return query, source_lang
        except Exception as e:
            logger.warning(f"Translate EN failed: {e}")
            return query, source_lang

    def _detect_lang(self, query: str) -> str:
        if any(c in query for c in 'àèéìòù'):
            return 'it'
        if any(ind in query.lower() for ind in [' the ', ' a ', ' is ', ' with ', ' without ']):
            return 'en'
        return 'en'


class QueryParser:
    CATEGORY_KEYWORDS = {
        'lievitati': {
            'it': ['pane', 'pizza', 'focaccia', 'brioche'],
            'en': ['bread', 'pizza', 'brioche', 'roll', 'loaf']
        },
        'carni': {
            'it': ['carne', 'pollo', 'bovino', 'suino'],
            'en': ['beef', 'pork', 'chicken', 'meat', 'steak', 'roast']
        },
        'pesce': {
            'it': ['pesce', 'salmone', 'merluzzo', 'tonno'],
            'en': ['fish', 'salmon', 'cod', 'tuna']
        },
        'verdure': {
            'it': ['verdura', 'verdure', 'zucca', 'patate'],
            'en': ['vegetable', 'pumpkin', 'potato']
        },
        'creme': {
            'it': ['crema', 'panna', 'budino'],
            'en': ['cream', 'custard', 'pudding', 'mousse']
        },
        'impasti': {
            'it': ['pasta frolla', 'crostate'],
            'en': ['pastry', 'shortcrust', 'tart']
        },
        'masse_montate': {
            'it': ['meringa', 'pan di spagna'],
            'en': ['meringue', 'sponge cake']
        },
        'conserve': {
            'it': ['marmellata', 'confettura'],
            'en': ['jam', 'marmalade', 'preserves']
        }
    }

    def __init__(self, config_path: str = "config/validation_rules.yaml", use_llm_rewrite: bool = True):
        self.config_path = config_path
        self.rules = {}
        self.use_llm_rewrite = use_llm_rewrite
        self.rewriter = QueryRewriter() if use_llm_rewrite else None
        if config_path:
            try:
                with open(config_path, 'r') as f:
                    self.rules = yaml.safe_load(f)
            except:
                pass
        self._compile_patterns()

    def _compile_patterns(self):
        self.quantity_patterns = {
            'grams': re.compile(r'(\d+(?:[.,]\d+)?)\s*(g|gr|grams?)\b', re.IGNORECASE),
            'kg': re.compile(r'(\d+(?:[.,]\d+)?)\s*(kg)\b', re.IGNORECASE),
            'ml': re.compile(r'(\d+(?:[.,]\d+)?)\s*(ml)\b', re.IGNORECASE),
            'l': re.compile(r'(\d+(?:[.,]\d+)?)\s*(l|liters?)\b', re.IGNORECASE),
            'servings': re.compile(r'(?:for|per)\s+(\d+)\s*(servings?|people|persone)?\b', re.IGNORECASE),
            'pieces': re.compile(r'(\d+)\s*(uova|eggs?|pieces?)\b', re.IGNORECASE),
        }

        self.temperature_patterns = {
            'celsius': re.compile(r'(\d+(?:[.,]\d+)?)\s*(°?[Cc])\b', re.IGNORECASE),
            'fahrenheit': re.compile(r'(\d+(?:[.,]\d+)?)\s*(°?[Ff])\b', re.IGNORECASE),
        }

        self.time_patterns = {
            'minutes': re.compile(r'(\d+(?:[.,]\d+)?)\s*(min|mins?|minutes?)\b', re.IGNORECASE),
            'hours': re.compile(r'(\d+(?:[.,]\d+)?)\s*(h|hours?)\b', re.IGNORECASE),
            'max_time': re.compile(r'(?:max|maximum|within)\s*(\d+)\s*(min|hours)\b', re.IGNORECASE),
            'min_time': re.compile(r'(?:min|minimum)\s*(\d+)\s*(min|hours)\b', re.IGNORECASE),
        }

    def _detect_language(self, query: str) -> str:
        if any(c in query for c in 'àèéìòù'):
            return 'it'
        if any(kw in query.lower() for kw in ['senza', 'per ', 'con', 'pane', 'pasta', 'torta']):
            return 'it'
        return 'en'

    def _normalize_token(self, token: str) -> Optional[str]:
        token_lower = token.lower()
        
        if token_lower in DIET_TAGS:
            return token_lower
        
        if token_lower in ALLERGEN_EU:
            return ALLERGEN_EU[token_lower]
        
        if token_lower in ALLERGEN_COMMON:
            return ALLERGEN_COMMON[token_lower]
        
        COMMON_ALLERGENS = {'sugar', 'dairy', 'egg', 'gluten', 'meat', 'fish', 'nuts', 'soy', 'corn', 'yeast',
                           'wheat', 'lactose', 'peanuts', 'shellfish', 'celery', 'mustard', 'sesame', 'sulphites'}
        if token_lower in COMMON_ALLERGENS:
            if token_lower == 'peanuts': return 'peanut'
            if token_lower in ('wheat', 'lactose'): return token_lower
            if token_lower == 'shellfish': return 'crustaceans'
            return token_lower
        
        return None

    def extract_forbidden(self, query: str) -> list[str]:
        """Extract forbidden terms from query."""
        forbidden = []
        query_clean = re.sub(r'[,;]', ' ', query.lower())
        
        for tag in DIET_TAGS:
            if tag in query_clean:
                forbidden.append(tag)
        
        negate_pattern = re.compile(r'(?:senza|without|no|free)\s+(\w+(?:\s+\w+)?)', re.IGNORECASE)
        for match in negate_pattern.finditer(query_clean):
            phrase = match.group(1).strip()
            for token in phrase.split():
                token_clean = re.sub(r'[^\w]', '', token)
                normalized = self._normalize_token(token_clean)
                if normalized:
                    forbidden.append(normalized)
        
        free_pattern = re.compile(r'(\w+)-free')
        for match in free_pattern.finditer(query_clean):
            forbidden.append(match.group(1))
        
        return list(set(forbidden))

    def expand_forbidden(self, forbidden: list[str]) -> list[str]:
        """Expand diet tags to their components."""
        expanded = []
        for f in forbidden:
            if f in DIET_TAG_EXPANSION:
                expanded.extend(DIET_TAG_EXPANSION[f])
            else:
                expanded.append(f)
        return list(set(expanded))

    def parse(self, query: str, category: Optional[str] = None) -> QueryAnalysis:
        lang = self._detect_language(query)

        if self.rewriter:
            normalized_query, normalized_lang = self.rewriter.translate_to_en(query, lang)
        else:
            normalized_query = query
            normalized_lang = lang

        forbidden_extracted = self.extract_forbidden(normalized_query)
        forbidden_expanded = self.expand_forbidden(forbidden_extracted)

        quantities = self._find_quantities(normalized_query)
        temperatures = self._find_temperatures(normalized_query)
        times = self._find_times(normalized_query)
        category_hints = self._detect_category_hints(normalized_query, 'en')

        return QueryAnalysis(
            raw_query=query,
            normalized_query=normalized_query,
            source_language=lang,
            normalized_language=normalized_lang,
            forbidden_extracted=forbidden_extracted,
            forbidden_expanded=forbidden_expanded,
            quantities=quantities,
            temperatures=temperatures,
            times=times,
            category_hints=category_hints,
            is_valid=True,
            validation_messages=[],
            language_detected=lang
        )

    def validate_ingredients_against_forbidden(self, ingredients: list[str], forbidden: list[str]) -> list[str]:
        """Check if ingredients contain forbidden terms."""
        violations = []
        for ing in ingredients:
            ing_lower = ing.lower()
            for f in forbidden:
                if f.lower() in ing_lower:
                    violations.append(f"'{ing}' contains '{f}'")
        return violations

    def _find_quantities(self, query: str) -> list[ParsedQuantity]:
        found = []
        for name, pattern in self.quantity_patterns.items():
            for match in pattern.finditer(query):
                try:
                    value = float(match.group(1).replace(',', '.'))
                except:
                    continue
                if value > 0:
                    unit = 'servings' if name == 'servings' else name
                    found.append(ParsedQuantity(value=value, unit=unit, raw_match=match.group(0)))
        return found

    def _find_temperatures(self, query: str) -> list[ParsedTemperature]:
        found = []
        for name, pattern in self.temperature_patterns.items():
            for match in pattern.finditer(query):
                try:
                    value = float(match.group(1).replace(',', '.'))
                except:
                    continue
                found.append(ParsedTemperature(value=value, unit=name, raw_match=match.group(0)))
        return found

    def _find_times(self, query: str) -> list[ParsedTime]:
        found = []
        for name, pattern in self.time_patterns.items():
            if name in ('max_time', 'min_time'):
                for match in pattern.finditer(query):
                    try:
                        value = float(match.group(1).replace(',', '.'))
                    except:
                        continue
                    found.append(ParsedTime(
                        value=value,
                        unit=match.group(2).lower(),
                        raw_match=match.group(0),
                        is_max=(name == 'max_time'),
                        is_min=(name == 'min_time')
                    ))
            else:
                for match in pattern.finditer(query):
                    try:
                        value = float(match.group(1).replace(',', '.'))
                    except:
                        continue
                    if value > 0:
                        found.append(ParsedTime(value=value, unit=name, raw_match=match.group(0)))
        return found

    def _detect_category_hints(self, query: str, lang: str) -> list[str]:
        # Category detection moved to AFTER RAG retrieval
        # This allows detecting category based on retrieved recipe content
        return []


if __name__ == "__main__":
    parser = QueryParser(use_llm_rewrite=False)

    tests = [
        "Pane senza glutine",
        "Bread without sugar",
        "Vegan cake",
        "Gluten-free bread",
        "Torta per 4 persone",
        "500g farina",
        "180°C",
        "30 minutes",
    ]

    print("Query Parser Demo\n")
    for q in tests:
        a = parser.parse(q)
        print(f"[{a.language_detected}] {q}")
        print(f"  Forbidden: {a.forbidden_extracted}")
        print(f"  Expanded:  {a.forbidden_expanded}")
        if a.quantities:
            print(f"  Qty: {[(q.value, q.unit) for q in a.quantities]}")
        print()