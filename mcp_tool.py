import argparse
import os
from knowledge_graph_generator import KnowledgeGraphGenerator # Import the new class

def main():
    parser = argparse.ArgumentParser(description="MCP Tool CLI: Create Knowledge Graphs from Research Papers in Neo4j.")

    # Neo4j Connection Arguments
    parser.add_argument("--uri", default=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
                        help="Neo4j URI (default: bolt://localhost:7687 or NEO4J_URI env var)")
    parser.add_argument("--user", default=os.environ.get("NEO4J_USERNAME", "neo4j"),
                        help="Neo4j username (default: neo4j or NEO4J_USERNAME env var)")
    parser.add_argument("--password", default=os.environ.get("NEO4J_PASSWORD", "password"),
                        help="Neo4j password (default: password or NEO4J_PASSWORD env var)")

    # Research Paper Arguments
    parser.add_argument("--title", required=True, help="Title of the research paper.")
    parser.add_argument("--doi", required=True, help="DOI of the research paper (used as primary identifier).")
    parser.add_argument("--abstract", help="Abstract of the research paper. Used for text processing.")
    parser.add_argument("--pubdate", help="Publication date of the research paper (e.g., YYYY-MM-DD).")

    parser.add_argument("--authors", nargs='+',
                        help="List of authors. Format: 'Author Name <ORCID>' or 'Author Name'. ORCID is optional. "
                             "Example: --authors 'Alice Wonderland <0000-0001-2345-6789>' 'Bob The Builder'")

    parser.add_argument("--author-affiliations", nargs='+',
                        help="List of affiliations for authors, one per author, in the same order as --authors. "
                             "Use 'None' or an empty string for authors without a listed affiliation for this paper. "
                             "Example: --author-affiliations 'Tech University' 'None' 'Science Institute'")

    parser.add_argument("--keywords", nargs='+', help="List of keywords/topics for the paper.")
    parser.add_argument("--venue", help="Publication venue (e.g., conference name, journal name).")
    parser.add_argument("--fulltext", help="Full text of the paper (optional, for more detailed processing).")

    args = parser.parse_args()

    # Prepare structured author data for KnowledgeGraphGenerator
    authors_data_list = []
    if args.authors:
        for i, author_str in enumerate(args.authors):
            name = author_str
            orcid = None
            affiliation = None

            if '<' in author_str and '>' in author_str:
                parts = author_str.split('<', 1)
                name = parts[0].strip()
                orcid_part = parts[1].split('>', 1)[0].strip()
                if orcid_part:
                    orcid = orcid_part

            if args.author_affiliations and i < len(args.author_affiliations):
                if args.author_affiliations[i].lower() not in ["none", ""]:
                    affiliation = args.author_affiliations[i].strip()

            authors_data_list.append({"name": name, "orcid": orcid, "affiliation": affiliation})

    kgg = None
    try:
        print("[MCP CLI] Initializing Knowledge Graph Generator...")
        kgg = KnowledgeGraphGenerator(args.uri, args.user, args.password)

        if not kgg.graph_db: # Check if Neo4j connection was successful within KGG
            print("[MCP CLI] Failed to establish Neo4j connection via KGG. Exiting.")
            return

        print("[MCP CLI] Processing paper via Knowledge Graph Generator...")
        kgg.process_paper(
            title=args.title,
            doi=args.doi,
            abstract=args.abstract,
            pubdate=args.pubdate,
            authors_data=authors_data_list,
            keywords=args.keywords,
            venue_name=args.venue,
            full_text=args.fulltext
        )
        print("\n[MCP CLI] Paper processing request sent to generator.")

    except ConnectionError as ce: # Catch connection errors specifically if KGG raises them
        print(f"[MCP CLI] A connection error occurred: {ce}")
    except Exception as e:
        print(f"[MCP CLI] An unexpected error occurred: {e}")
    finally:
        if kgg:
            print("[MCP CLI] Closing Neo4j connection via KGG.")
            kgg.close_connection()
        print("[MCP CLI] Tool execution finished.")

if __name__ == "__main__":
    main()
