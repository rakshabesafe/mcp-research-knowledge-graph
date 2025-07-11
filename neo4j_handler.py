from neo4j import GraphDatabase

class Neo4jGraph:
    def __init__(self, uri, user, password):
        self._uri = uri
        self._user = user
        self._password = password
        self._driver = None
        try:
            self._driver = GraphDatabase.driver(self._uri, auth=(self._user, self._password))
            self._driver.verify_connectivity()
            print("[Neo4jHandler] Successfully connected to Neo4j.")
        except Exception as e:
            print(f"[Neo4jHandler] Failed to connect to Neo4j: {e}")
            # Re-raise to make it clear to the caller (e.g., lifespan manager)
            raise ConnectionError(f"Neo4j connection failed: {e}") from e

    def close(self):
        if self._driver is not None:
            self._driver.close()
            print("[Neo4jHandler] Neo4j connection closed.")

    def _run_query(self, query, parameters=None):
        if self._driver is None:
            print("[Neo4jHandler] Driver not initialized. Cannot run query.")
            return None # Or raise an error
        try:
            with self._driver.session() as session:
                result = session.run(query, parameters)
                return [record for record in result]
        except Exception as e:
            print(f"[Neo4jHandler] Error running Cypher query: {e}\nQuery: {query}\nParams: {parameters}")
            # Depending on desired behavior, might re-raise or return None/empty
            # For now, printing and returning None to avoid crashing the whole tool for one bad query.
            return None


    # --- Node Creation/Merging Methods ---

    def add_research_paper(self, doi: str, title: str, abstract: Optional[str] = None,
                           publication_date: Optional[str] = None, keywords: Optional[list] = None,
                           full_text_link: Optional[str] = None,
                           venue_name: Optional[str] = None,
                           venue_issn_isbn: Optional[str] = None,
                           venue_publisher: Optional[str] = None):
        # Node label is Paper now
        query = """
        MERGE (p:Paper {doi: $doi})
        ON CREATE SET
            p.title = $title, p.abstract = $abstract, p.publication_date = $publication_date,
            p.keywords = $keywords, p.full_text_link = $full_text_link,
            p.created_at = timestamp()
        ON MATCH SET
            p.title = $title, p.abstract = $abstract, p.publication_date = $publication_date,
            p.keywords = $keywords, p.full_text_link = $full_text_link,
            p.updated_at = timestamp()
        RETURN p
        """
        if not doi: # DOI is crucial for merging
            print("[Neo4jHandler] DOI is required to add/merge a Paper.")
            return None

        params = {
            "doi": doi, "title": title, "abstract": abstract,
            "publication_date": publication_date, "keywords": keywords,
            "full_text_link": full_text_link
        }
        paper_node = self._run_query(query, params)

        if venue_name:
            self.add_publication_venue(name=venue_name, issn_isbn=venue_issn_isbn, publisher=venue_publisher)
            self.link_paper_to_publication_venue(paper_doi=doi, venue_name=venue_name)
        return paper_node

    def add_author(self, name: str, orcid: Optional[str] = None, email: Optional[str] = None,
                   affiliation_name: Optional[str] = None, affiliation_location: Optional[str] = None):
        # Node label is Author
        if orcid:
            query = """
            MERGE (au:Author {orcid: $orcid})
            ON CREATE SET au.name = $name, au.email = $email, au.created_at = timestamp()
            ON MATCH SET au.name = $name, au.email = $email, au.updated_at = timestamp()
            RETURN au
            """
            params = {"orcid": orcid, "name": name, "email": email}
        else: # Merge by name if no ORCID
            query = """
            MERGE (au:Author {name: $name})
            ON CREATE SET au.email = $email, au.orcid = $orcid, au.created_at = timestamp()
            ON MATCH SET au.email = $email, au.orcid = $orcid, au.updated_at = timestamp()
            RETURN au
            """
            params = {"name": name, "email": email, "orcid": orcid}

        author_node = self._run_query(query, params)
        if affiliation_name:
            self.add_affiliation(name=affiliation_name, location=affiliation_location)
            author_identifier = orcid if orcid else name
            self.link_author_to_affiliation(author_identifier=author_identifier, affiliation_name=affiliation_name, by_orcid=bool(orcid))
        return author_node

    def add_affiliation(self, name: str, location: Optional[str] = None):
        # Node label is Affiliation
        query = """
        MERGE (aff:Affiliation {name: $name})
        ON CREATE SET aff.location = $location, aff.created_at = timestamp()
        ON MATCH SET aff.location = $location, aff.updated_at = timestamp()
        RETURN aff
        """
        return self._run_query(query, {"name": name, "location": location})

    def add_publication_venue(self, name: str, issn_isbn: Optional[str] = None, publisher: Optional[str] = None):
        # Node label is PublicationVenue
        query = """
        MERGE (pv:PublicationVenue {name: $name})
        ON CREATE SET pv.issn_isbn = $issn_isbn, pv.publisher = $publisher, pv.created_at = timestamp()
        ON MATCH SET pv.issn_isbn = $issn_isbn, pv.publisher = $publisher, pv.updated_at = timestamp()
        RETURN pv
        """
        return self._run_query(query, {"name": name, "issn_isbn": issn_isbn, "publisher": publisher})

    def add_research_topic(self, name: str):
        # Node label is ResearchTopic
        query = """
        MERGE (rt:ResearchTopic {name: $name})
        ON CREATE SET rt.created_at = timestamp()
        RETURN rt
        """
        return self._run_query(query, {"name": name})

    def add_method(self, name: str, description: Optional[str] = None):
        # Node label is Method (same as before)
        query = """
        MERGE (m:Method {name: $name})
        ON CREATE SET m.description = $description, m.created_at = timestamp()
        ON MATCH SET m.description = $description, m.updated_at = timestamp()
        RETURN m
        """
        return self._run_query(query, {"name": name, "description": description})

    def add_dataset(self, name: str, description: Optional[str] = None, url: Optional[str] = None):
        # Node label is Dataset
        query = """
        MERGE (d:Dataset {name: $name})
        ON CREATE SET d.description = $description, d.url = $url, d.created_at = timestamp()
        ON MATCH SET d.description = $description, d.url = $url, d.updated_at = timestamp()
        RETURN d
        """
        return self._run_query(query, {"name": name, "description": description, "url": url})

    def add_funder(self, name: str):
        # Node label is Funder
        query = """
        MERGE (f:Funder {name: $name})
        ON CREATE SET f.created_at = timestamp()
        RETURN f
        """
        return self._run_query(query, {"name": name})

    # --- Relationship Linking Methods ---

    def link_paper_to_author(self, paper_doi: str, author_identifier: str, by_orcid: bool = False):
        # Relationship :HAS_AUTHOR
        author_match_prop = "orcid" if by_orcid else "name"
        query = f"""
        MATCH (p:Paper {{doi: $paper_doi}})
        MATCH (au:Author {{{author_match_prop}: $author_id}})
        MERGE (p)-[r:HAS_AUTHOR]->(au)
        MERGE (au)-[r_inv:AUTHORED_BY]->(p) // Maintain inverse for querying ease
        RETURN type(r), type(r_inv)
        """
        return self._run_query(query, {"paper_doi": paper_doi, "author_id": author_identifier})

    def link_author_to_affiliation(self, author_identifier: str, affiliation_name: str, by_orcid: bool = False):
        # Relationship :IS_AFFILIATED_WITH
        author_match_prop = "orcid" if by_orcid else "name"
        query = f"""
        MATCH (au:Author {{{author_match_prop}: $author_id}})
        MATCH (aff:Affiliation {{name: $affiliation_name}})
        MERGE (au)-[r:IS_AFFILIATED_WITH]->(aff)
        RETURN type(r)
        """
        return self._run_query(query, {"author_id": author_identifier, "affiliation_name": affiliation_name})

    def link_paper_to_publication_venue(self, paper_doi: str, venue_name: str):
        # Relationship :PUBLISHED_IN
        query = """
        MATCH (p:Paper {doi: $paper_doi})
        MATCH (pv:PublicationVenue {name: $venue_name})
        MERGE (p)-[r:PUBLISHED_IN]->(pv)
        RETURN type(r)
        """
        return self._run_query(query, {"paper_doi": paper_doi, "venue_name": venue_name})

    def link_paper_to_research_topic(self, paper_doi: str, topic_name: str):
        # Relationship :HAS_TOPIC
        query = """
        MATCH (p:Paper {doi: $paper_doi})
        MATCH (rt:ResearchTopic {name: $topic_name})
        MERGE (p)-[r:HAS_TOPIC]->(rt)
        RETURN type(r)
        """
        return self._run_query(query, {"paper_doi": paper_doi, "topic_name": topic_name})

    def link_paper_to_method(self, paper_doi: str, method_name: str):
        # Relationship :USES_METHOD
        query = """
        MATCH (p:Paper {doi: $paper_doi})
        MATCH (m:Method {name: $method_name})
        MERGE (p)-[r:USES_METHOD]->(m)
        RETURN type(r)
        """
        return self._run_query(query, {"paper_doi": paper_doi, "method_name": method_name})

    def link_paper_to_dataset(self, paper_doi: str, dataset_name: str):
        # Relationship :USES_DATASET
        query = """
        MATCH (p:Paper {doi: $paper_doi})
        MATCH (d:Dataset {name: $dataset_name})
        MERGE (p)-[r:USES_DATASET]->(d)
        RETURN type(r)
        """
        return self._run_query(query, {"paper_doi": paper_doi, "dataset_name": dataset_name})

    def link_paper_to_funder(self, paper_doi: str, funder_name: str):
        # Relationship :IS_FUNDED_BY
        query = """
        MATCH (p:Paper {doi: $paper_doi})
        MATCH (f:Funder {name: $funder_name})
        MERGE (p)-[r:IS_FUNDED_BY]->(f)
        RETURN type(r)
        """
        return self._run_query(query, {"paper_doi": paper_doi, "funder_name": funder_name})

    def link_papers_citation(self, citing_paper_doi: str, cited_paper_doi: str):
        # Relationship :CITES
        query = """
        MATCH (citing_p:Paper {doi: $citing_doi})
        MATCH (cited_p:Paper {doi: $cited_doi})
        MERGE (citing_p)-[r:CITES]->(cited_p)
        MERGE (cited_p)-[r_inv:REFERENCED_BY]->(citing_p) // Maintain inverse
        RETURN type(r), type(r_inv)
        """
        return self._run_query(query, {"citing_doi": citing_paper_doi, "cited_doi": cited_paper_doi})

    def link_coauthors(self, author1_identifier: str, author2_identifier: str, paper_doi: str,
                       author1_by_orcid: bool = False, author2_by_orcid: bool = False):
        # This still links authors on a specific paper, relationship name can be generic or specific
        # New ontology doesn't specify a co-author link, but it's often useful.
        # Let's keep it as COAUTHORED_WITH_ON or make it more generic if preferred.
        # For now, keeping the specific-to-paper link.
        author1_match_prop = "orcid" if author1_by_orcid else "name"
        author2_match_prop = "orcid" if author2_by_orcid else "name"

        query = f"""
        MATCH (a1:Author {{{author1_match_prop}: $author1_id}})
        MATCH (a2:Author {{{author2_match_prop}: $author2_id}})
        MATCH (p:Paper {{doi: $paper_doi}})
        // Ensure both authors are connected to the paper via HAS_AUTHOR
        MERGE (a1)<-[:HAS_AUTHOR]-(p)-[:HAS_AUTHOR]->(a2)
        // Create co-author link, could be specific to the paper or general
        MERGE (a1)-[r:COAUTHORED_WITH_ON {{paper_doi: $paper_doi}}]->(a2)
        MERGE (a2)-[r_inv:COAUTHORED_WITH_ON {{paper_doi: $paper_doi}}]->(a1)
        RETURN type(r), type(r_inv)
        """
        return self._run_query(query, {
            "author1_id": author1_identifier,
            "author2_id": author2_identifier,
            "paper_doi": paper_doi
        })

