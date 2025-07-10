from neo4j_handler import Neo4jGraph
from text_processor import extract_entities_relations

class KnowledgeGraphGenerator:
    def __init__(self, neo4j_uri, neo4j_user, neo4j_password):
        self.graph_db = None
        try:
            print(f"[KGG] Attempting to connect to Neo4j at {neo4j_uri} with user {neo4j_user}...")
            self.graph_db = Neo4jGraph(neo4j_uri, neo4j_user, neo4j_password)
            print("[KGG] Successfully connected to Neo4j.")
        except Exception as e:
            print(f"[KGG] Error initializing Neo4jGraph: {e}")
            # Allow initialization but graph_db will be None, operations will fail
            # Or re-raise: raise ConnectionError(f"Failed to connect to Neo4j: {e}") from e
            self.graph_db = None # Ensure it's None if connection failed

    def process_paper(self, title, doi, abstract=None, pubdate=None, authors_data=None,
                      keywords=None, venue_name=None, full_text=None):
        """
        Processes a single research paper and populates the knowledge graph.
        Args:
            title (str): Title of the paper.
            doi (str): DOI of the paper.
            abstract (str, optional): Abstract of the paper.
            pubdate (str, optional): Publication date.
            authors_data (list, optional): List of author dicts, e.g.,
                                         [{'name': 'Author A', 'orcid': 'xxx', 'affiliation': 'Uni A'}, ...]
            keywords (list, optional): List of keywords.
            venue_name (str, optional): Name of the venue.
            full_text (str, optional): Full text of the paper.
        """
        if not self.graph_db:
            print("[KGG] Neo4j connection not available. Cannot process paper.")
            return

        print(f"\n[KGG] Processing paper: '{title}' (DOI: {doi})")

        # 1. Add Research Paper node (includes venue handling)
        self.graph_db.add_research_paper(
            title=title,
            abstract=abstract,
            publication_date=pubdate,
            doi=doi,
            keywords=keywords, # Will be added as topics by add_research_paper or later explicitly
            full_text=full_text,
            venue_name=venue_name
        )
        print(f"[KGG] - Added/Merged ResearchPaper: {title} ({doi})")
        if venue_name:
             print(f"[KGG] - Handled Venue: {venue_name} and linked to paper.")


        # 2. Add Authors and link to Paper
        if authors_data:
            author_ids_for_coauthor_linking = [] # Store (name, orcid) tuples or just primary id
            for author_info in authors_data:
                name = author_info.get("name")
                orcid = author_info.get("orcid")
                affiliation = author_info.get("affiliation")

                if not name:
                    print("[KGG] - Skipping author with no name.")
                    continue

                self.graph_db.add_author(name=name, orcid=orcid, affiliation_name=affiliation)
                print(f"[KGG] - Added/Merged Author: {name}" + (f" (ORCID: {orcid})" if orcid else "") + (f" (Affiliation: {affiliation})" if affiliation else ""))

                author_identifier = orcid if orcid else name
                author_ids_for_coauthor_linking.append({"id": author_identifier, "name": name, "is_orcid": bool(orcid)})

                self.graph_db.link_paper_to_author(
                    paper_identifier=doi,
                    author_identifier=author_identifier,
                    paper_by_doi=True,
                    author_by_orcid=bool(orcid)
                )
                print(f"[KGG]   - Linked Author '{name}' to Paper '{title}'")

            # Link Co-authors
            if len(author_ids_for_coauthor_linking) > 1:
                for i in range(len(author_ids_for_coauthor_linking)):
                    for j in range(i + 1, len(author_ids_for_coauthor_linking)):
                        author1 = author_ids_for_coauthor_linking[i]
                        author2 = author_ids_for_coauthor_linking[j]
                        self.graph_db.link_coauthors(
                            author1_identifier=author1["id"],
                            author2_identifier=author2["id"],
                            paper_identifier=doi,
                            author1_by_orcid=author1["is_orcid"],
                            author2_by_orcid=author2["is_orcid"],
                            paper_by_doi=True
                        )
                        print(f"[KGG]   - Linked Co-authors: '{author1['name']}' and '{author2['name']}' on paper '{doi}'")


        # 3. Add Topics from Keywords and link to Paper
        if keywords:
            for keyword in keywords:
                self.graph_db.add_topic(keyword)
                print(f"[KGG] - Added/Merged Topic (from keyword): {keyword}")
                self.graph_db.link_paper_to_topic(
                    paper_identifier=doi,
                    topic_name=keyword,
                    paper_by_doi=True
                )
                print(f"[KGG]   - Linked Topic '{keyword}' to Paper '{title}'")

        # 4. Text Processing for additional entities (Methods, Institutions, Topics)
        text_to_process = abstract
        if full_text: # Prefer full_text if available
            text_to_process = full_text

        if text_to_process:
            try:
                print("\n[KGG] Starting text processing for additional entities...")
                extracted_data = extract_entities_relations(text_to_process)

                if extracted_data:
                    # Process extracted methods
                    if "methods" in extracted_data["entities"]:
                        for method_info in extracted_data["entities"]["methods"]:
                            method_name = method_info.get("name")
                            method_desc = method_info.get("description")
                            if method_name:
                                self.graph_db.add_method(name=method_name, description=method_desc)
                                print(f"[KGG] - Added/Merged Method (from text): {method_name}")
                                self.graph_db.link_paper_to_method(
                                    paper_identifier=doi,
                                    method_name=method_name,
                                    paper_by_doi=True
                                )
                                print(f"[KGG]   - Linked Method '{method_name}' to Paper '{title}'")

                    # Process extracted institutions
                    if "institutions" in extracted_data["entities"]:
                        for inst_info in extracted_data["entities"]["institutions"]:
                            inst_name = inst_info.get("name")
                            inst_loc = inst_info.get("location")
                            if inst_name:
                                self.graph_db.add_institution(name=inst_name, location=inst_loc)
                                print(f"[KGG] - Added/Merged Institution (from text): {inst_name}")
                                # Future: Link paper to this institution via MENTIONS_INSTITUTION if desired

                    # Process additional topics extracted from text
                    if "topics" in extracted_data["entities"]:
                        for topic_info in extracted_data["entities"]["topics"]:
                            topic_name = topic_info.get("name")
                            if topic_name:
                                # Check if topic already added from keywords to avoid redundant linking
                                if not (keywords and topic_name in keywords):
                                    self.graph_db.add_topic(topic_name)
                                    print(f"[KGG] - Added/Merged Topic (from text): {topic_name}")
                                    self.graph_db.link_paper_to_topic(
                                        paper_identifier=doi,
                                        topic_name=topic_name,
                                        paper_by_doi=True
                                    )
                                    print(f"[KGG]   - Linked Topic '{topic_name}' to Paper '{title}'")
                                else:
                                    print(f"[KGG] - Topic (from text) '{topic_name}' already processed from keywords.")
                else:
                    print("[KGG] Text processor returned no data.")
            except ImportError: # Catching specific error from text_processor if spaCy is missing
                print("[KGG] Text processing skipped: spaCy library likely not found or model not loaded. Please check text_processor.py setup.")
            except Exception as e: # Catch other potential errors during text processing
                print(f"[KGG] Error during text processing: {e}")
        else:
            print("\n[KGG] No abstract or full text provided for advanced text processing.")

        print(f"\n[KGG] Paper processing finished for DOI: {doi}")

    def close_connection(self):
        if self.graph_db:
            self.graph_db.close()

