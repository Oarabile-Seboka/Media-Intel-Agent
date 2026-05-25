import argparse
import sys
from src.storage import Storage
from src.fetcher import RSSFetcher
from src.analyzer import ContentAnalyzer
from src.interface import QueryInterface

def main():
    parser = argparse.ArgumentParser(description="Personal News Intelligence Agent")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Ingest command
    subparsers.add_parser("ingest", help="Fetch, analyze, and store new articles")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export the database to a CSV file")
    export_parser.add_argument("--output", "-o", default="data/articles_export.csv", help="Output path for the CSV file")

    # Query command
    query_parser = subparsers.add_parser("query", help="Query the news database")
    query_parser.add_argument("text", help="Natural language query")

    args = parser.parse_args()

    # Initialize components
    storage = Storage()
    analyzer = ContentAnalyzer()
    fetcher = RSSFetcher(storage=storage)
    interface = QueryInterface(storage, analyzer)

    if args.command == "ingest":
        print("Starting ingestion...")
        articles = fetcher.fetch_all()
        print(f"Found {len(articles)} new articles.")
        
        for i, article in enumerate(articles):
            print(f"Analyzing {i+1}/{len(articles)}: {article['title']}")
            analysis = analyzer.analyze_article(article)
            
            relevance = analysis.get("relevance_score", "").lower()
            usefulness = analysis.get("usefulness", "").lower()
            
            if relevance == "low":
                print(f"  -> Skipping: Low relevance")
                continue
            
            # Merge analysis into article data
            article.update(analysis)
            
            storage.add_article(article)
            
        print("Ingestion complete.")

    elif args.command == "query":
        print(f"Querying: {args.text}")
        results = interface.handle_query(args.text)
        print(interface.format_results(results))

    elif args.command == "export":
        print("Exporting database to CSV...")
        output_path = storage.export_to_csv(args.output)
        if output_path:
            print(f"Successfully exported to {output_path}")
        else:
            print("Failed to export: database might be empty.")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
