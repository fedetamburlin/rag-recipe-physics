#!/usr/bin/env python3
import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="RAG Recipe Pipeline")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    parser.add_argument("--query", type=str, help="Query to process")
    parser.add_argument("--config", default="../config/pipeline.yaml", help="Config file")
    parser.add_argument("--skip-generation", action="store_true", help="Only retrieval, no generation")
    args = parser.parse_args()
    
    from parser.query_analyzer import QueryAnalyzer
    from rag.retriever import RAGRetriever
    
    print("\n" + "="*60)
    print("Initializing Query Analyzer...")
    analyzer = QueryAnalyzer(config_path=args.config)
    
    print("Initializing RAG Retriever...")
    retriever = RAGRetriever(config_path=args.config, debug=args.debug)
    
    print("="*60 + "\n")
    
    if args.query:
        query = args.query
    else:
        print("Enter recipe query (or 'quit' to exit):")
        query = input("> ").strip()
    
    while query.lower() not in ['quit', 'exit', 'q']:
        if not query:
            query = input("> ").strip()
            continue
        
        print(f"\n{'─'*60}")
        print(f"Query: {query}")
        print(f"{'─'*60}")
        
        analysis = analyzer.parse(query)
        
        print(f"\n[Parsed]")
        print(f"  Language: {analysis.source_language} → EN")
        print(f"  Normalized: {analysis.normalized_query}")
        print(f"  Target Language: {analysis.target_language}")
        print(f"  Servings: {analysis.target_servings}")
        print(f"  Weight: {analysis.target_weight_grams}g")
        print(f"  Forbidden: {analysis.forbidden_ingredients}")
        print(f"  Diets: {analysis.diets}")
        print(f"  Max time: {analysis.max_time_minutes}min")
        
        retrieved = retriever.retrieve(analysis.normalized_query, analysis.forbidden_ingredients)
        taxonomy = retriever._compute_taxonomy(retrieved)
        
        print(f"\n[Retrieval] Taxonomy: {taxonomy}")
        print(f"  Top 3:")
        for r in retrieved:
            print(f"    [{r.rank}] {r.title[:40]:<40} score={r.cross_score:.3f}")
        
        if not args.skip_generation:
            print("\n[Generation]")
            result = retriever.generate(analysis.normalized_query, retrieved, 
                                         analysis.forbidden_ingredients, taxonomy)
            
            print("\n[Nutrition per 100g]")
            nutrition = retriever.calculate_recipe_nutrition(result)
            for k in ['Energy', 'Protein', 'Carbohydrates', 'Fat', 'Fiber', 'Sodium']:
                if k in nutrition:
                    print(f"  {k}: {nutrition[k]['amount']} {nutrition[k]['unit']}")
        
        print("\n" + "="*60)
        
        if args.query:
            break
        
        query = input("\nNext query: ").strip()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="RAG Recipe Pipeline")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    parser.add_argument("--query", type=str, help="Query to process")
    parser.add_argument("--config", default="../config/pipeline.yaml", help="Config file")
    parser.add_argument("--skip-generation", action="store_true", help="Only retrieval, no generation")
    parser.add_argument("--test", action="store_true", help="Run 20 test cases")
    args = parser.parse_args()
    
    from parser.query_analyzer import QueryAnalyzer
    
    if args.test:
        analyzer = QueryAnalyzer(config_path=args.config)
        run_tests(analyzer)
        sys.exit(0)
    
    from rag.retriever import RAGRetriever
    
    print("\n" + "="*60)
    print("Initializing Query Analyzer...")
    analyzer = QueryAnalyzer(config_path=args.config)
    
    print("Initializing RAG Retriever...")
    retriever = RAGRetriever(config_path=args.config, debug=args.debug)
    
    print("="*60 + "\n")
    
    if args.query:
        query = args.query
    else:
        print("Enter recipe query (or 'quit' to exit):")
        query = input("> ").strip()
    
    while query.lower() not in ['quit', 'exit', 'q']:
        if not query:
            query = input("> ").strip()
            continue
        
        print(f"\n{'─'*60}")
        print(f"Query: {query}")
        print(f"{'─'*60}")
        
        analysis = analyzer.parse(query)
        
        print(f"\n[Parsed]")
        print(f"  Language: {analysis.source_language} → EN")
        print(f"  Normalized: {analysis.normalized_query}")
        print(f"  Target Language: {analysis.target_language}")
        print(f"  Servings: {analysis.target_servings}")
        print(f"  Weight: {analysis.target_weight_grams}g")
        print(f"  Forbidden: {analysis.forbidden_ingredients}")
        print(f"  Diets: {analysis.diets}")
        print(f"  Max time: {analysis.max_time_minutes}min")
        
        retrieved = retriever.retrieve(analysis.normalized_query, analysis.forbidden_ingredients)
        taxonomy = retriever._compute_taxonomy(retrieved)
        
        print(f"\n[Retrieval] Taxonomy: {taxonomy}")
        print(f"  Top 3:")
        for r in retrieved:
            print(f"    [{r.rank}] {r.title[:40]:<40} score={r.cross_score:.3f}")
        
        if not args.skip_generation:
            print("\n[Generation]")
            try:
                result = retriever.generate(analysis.normalized_query, retrieved, 
                                             analysis.forbidden_ingredients, taxonomy)
            except Exception as e:
                print(f"[Error in generate: {e}]")
                result = ""
            
            if result:
                print("\n[Nutrition per 100g]")
                try:
                    nutrition = retriever.calculate_recipe_nutrition(result)
                    for k in ['Energy', 'Protein', 'Carbohydrates', 'Fat', 'Fiber', 'Sodium']:
                        if k in nutrition:
                            print(f"  {k}: {nutrition[k]['amount']} {nutrition[k]['unit']}")
                except Exception as e:
                    print(f"[Error in nutrition: {e}]")
        
        print("\n" + "="*60)
        
        if args.query:
            break
        
        query = input("\nNext query: ").strip()