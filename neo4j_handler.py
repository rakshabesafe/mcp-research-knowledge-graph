from neo4j import GraphDatabase
from typing import Optional # Added for type hinting

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
            raise ConnectionError(f"Neo4j connection failed: {e}") from e

    def close(self):
        if self._driver is not None:
            self._driver.close()
            print("[Neo4jHandler] Neo4j connection closed.")

    def _run_query(self, query, parameters=None):
        if self._driver is None:
            print("[Neo4jHandler] Driver not initialized. Cannot run query.")
            return None
        try:
            with self._driver.session() as session:
                result = session.run(query, parameters)
                return [record for record in result]
        except Exception as e:
            print(f"[Neo4jHandler] Error running Cypher query: {e}\nQuery: {query}\nParams: {parameters}")
            return None

    # --- Node Creation/Merging Methods (Updated Ontology) ---

    def add_research_paper(self, doi: str, title: str, abstract: Optional[str] = None,
                           publication_date: Optional[str] = None, keywords: Optional[list] = None,
                           full_text_link: Optional[str] = None,
                           # Venue details passed directly now
                           venue_name: Optional[str] = None,
                           venue_issn_isbn: Optional[str] = None,
                           venue_publisher: Optional[str] = None):
        query = """
        MERGE (p:Paper {doi: $doi})
        ON CREATE SET p.title = $title, p.abstract = $abstract, p.publication_date = $publication_date,
                      p.keywords = $keywords, p.full_text_link = $full_text_link, p.created_at = timestamp()
        ON MATCH SET p.title = $title, p.abstract = $abstract, p.publication_date = $publication_date,
                     p.keywords = $keywords, p.full_text_link = $full_text_link, p.updated_at = timestamp()
        RETURN p
        """
        if not doi:
            print("[Neo4jHandler] DOI is required to add/merge a Paper.")
            return None

        params = {
            "doi": doi, "title": title, "abstract": abstract,
            "publication_date": publication_date, "keywords": keywords,
            "full_text_link": full_text_link
        }
        paper_node_result = self._run_query(query, params)

        if venue_name: # If venue_name is provided, create/merge venue and link
            self.add_publication_venue(name=venue_name, issn_isbn=venue_issn_isbn, publisher=venue_publisher)
            self.link_paper_to_publication_venue(paper_doi=doi, venue_name=venue_name)
        return paper_node_result

    def add_author(self, name: str, orcid: Optional[str] = None, email: Optional[str] = None,
                   affiliation_name: Optional[str] = None, affiliation_location: Optional[str] = None):
        if orcid:
            query = """
            MERGE (au:Author {orcid: $orcid})
            ON CREATE SET au.name = $name, au.email = $email, au.created_at = timestamp()
            ON MATCH SET au.name = $name, au.email = $email, au.updated_at = timestamp()
            RETURN au
            """
            params = {"orcid": orcid, "name": name, "email": email}
        else:
            query = """
            MERGE (au:Author {name: $name})
            ON CREATE SET au.email = $email, au.orcid = $orcid, au.created_at = timestamp()
            ON MATCH SET au.email = $email, au.orcid = $orcid, au.updated_at = timestamp()
            RETURN au
            """
            params = {"name": name, "email": email, "orcid": orcid} # Pass ORCID even if None to set on create

        author_node_result = self._run_query(query, params)
        if affiliation_name:
            self.add_affiliation(name=affiliation_name, location=affiliation_location)
            author_identifier = orcid if orcid else name
            self.link_author_to_affiliation(author_identifier=author_identifier, affiliation_name=affiliation_name, by_orcid=bool(orcid))
        return author_node_result

    def add_affiliation(self, name: str, location: Optional[str] = None):
        query = """
        MERGE (aff:Affiliation {name: $name})
        ON CREATE SET aff.location = $location, aff.created_at = timestamp()
        ON MATCH SET aff.location = $location, aff.updated_at = timestamp()
        RETURN aff
        """
        return self._run_query(query, {"name": name, "location": location})

    def add_publication_venue(self, name: str, issn_isbn: Optional[str] = None, publisher: Optional[str] = None):
        query = """
        MERGE (pv:PublicationVenue {name: $name})
        ON CREATE SET pv.issn_isbn = $issn_isbn, pv.publisher = $publisher, pv.created_at = timestamp()
        ON MATCH SET pv.issn_isbn = $issn_isbn, pv.publisher = $publisher, pv.updated_at = timestamp()
        RETURN pv
        """
        return self._run_query(query, {"name": name, "issn_isbn": issn_isbn, "publisher": publisher})

    def add_research_topic(self, name: str):
        query = """
        MERGE (rt:ResearchTopic {name: $name})
        ON CREATE SET rt.created_at = timestamp()
        RETURN rt
        """
        return self._run_query(query, {"name": name})

    def add_method(self, name: str, description: Optional[str] = None):
        query = """
        MERGE (m:Method {name: $name})
        ON CREATE SET m.description = $description, m.created_at = timestamp()
        ON MATCH SET m.description = $description, m.updated_at = timestamp()
        RETURN m
        """
        return self._run_query(query, {"name": name, "description": description})

    def add_dataset(self, name: str, description: Optional[str] = None, url: Optional[str] = None):
        query = """
        MERGE (d:Dataset {name: $name})
        ON CREATE SET d.description = $description, d.url = $url, d.created_at = timestamp()
        ON MATCH SET d.description = $description, d.url = $url, d.updated_at = timestamp()
        RETURN d
        """
        return self._run_query(query, {"name": name, "description": description, "url": url})

    def add_funder(self, name: str):
        query = """
        MERGE (f:Funder {name: $name})
        ON CREATE SET f.created_at = timestamp()
        RETURN f
        """
        return self._run_query(query, {"name": name})

    def add_objective(self, description: str):
        query = """
        MERGE (o:Objective {description: $description})
        ON CREATE SET o.created_at = timestamp()
        RETURN o
        """
        return self._run_query(query, {"description": description})

    def add_hypothesis(self, description: str):
        query = """
        MERGE (h:Hypothesis {description: $description})
        ON CREATE SET h.created_at = timestamp()
        RETURN h
        """
        return self._run_query(query, {"description": description})

    def add_concept(self, name: str, definition: Optional[str] = None, first_mentioned_doi: Optional[str] = None):
        query = """
        MERGE (c:Concept {name: $name})
        ON CREATE SET c.definition = $definition, c.first_mentioned_doi = $first_mentioned_doi, c.created_at = timestamp()
        ON MATCH SET c.definition = $definition, c.first_mentioned_doi = $first_mentioned_doi, c.updated_at = timestamp()
        RETURN c
        """
        return self._run_query(query, {"name": name, "definition": definition, "first_mentioned_doi": first_mentioned_doi})

    def add_research_problem(self, description: str):
        query = """
        MERGE (rp:ResearchProblem {description: $description})
        ON CREATE SET rp.created_at = timestamp()
        RETURN rp
        """
        return self._run_query(query, {"description": description})

    def add_limitation(self, description: str):
        query = """
        MERGE (l:Limitation {description: $description})
        ON CREATE SET l.created_at = timestamp()
        RETURN l
        """
        return self._run_query(query, {"description": description})

    def add_future_work(self, description: str):
        query = """
        MERGE (fw:FutureWork {description: $description})
        ON CREATE SET fw.created_at = timestamp()
        RETURN fw
        """
        return self._run_query(query, {"description": description})

    # --- Relationship Linking Methods (Updated Ontology) ---

    def link_paper_to_author(self, paper_doi: str, author_identifier: str, by_orcid: bool = False):
        author_match_prop = "orcid" if by_orcid else "name"
        query = f"""
        MATCH (p:Paper {{doi: $paper_doi}})
        MATCH (au:Author {{{author_match_prop}: $author_id}})
        MERGE (p)-[r:HAS_AUTHOR]->(au)
        MERGE (au)-[r_inv:AUTHORED_BY]->(p)
        RETURN type(r), type(r_inv)
        """
        return self._run_query(query, {"paper_doi": paper_doi, "author_id": author_identifier})

    def link_author_to_affiliation(self, author_identifier: str, affiliation_name: str, by_orcid: bool = False):
        author_match_prop = "orcid" if by_orcid else "name"
        query = f"""
        MATCH (au:Author {{{author_match_prop}: $author_id}})
        MATCH (aff:Affiliation {{name: $affiliation_name}})
        MERGE (au)-[r:IS_AFFILIATED_WITH]->(aff)
        RETURN type(r)
        """
        return self._run_query(query, {"author_id": author_identifier, "affiliation_name": affiliation_name})

    def link_paper_to_publication_venue(self, paper_doi: str, venue_name: str):
        query = """
        MATCH (p:Paper {doi: $paper_doi})
        MATCH (pv:PublicationVenue {name: $venue_name})
        MERGE (p)-[r:PUBLISHED_IN]->(pv)
        RETURN type(r)
        """
        return self._run_query(query, {"paper_doi": paper_doi, "venue_name": venue_name})

    def link_paper_to_research_topic(self, paper_doi: str, topic_name: str):
        query = """
        MATCH (p:Paper {doi: $paper_doi})
        MATCH (rt:ResearchTopic {name: $topic_name})
        MERGE (p)-[r:HAS_TOPIC]->(rt)
        RETURN type(r)
        """
        return self._run_query(query, {"paper_doi": paper_doi, "topic_name": topic_name})

    def link_paper_to_method(self, paper_doi: str, method_name: str):
        query = """
        MATCH (p:Paper {doi: $paper_doi})
        MATCH (m:Method {name: $method_name})
        MERGE (p)-[r:USES_METHOD]->(m)
        RETURN type(r)
        """
        return self._run_query(query, {"paper_doi": paper_doi, "method_name": method_name})

    def link_paper_to_dataset(self, paper_doi: str, dataset_name: str):
        query = """
        MATCH (p:Paper {doi: $paper_doi})
        MATCH (d:Dataset {name: $dataset_name})
        MERGE (p)-[r:USES_DATASET]->(d)
        RETURN type(r)
        """
        return self._run_query(query, {"paper_doi": paper_doi, "dataset_name": dataset_name})

    def link_paper_to_funder(self, paper_doi: str, funder_name: str):
        query = """
        MATCH (p:Paper {doi: $paper_doi})
        MATCH (f:Funder {name: $funder_name})
        MERGE (p)-[r:IS_FUNDED_BY]->(f)
        RETURN type(r)
        """
        return self._run_query(query, {"paper_doi": paper_doi, "funder_name": funder_name})

    def link_papers_citation(self, citing_paper_doi: str, cited_paper_doi: str):
        query = """
        MATCH (citing_p:Paper {doi: $citing_doi})
        MATCH (cited_p:Paper {doi: $cited_doi})
        MERGE (citing_p)-[r:CITES]->(cited_p)
        MERGE (cited_p)-[r_inv:REFERENCED_BY]->(citing_p)
        RETURN type(r), type(r_inv)
        """
        return self._run_query(query, {"citing_doi": citing_paper_doi, "cited_doi": cited_paper_doi})

    def link_paper_to_objective(self, paper_doi: str, objective_description: str):
        query = """
        MATCH (p:Paper {doi: $paper_doi})
        MATCH (o:Objective {description: $objective_description})
        MERGE (p)-[r:HAS_OBJECTIVE]->(o)
        RETURN type(r)
        """
        return self._run_query(query, {"paper_doi": paper_doi, "objective_description": objective_description})

    def link_paper_to_hypothesis(self, paper_doi: str, hypothesis_description: str):
        query = """
        MATCH (p:Paper {doi: $paper_doi})
        MATCH (h:Hypothesis {description: $hypothesis_description})
        MERGE (p)-[r:HAS_HYPOTHESIS]->(h)
        RETURN type(r)
        """
        return self._run_query(query, {"paper_doi": paper_doi, "hypothesis_description": hypothesis_description})

    def link_objective_to_hypothesis(self, objective_description: str, hypothesis_description: str):
        query = """
        MATCH (o:Objective {description: $objective_description})
        MATCH (h:Hypothesis {description: $hypothesis_description})
        MERGE (o)-[r:IS_ADDRESSED_BY]->(h)
        RETURN type(r)
        """
        return self._run_query(query, {"objective_description": objective_description, "hypothesis_description": hypothesis_description})

    def link_hypothesis_to_method(self, hypothesis_description: str, method_name: str):
        query = """
        MATCH (h:Hypothesis {description: $hypothesis_description})
        MATCH (m:Method {name: $method_name})
        MERGE (h)-[r:IS_TESTED_BY]->(m)
        RETURN type(r)
        """
        return self._run_query(query, {"hypothesis_description": hypothesis_description, "method_name": method_name})

    def link_paper_to_concept(self, paper_doi: str, concept_name: str, relationship_type: str = "MENTIONS_CONCEPT"):
        valid_rels = ["MENTIONS_CONCEPT", "INTRODUCES_CONCEPT"]
        if relationship_type not in valid_rels:
            print(f"[Neo4jHandler] Invalid relationship type for paper to concept: {relationship_type}. Must be one of {valid_rels}")
            return None
        query = f"""
        MATCH (p:Paper {{doi: $paper_doi}})
        MATCH (c:Concept {{name: $concept_name}})
        MERGE (p)-[r:{relationship_type}]->(c)
        RETURN type(r)
        """
        return self._run_query(query, {"paper_doi": paper_doi, "concept_name": concept_name})

    def link_concept_to_research_topic(self, concept_name: str, topic_name: str):
        query = """
        MATCH (c:Concept {name: $concept_name})
        MATCH (rt:ResearchTopic {name: $topic_name})
        MERGE (c)-[r:PART_OF]->(rt)
        RETURN type(r)
        """
        return self._run_query(query, {"concept_name": concept_name, "topic_name": topic_name})

    def link_concept_to_concept(self, concept1_name: str, concept2_name: str, relationship_type: str):
        valid_rels = ["IS_SUB_CONCEPT_OF", "IS_PREREQUISITE_FOR", "IS_RELATED_TO"]
        if relationship_type not in valid_rels:
            print(f"[Neo4jHandler] Invalid relationship type between concepts: {relationship_type}. Must be one of {valid_rels}")
            return None
        query = f"""
        MATCH (c1:Concept {{name: $concept1_name}})
        MATCH (c2:Concept {{name: $concept2_name}})
        MERGE (c1)-[r:{relationship_type}]->(c2)
        RETURN type(r)
        """
        return self._run_query(query, {"concept1_name": concept1_name, "concept2_name": concept2_name})

    def link_paper_to_research_problem(self, paper_doi: str, problem_description: str):
        query = """
        MATCH (p:Paper {doi: $paper_doi})
        MATCH (rp:ResearchProblem {description: $problem_description})
        MERGE (p)-[r:ADDRESSES]->(rp)
        RETURN type(r)
        """
        return self._run_query(query, {"paper_doi": paper_doi, "problem_description": problem_description})

    def link_paper_to_limitation(self, paper_doi: str, limitation_description: str):
        query = """
        MATCH (p:Paper {doi: $paper_doi})
        MATCH (l:Limitation {description: $limitation_description})
        MERGE (p)-[r:HAS_LIMITATION]->(l)
        RETURN type(r)
        """
        return self._run_query(query, {"paper_doi": paper_doi, "limitation_description": limitation_description})

    def link_paper_to_future_work(self, paper_doi: str, future_work_description: str):
        query = """
        MATCH (p:Paper {doi: $paper_doi})
        MATCH (fw:FutureWork {description: $future_work_description})
        MERGE (p)-[r:SUGGESTS]->(fw)
        RETURN type(r)
        """
        return self._run_query(query, {"paper_doi": paper_doi, "future_work_description": future_work_description})

    def link_coauthors(self, author1_identifier: str, author2_identifier: str, paper_doi: str,
                       author1_by_orcid: bool = False, author2_by_orcid: bool = False):
        author1_match_prop = "orcid" if author1_by_orcid else "name"
        author2_match_prop = "orcid" if author2_by_orcid else "name"
        query = f"""
        MATCH (a1:Author {{{author1_match_prop}: $author1_id}})
        MATCH (a2:Author {{{author2_match_prop}: $author2_id}})
        MATCH (p:Paper {{doi: $paper_doi}})
        MERGE (a1)<-[:HAS_AUTHOR]-(p)-[:HAS_AUTHOR]->(a2)
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
    import os
    NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")

    if NEO4J_PASSWORD == "password":
        print("WARNING: Using default Neo4j password for example.")

    graph = None
    try:
        graph = Neo4jGraph(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

        paper1_doi = "10.test/paper001.v3"
        graph.add_research_paper(
            doi=paper1_doi, title="Paper on New Methods and Concepts",
            abstract="Uses method X. Introduces Concept Alpha. Addresses problem Y.",
            keywords=["TopicAlpha", "ConceptLearning"],
            full_text_link="http://example.com/paper001v3.pdf",
            venue_name="Journal of Ontological Engineering",
            venue_issn_isbn="2345-6789",
            venue_publisher="Ontology Press"
        )
        print(f"Added Paper: {paper1_doi}")

        graph.add_author(name="Dr. Concepta", orcid="0000-0001-0002-0003",
                         email="concepta@example.com",
                         affiliation_name="Conceptual University",
                         affiliation_location="Ideapolis")
        print("Added Author: Dr. Concepta")
        graph.link_paper_to_author(paper_doi=paper1_doi, author_identifier="0000-0001-0002-0003", by_orcid=True)

        graph.add_research_topic("ConceptLearning")
        graph.link_paper_to_research_topic(paper_doi=paper1_doi, topic_name="ConceptLearning")

        graph.add_method(name="Method X", description="A refined approach.")
        graph.link_paper_to_method(paper_doi=paper1_doi, method_name="Method X")

        # New entities and links
        obj_desc = "To validate Concept Alpha."
        graph.add_objective(obj_desc)
        graph.link_paper_to_objective(paper1_doi, obj_desc)

        hyp_desc = "Concept Alpha improves understanding."
        graph.add_hypothesis(hyp_desc)
        graph.link_paper_to_hypothesis(paper1_doi, hyp_desc)
        graph.link_objective_to_hypothesis(obj_desc, hyp_desc)
        graph.link_hypothesis_to_method(hyp_desc, "Method X")

        concept_name = "Concept Alpha"
        graph.add_concept(name=concept_name, definition="A foundational element in this work.", first_mentioned_doi=paper1_doi)
        graph.link_paper_to_concept(paper_doi=paper1_doi, concept_name=concept_name, relationship_type="INTRODUCES_CONCEPT")
        graph.link_concept_to_research_topic(concept_name=concept_name, topic_name="ConceptLearning")

        prob_desc = "Lack of clarity in conceptual models."
        graph.add_research_problem(prob_desc)
        graph.link_paper_to_research_problem(paper1_doi, prob_desc)

        limit_desc = "Study limited to specific domain."
        graph.add_limitation(limit_desc)
        graph.link_paper_to_limitation(paper1_doi, limit_desc)

        fw_desc = "Apply Concept Alpha to other domains."
        graph.add_future_work(fw_desc)
        graph.link_paper_to_future_work(paper1_doi, fw_desc)

        print("Added and linked new ontology elements.")

    except ConnectionError as ce:
        print(f"Example usage failed to connect to Neo4j: {ce}")
    except Exception as e:
        print(f"An error occurred in example usage: {e}")
    finally:
        if graph:
            graph.close()