# Example Usage (for testing this module directly)
if __name__ == '__main__':
    # This example requires NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD environment variables to be set
    # or default values to work with a local Neo4j instance.
    import os
    NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password") # Replace with your actual password

    if NEO4J_PASSWORD == "password":
        print("WARNING: Using default Neo4j password for example. Please ensure it's changed for production.")

    graph = None
    try:
        graph = Neo4jGraph(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

        # Test new ontology
        paper1_doi = "10.test/paper001"
        graph.add_research_paper(
            doi=paper1_doi, title="Paper on New Methods", abstract="Uses method X.",
            keywords=["TopicA", "Methodology"], full_text_link="http://example.com/paper001.pdf",
            venue_name="Journal of Test Results", venue_issn_isbn="1234-5678", venue_publisher="Test Pub"
        )
        print(f"Added Paper: {paper1_doi}")

        graph.add_author(name="Dr. Test", orcid="0000-0000-0000-0001", email="dr.test@example.com", affiliation_name="Test University", affiliation_location="Testville")
        print("Added Author: Dr. Test")
        graph.link_paper_to_author(paper_doi=paper1_doi, author_identifier="0000-0000-0000-0001", by_orcid=True)
        print("Linked Dr. Test to paper.")

        graph.add_research_topic("TopicA") # Should merge
        graph.link_paper_to_research_topic(paper_doi=paper1_doi, topic_name="TopicA")
        print("Linked TopicA to paper.")

        graph.add_method(name="Method X", description="A novel approach.")
        graph.link_paper_to_method(paper_doi=paper1_doi, method_name="Method X")
        print("Linked Method X to paper.")

        graph.add_dataset(name="Dataset Alpha", description="Primary dataset used.", url="http://example.com/dataset_alpha")
        graph.link_paper_to_dataset(paper_doi=paper1_doi, dataset_name="Dataset Alpha")
        print("Linked Dataset Alpha to paper.")

        graph.add_funder(name="National Test Foundation")
        graph.link_paper_to_funder(paper_doi=paper1_doi, funder_name="National Test Foundation")
        print("Linked National Test Foundation to paper.")

        paper2_doi = "10.test/paper002"
        graph.add_research_paper(doi=paper2_doi, title="Citing Paper")
        graph.link_papers_citation(citing_paper_doi=paper2_doi, cited_paper_doi=paper1_doi)
        print(f"Linked {paper2_doi} CITES {paper1_doi}")


    except ConnectionError as ce:
        print(f"Example usage failed to connect to Neo4j: {ce}")
    except Exception as e:
        print(f"An error occurred in example usage: {e}")
    finally:
        if graph:
            graph.close()
```