if __name__ == '__main__':
    # Example Usage (requires a running Neo4j instance & credentials)
    # Replace with your Neo4j credentials and URI
    NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.environ.get("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password") # Ensure this is secure

    # Sample data
    sample_paper_data = {
        "title": "Advanced Knowledge Graph Generation Techniques",
        "doi": "10.9999/samplekgg.2024.001",
        "abstract": "This paper details novel methods for constructing knowledge graphs, including the use of machine learning and statistical models. Research conducted at Example University and Tech Solutions Inc.",
        "pubdate": "2024-05-01",
        "authors_data": [
            {"name": "Dr. Gen Erator", "orcid": "0000-0001-0002-0003", "affiliation": "Example University"},
            {"name": "Prof. Know Ledge", "affiliation": "Example University"},
            {"name": "A.I. Construct", "orcid": "0000-0003-0002-0001", "affiliation": "Tech Solutions Inc."}
        ],
        "keywords": ["Knowledge Graph", "NLP", "Automated KG Construction"],
        "venue_name": "Journal of Semantic Web Research",
        "full_text": "The full text would be much longer and provide more details for NLP..." # Optional
    }

    kgg = None
    try:
        # It's good practice to ensure KGG is only used if the connection is successful.
        # The KGG __init__ prints errors but doesn't stop if connection fails.
        # A check like `if kgg and kgg.graph_db:` could be useful before calling process_paper.
        kgg = KnowledgeGraphGenerator(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        if kgg.graph_db: # Proceed only if connection was successful
            kgg.process_paper(**sample_paper_data)

            # Example of processing a second paper
            sample_paper_data_2 = {
                "title": "The Role of Ontologies in AI",
                "doi": "10.9999/ontologies.2023.005",
                "abstract": "This work explores how ontologies enhance AI systems, performed at the Institute of Logic.",
                "authors_data": [
                    {"name": "Dr. Gen Erator", "orcid": "0000-0001-0002-0003", "affiliation": "Example University"}
                ],
                "keywords": ["Ontology", "AI", "Semantic Reasoning"],
                "venue_name": "AI Perspectives Conference"
            }
            kgg.process_paper(**sample_paper_data_2)

            # Example: Add citation link if Paper 1 cites Paper 2
            # Ensure papers exist first (which process_paper would do)
            # kgg.graph_db.link_papers_citation(sample_paper_data["doi"], sample_paper_data_2["doi"])
            # print(f"[KGG] - Added citation from {sample_paper_data['doi']} to {sample_paper_data_2['doi']}")

        else:
            print("[KGG Example] Could not process paper due to Neo4j connection issue.")

    except Exception as e:
        print(f"[KGG Example] An error occurred: {e}")
    finally:
        if kgg:
            kgg.close_connection()
```
