import argparse
from neo4j_handler import Neo4jGraph
from text_processor import extract_entities_relations # Import the function
import os

def main():
    parser = argparse.ArgumentParser(description="MCP Tool: Create Knowledge Graphs from Research Papers in Neo4j.")

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

    # Argument for author affiliations - one per author, in order.
    # Example: --author-affiliations "Tech University" "Science Institute"
    # If an author has no affiliation for this paper, use a placeholder like "None" or an empty string.
    parser.add_argument("--author-affiliations", nargs='+',
                        help="List of affiliations for authors, one per author, in the same order as --authors. "
                             "Use 'None' or omit for authors without a listed affiliation for this paper.")


    parser.add_argument("--keywords", nargs='+', help="List of keywords/topics for the paper.")
    parser.add_argument("--venue", help="Publication venue (e.g., conference name, journal name).")
    parser.add_argument("--fulltext", help="Full text of the paper (optional, for more detailed processing).")


    args = parser.parse_args()

    graph_db = None
    try:
        print(f"Attempting to connect to Neo4j at {args.uri} with user {args.user}...")
        graph_db = Neo4jGraph(args.uri, args.user, args.password)
        print("Successfully connected to Neo4j.")

        print(f"\nProcessing paper: '{args.title}' (DOI: {args.doi})")

        # Add Research Paper node
        graph_db.add_research_paper(
            title=args.title,
            abstract=args.abstract,
            publication_date=args.pubdate,
            doi=args.doi,
            keywords=args.keywords,
            full_text=args.fulltext, # Pass fulltext if available
            venue_name=args.venue
        )
        print(f"- Added/Merged ResearchPaper: {args.title} ({args.doi})")
        if args.venue:
            # Venue linking is handled by add_research_paper now
            print(f"- Handled Venue: {args.venue} and linked to paper.")

        # Add Authors and link to Paper
        if args.authors:
            num_authors = len(args.authors)
            for i, author_str in enumerate(args.authors):
                name = author_str
                orcid = None
                affiliation_name = None # Default to no affiliation

                if '<' in author_str and '>' in author_str:
                    parts = author_str.split('<', 1)
                    name = parts[0].strip()
                    orcid_part = parts[1].split('>', 1)[0].strip()
                    if orcid_part:
                        orcid = orcid_part

                # Get affiliation if provided for this author
                if args.author_affiliations and i < len(args.author_affiliations):
                    if args.author_affiliations[i].lower() not in ["none", ""]:
                        affiliation_name = args.author_affiliations[i].strip()

                graph_db.add_author(name=name, orcid=orcid, affiliation_name=affiliation_name)
                print(f"- Added/Merged Author: {name}" + (f" (ORCID: {orcid})" if orcid else "") + (f" (Affiliation: {affiliation_name})" if affiliation_name else ""))

                paper_identifier = args.doi
                author_identifier = orcid if orcid else name
                graph_db.link_paper_to_author(
                    paper_identifier=paper_identifier,
                    author_identifier=author_identifier,
                    paper_by_doi=True,
                    author_by_orcid=bool(orcid)
                )
                print(f"  - Linked Author '{name}' to Paper '{args.title}'")

            # Link Co-authors (basic: all authors on this paper are co-authors)
            if num_authors > 1:
                for i in range(num_authors):
                    for j in range(i + 1, num_authors):
                        author1_str = args.authors[i]
                        author2_str = args.authors[j]

                        name1, orcid1 = (author1_str.split('<',1)[0].strip(), author1_str.split('<',1)[1].split('>',1)[0].strip() if '<' in author1_str else None)
                        name2, orcid2 = (author2_str.split('<',1)[0].strip(), author2_str.split('<',1)[1].split('>',1)[0].strip() if '<' in author2_str else None)

                        id1 = orcid1 if orcid1 else name1
                        id2 = orcid2 if orcid2 else name2

                        graph_db.link_coauthors(
                            author1_identifier=id1,
                            author2_identifier=id2,
                            paper_identifier=args.doi,
                            author1_by_orcid=bool(orcid1),
                            author2_by_orcid=bool(orcid2),
                            paper_by_doi=True
                        )
                        print(f"  - Linked Co-authors: '{name1}' and '{name2}' on paper '{args.doi}'")


        # Add Topics (Keywords) and link to Paper
        if args.keywords:
            for keyword in args.keywords:
                graph_db.add_topic(keyword) # add_topic is idempotent
                print(f"- Added/Merged Topic (from keyword): {keyword}")
                graph_db.link_paper_to_topic(
                    paper_identifier=args.doi,
                    topic_name=keyword,
                    paper_by_doi=True
                )
                print(f"  - Linked Topic '{keyword}' to Paper '{args.title}'")

        # --- Text Processing Integration ---
        text_to_process = args.abstract
        if args.fulltext: # Prefer fulltext if available
            text_to_process = args.fulltext

        if text_to_process:
            try:
                print("\n[MCP Tool] Starting text processing for entities...")
                extracted_data = extract_entities_relations(text_to_process)

                if extracted_data:
                    # Process extracted methods
                    if "methods" in extracted_data["entities"]:
                        for method_info in extracted_data["entities"]["methods"]:
                            method_name = method_info.get("name")
                            method_desc = method_info.get("description")
                            if method_name:
                                graph_db.add_method(name=method_name, description=method_desc)
                                print(f"- Added/Merged Method (from text): {method_name}")
                                graph_db.link_paper_to_method(
                                    paper_identifier=args.doi,
                                    method_name=method_name,
                                    paper_by_doi=True
                                )
                                print(f"  - Linked Method '{method_name}' to Paper '{args.title}'")

                    # Process extracted institutions (e.g., affiliations not explicitly linked to authors yet)
                    if "institutions" in extracted_data["entities"]:
                        for inst_info in extracted_data["entities"]["institutions"]:
                            inst_name = inst_info.get("name")
                            inst_loc = inst_info.get("location")
                            if inst_name:
                                graph_db.add_institution(name=inst_name, location=inst_loc)
                                print(f"- Added/Merged Institution (from text): {inst_name}")
                                # Note: Linking these institutions to specific authors would require
                                # more advanced co-reference resolution or explicit mapping.
                                # For now, they are added as general entities found in the paper.
                                # One could also link the paper to such institutions with a generic relationship like "MENTIONS_INSTITUTION"

                    # Process additional topics extracted from text
                    if "topics" in extracted_data["entities"]:
                        for topic_info in extracted_data["entities"]["topics"]:
                            topic_name = topic_info.get("name")
                            if topic_name:
                                graph_db.add_topic(topic_name)
                                print(f"- Added/Merged Topic (from text): {topic_name}")
                                graph_db.link_paper_to_topic(
                                    paper_identifier=args.doi,
                                    topic_name=topic_name,
                                    paper_by_doi=True
                                )
                                print(f"  - Linked Topic '{topic_name}' to Paper '{args.title}'")
                else:
                    print("[MCP Tool] Text processor returned no data.")
            except ImportError:
                print("[MCP Tool] Text processing skipped: spaCy library likely not found or model not loaded. Please check setup.")
            except Exception as e:
                print(f"[MCP Tool] Error during text processing: {e}")
        else:
            print("\n[MCP Tool] No abstract or full text provided for advanced text processing.")

        print("\nPaper processing complete.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if graph_db:
            graph_db.close()
            # print("Neo4j connection closed.") # Already printed by neo4j_handler

if __name__ == "__main__":
    main()
```
