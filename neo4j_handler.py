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
            print("Successfully connected to Neo4j.")
        except Exception as e:
            print(f"Failed to connect to Neo4j: {e}")
            raise

    def close(self):
        if self._driver is not None:
            self._driver.close()
            print("Neo4j connection closed.")

    def _run_query(self, query, parameters=None):
        if self._driver is None:
            print("Driver not initialized.")
            return None
        with self._driver.session() as session:
            result = session.run(query, parameters)
            return [record for record in result]

    def add_research_paper(self, title, abstract=None, publication_date=None, doi=None, keywords=None, full_text=None, venue_name=None):
        query = """
        MERGE (p:ResearchPaper {doi: $doi})
        ON CREATE SET p.title = $title, p.abstract = $abstract, p.publication_date = $publication_date,
                      p.keywords = $keywords, p.full_text = $full_text, p.created_at = timestamp()
        ON MATCH SET p.title = $title, p.abstract = $abstract, p.publication_date = $publication_date,
                     p.keywords = $keywords, p.full_text = $full_text, p.updated_at = timestamp()
        RETURN p
        """
        # Ensure DOI is present for merging
        if not doi:
            # If DOI is not available, we might use title for merging, but it's less reliable.
            # For now, let's assume DOI is the primary key for ResearchPaper.
            # Alternatively, create a unique ID if DOI is missing.
            # This example prioritizes DOI.
            print("DOI is required to add/merge a research paper.")
            # Fallback or error handling needed if DOI is truly optional for MERGE.
            # For now, let's use title if DOI is None, but this is not ideal for uniqueness.
            if title:
                 query_by_title = """
                 MERGE (p:ResearchPaper {title: $title})
                 ON CREATE SET p.doi = $doi, p.abstract = $abstract, p.publication_date = $publication_date,
                               p.keywords = $keywords, p.full_text = $full_text, p.created_at = timestamp()
                 ON MATCH SET p.doi = $doi, p.abstract = $abstract, p.publication_date = $publication_date,
                              p.keywords = $keywords, p.full_text = $full_text, p.updated_at = timestamp()
                 RETURN p
                 """
                 return self._run_query(query_by_title, {
                     "title": title, "abstract": abstract, "publication_date": publication_date,
                     "doi": doi, "keywords": keywords, "full_text": full_text
                 })
            else:
                print("DOI or Title is required to add/merge a research paper.")
                return None


        params = {
            "doi": doi, "title": title, "abstract": abstract,
            "publication_date": publication_date, "keywords": keywords,
            "full_text": full_text
        }
        result = self._run_query(query, params)

        if venue_name:
            self.add_venue(venue_name)
            self.link_paper_to_venue(doi if doi else title, venue_name)
        return result

    def add_author(self, name, affiliation_name=None, orcid=None):
        # Prefer ORCID for merging if available
        if orcid:
            query = """
            MERGE (a:Author {orcid: $orcid})
            ON CREATE SET a.name = $name, a.created_at = timestamp()
            ON MATCH SET a.name = $name, a.updated_at = timestamp()
            RETURN a
            """
            params = {"orcid": orcid, "name": name}
        else:
            query = """
            MERGE (a:Author {name: $name})
            ON CREATE SET a.created_at = timestamp()
            ON MATCH SET a.updated_at = timestamp()
            RETURN a
            """
            params = {"name": name}

        result = self._run_query(query, params)
        if affiliation_name:
            self.add_institution(affiliation_name)
            # Use ORCID if available for linking, else name
            author_identifier = orcid if orcid else name
            self.link_author_to_institution(author_identifier, affiliation_name, by_orcid=bool(orcid))
        return result

    def add_topic(self, name):
        query = """
        MERGE (t:Topic {name: $name})
        ON CREATE SET t.created_at = timestamp()
        RETURN t
        """
        return self._run_query(query, {"name": name})

    def add_method(self, name, description=None):
        query = """
        MERGE (m:Method {name: $name})
        ON CREATE SET m.description = $description, m.created_at = timestamp()
        ON MATCH SET m.description = $description, m.updated_at = timestamp()
        RETURN m
        """
        return self._run_query(query, {"name": name, "description": description})

    def add_institution(self, name, location=None):
        query = """
        MERGE (i:Institution {name: $name})
        ON CREATE SET i.location = $location, i.created_at = timestamp()
        ON MATCH SET i.location = $location, i.updated_at = timestamp()
        RETURN i
        """
        return self._run_query(query, {"name": name, "location": location})

    def add_venue(self, name): # e.g., conference or journal
        query = """
        MERGE (v:Venue {name: $name})
        ON CREATE SET v.created_at = timestamp()
        RETURN v
        """
        return self._run_query(query, {"name": name})

    def link_paper_to_author(self, paper_identifier, author_identifier, paper_by_doi=True, author_by_orcid=False):
        paper_match_prop = "doi" if paper_by_doi else "title"
        author_match_prop = "orcid" if author_by_orcid else "name"

        query = f"""
        MATCH (p:ResearchPaper {{{paper_match_prop}: $paper_id}})
        MATCH (a:Author {{{author_match_prop}: $author_id}})
        MERGE (p)-[r:HAS_AUTHOR]->(a)
        MERGE (a)-[r_inv:AUTHORED_BY]->(p)
        RETURN type(r), type(r_inv)
        """
        return self._run_query(query, {"paper_id": paper_identifier, "author_id": author_identifier})

    def link_paper_to_topic(self, paper_identifier, topic_name, paper_by_doi=True):
        paper_match_prop = "doi" if paper_by_doi else "title"
        query = f"""
        MATCH (p:ResearchPaper {{{paper_match_prop}: $paper_id}})
        MATCH (t:Topic {{name: $topic_name}})
        MERGE (p)-[r:FOCUSES_ON]->(t)
        RETURN type(r)
        """
        return self._run_query(query, {"paper_id": paper_identifier, "topic_name": topic_name})

    def link_paper_to_method(self, paper_identifier, method_name, paper_by_doi=True):
        paper_match_prop = "doi" if paper_by_doi else "title"
        query = f"""
        MATCH (p:ResearchPaper {{{paper_match_prop}: $paper_id}})
        MATCH (m:Method {{name: $method_name}})
        MERGE (p)-[r:EMPLOYS_METHOD]->(m)
        RETURN type(r)
        """
        return self._run_query(query, {"paper_id": paper_identifier, "method_name": method_name})

    def link_author_to_institution(self, author_identifier, institution_name, by_orcid=False):
        author_match_prop = "orcid" if by_orcid else "name"
        query = f"""
        MATCH (a:Author {{{author_match_prop}: $author_id}})
        MATCH (i:Institution {{name: $institution_name}})
        MERGE (a)-[r:AFFILIATED_WITH]->(i)
        RETURN type(r)
        """
        return self._run_query(query, {"author_id": author_identifier, "institution_name": institution_name})

    def link_paper_to_venue(self, paper_identifier, venue_name, paper_by_doi=True):
        paper_match_prop = "doi" if paper_by_doi else "title"
        query = f"""
        MATCH (p:ResearchPaper {{{paper_match_prop}: $paper_id}})
        MATCH (v:Venue {{name: $venue_name}})
        MERGE (p)-[r:PUBLISHED_IN]->(v)
        RETURN type(r)
        """
        return self._run_query(query, {"paper_id": paper_identifier, "venue_name": venue_name})

    def link_papers_citation(self, citing_paper_doi, cited_paper_doi):
        # Assuming papers are identified by DOI for citations
        query = """
        MATCH (citing_p:ResearchPaper {doi: $citing_doi})
        MATCH (cited_p:ResearchPaper {doi: $cited_doi})
        MERGE (citing_p)-[r:CITES]->(cited_p)
        MERGE (cited_p)-[r_inv:REFERENCED_BY]->(citing_p)
        RETURN type(r), type(r_inv)
        """
        return self._run_query(query, {"citing_doi": citing_paper_doi, "cited_doi": cited_paper_doi})

    def link_coauthors(self, author1_identifier, author2_identifier, paper_identifier, author1_by_orcid=False, author2_by_orcid=False, paper_by_doi=True):
        # This relationship is implicitly created if they are authors of the same paper.
        # However, an explicit COAUTHORED_WITH can be useful for direct queries.
        # This function ensures they are linked on a specific paper.
        author1_match_prop = "orcid" if author1_by_orcid else "name"
        author2_match_prop = "orcid" if author2_by_orcid else "name"
        paper_match_prop = "doi" if paper_by_doi else "title"

        query = f"""
        MATCH (a1:Author {{{author1_match_prop}: $author1_id}})
        MATCH (a2:Author {{{author2_match_prop}: $author2_id}})
        MATCH (p:ResearchPaper {{{paper_match_prop}: $paper_id}})
        // Ensure both authors are connected to the paper
        MERGE (a1)<-[:HAS_AUTHOR]-(p)-[:HAS_AUTHOR]->(a2)
        // Create co-author link, could be specific to the paper or general
        MERGE (a1)-[r:COAUTHORED_WITH_ON {{paper_{paper_match_prop}: $paper_id}}]->(a2)
        MERGE (a2)-[r_inv:COAUTHORED_WITH_ON {{paper_{paper_match_prop}: $paper_id}}]->(a1)
        RETURN type(r), type(r_inv)
        """
        return self._run_query(query, {
            "author1_id": author1_identifier,
            "author2_id": author2_identifier,
            "paper_id": paper_identifier
        })

if __name__ == '__main__':
    # Example Usage (requires a running Neo4j instance)
    # Replace with your Neo4j credentials and URI
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "password" # Change this!

    try:
        graph = Neo4jGraph(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

        # Add a research paper
        paper_doi = "10.1000/xyz123"
        paper_title = "The Future of AI in Research"
        graph.add_research_paper(
            title=paper_title,
            abstract="This paper discusses the advancements...",
            publication_date="2023-10-26",
            doi=paper_doi,
            keywords=["AI", "Research", "Machine Learning"],
            venue_name="Journal of Innovative Research"
        )
        print(f"Added paper: {paper_title}")

        # Add authors
        author1_name = "Dr. Alice Smith"
        author1_orcid = "0000-0001-2345-6789"
        graph.add_author(name=author1_name, orcid=author1_orcid, affiliation_name="Tech University")
        print(f"Added author: {author1_name}")

        author2_name = "Dr. Bob Johnson"
        graph.add_author(name=author2_name, affiliation_name="Science Institute")
        print(f"Added author: {author2_name}")

        # Link paper to authors
        graph.link_paper_to_author(paper_identifier=paper_doi, author_identifier=author1_orcid, paper_by_doi=True, author_by_orcid=True)
        graph.link_paper_to_author(paper_identifier=paper_doi, author_identifier=author2_name, paper_by_doi=True, author_by_orcid=False)
        print("Linked paper to authors.")

        # Add topics and link to paper
        for keyword in ["AI", "Research", "Machine Learning"]:
            graph.add_topic(keyword)
            graph.link_paper_to_topic(paper_identifier=paper_doi, topic_name=keyword, paper_by_doi=True)
        print("Added topics and linked to paper.")

        # Add a method and link to paper
        method_name = "Deep Learning Analysis"
        graph.add_method(name=method_name, description="Utilizing CNNs for pattern recognition.")
        graph.link_paper_to_method(paper_identifier=paper_doi, method_name=method_name, paper_by_doi=True)
        print("Added method and linked to paper.")

        # Example of co-author link (on the specific paper)
        graph.link_coauthors(
            author1_identifier=author1_orcid,
            author2_identifier=author2_name,
            paper_identifier=paper_doi,
            author1_by_orcid=True,
            author2_by_orcid=False,
            paper_by_doi=True
        )
        print("Linked co-authors on the paper.")

        # Add another paper for citation example
        cited_paper_doi = "10.1000/abc789"
        cited_paper_title = "Foundations of Neural Networks"
        graph.add_research_paper(title=cited_paper_title, doi=cited_paper_doi, venue_name="Archive of CS")
        print(f"Added paper: {cited_paper_title}")

        # Link papers by citation
        graph.link_papers_citation(citing_paper_doi=paper_doi, cited_paper_doi=cited_paper_doi)
        print(f"Linked {paper_title} (CITES) {cited_paper_title}")


    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'graph' in locals() and graph._driver is not None:
            graph.close()

    # Note: For the 'hasResearchQuestion/addressesResearchQuestion' and 'producedBy/produces' relationships,
    # these would typically require more advanced NLP to extract from text, or explicit input.
    # The current structure allows adding generic nodes/relationships if such data is available.
    # For example, one could add a 'ResearchQuestion' node and link it.
    # def add_research_question(self, question_text, paper_doi_or_title):
    #     self.add_node_with_properties("ResearchQuestion", {"text": question_text})
    #     self.link_paper_to_node(paper_doi_or_title, "ResearchQuestion", question_text, "HAS_RESEARCH_QUESTION", node_prop_to_match="text")

    # def link_paper_to_node(self, paper_identifier, node_label, node_identifier, relationship_type, paper_by_doi=True, node_prop_to_match="name"):
    #     paper_match_prop = "doi" if paper_by_doi else "title"
    #     query = f"""
    #     MATCH (p:ResearchPaper {{{paper_match_prop}: $paper_id}})
    #     MATCH (n:{node_label} {{{node_prop_to_match}: $node_id}})
    #     MERGE (p)-[r:{relationship_type}]->(n)
    #     RETURN type(r)
    #     """
    #     self._run_query(query, {"paper_id": paper_identifier, "node_id": node_identifier})
    # This is a more generic way to handle some of the other relationships if the other node type is simple.
