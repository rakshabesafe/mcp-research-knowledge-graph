import os
import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field
from fastmcp import FastMCP, Context

from neo4j_handler import Neo4jGraph
from text_processor import extract_entities_relations

# --- Pydantic Models for Tool Input (Aligned with new ontology) ---
class AuthorInput(BaseModel):
    name: str = Field(..., description="Full name of the author.")
    orcid: Optional[str] = Field(default=None, description="ORCID identifier for the author.")
    email: Optional[str] = Field(default=None, description="Author's contact email.")
    affiliation_name: Optional[str] = Field(default=None, description="Name of the author's affiliation for this paper.")
    affiliation_location: Optional[str] = Field(default=None, description="Location of the author's affiliation.")

class PublicationVenueDetail(BaseModel):
    name: str = Field(..., description="Name of the journal or conference.")
    issn_isbn: Optional[str] = Field(default=None, description="ISSN or ISBN of the venue.")
    publisher: Optional[str] = Field(default=None, description="Publisher of the venue.")

class DatasetDetail(BaseModel):
    name: str = Field(..., description="Name of the dataset.")
    description: Optional[str] = Field(default=None, description="Brief description of the dataset.")
    url: Optional[str] = Field(default=None, description="URL or access point for the dataset.")

class FunderDetail(BaseModel):
    name: str = Field(..., description="Name of the funding organization or agency.")

class PaperDetails(BaseModel):
    title: str = Field(..., description="Title of the research paper.")
    doi: str = Field(..., description="Digital Object Identifier, used as the primary key.")
    abstract: Optional[str] = Field(default=None, description="Abstract of the paper.")
    publication_date: Optional[str] = Field(default=None, description="Publication date, preferably YYYY-MM-DD.")
    authors: Optional[List[AuthorInput]] = Field(default_factory=list, description="List of authors with their details.")
    keywords: Optional[List[str]] = Field(default_factory=list, description="List of keywords or research topics.")
    full_text_link: Optional[str] = Field(default=None, description="URL to the full text of the paper.")
    publication_venue: Optional[PublicationVenueDetail] = Field(default=None, description="Details of the publication venue.")
    datasets: Optional[List[DatasetDetail]] = Field(default_factory=list, description="List of datasets used or produced.")
    funders: Optional[List[FunderDetail]] = Field(default_factory=list, description="List of funding organizations.")

# --- Lifespan Management for Neo4j Connection ---
@asynccontextmanager
async def lifespan(app: FastMCP):
    """Manages Neo4j connection lifecycle for the FastMCP application."""
    print("[Lifespan] MCP Server starting up...")
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "your_secure_password")

    neo4j_client_instance = None
    try:
        neo4j_client_instance = Neo4jGraph(uri, user, password)
        app.neo4j_handler_instance = neo4j_client_instance
        print("[Lifespan] Neo4j handler initialized and attached to FastMCP app instance.")
        yield
    except Exception as e:
        print(f"[Lifespan] Critical error: Failed to initialize Neo4j client during startup: {e}")
        app.neo4j_handler_instance = None
        yield
    finally:
        if hasattr(app, 'neo4j_handler_instance') and app.neo4j_handler_instance:
            print("[Lifespan] MCP Server shutting down. Closing Neo4j connection.")
            app.neo4j_handler_instance.close()
        else:
            print("[Lifespan] MCP Server shutting down. No active Neo4j connection to close or was not initialized.")

# --- FastMCP Server Instance ---
mcp_server = FastMCP(
    name="ResearchPaperKGProcessor",
    instructions="A FastMCP server to process research paper details and build a knowledge graph in Neo4j based on the new ontology.",
    lifespan=lifespan,
    dependencies=[
        "fastmcp",
        "neo4j>=5.0.0,<6.0.0",
        "spacy>=3.0.0,<4.0.0",
        "pydantic>=2.0.0,<3.0.0"
    ]
)

# --- Core Tool Definition ---
@mcp_server.tool(
    name="ProcessPaperToKG",
    description="Processes research paper details and ingests them into a Neo4j knowledge graph according to the defined ontology."
)
async def process_paper_to_kg(paper_data: PaperDetails, ctx: Context) -> Dict[str, Any]:
    """
    MCP Tool to process a research paper and generate knowledge graph entries
    based on the new ontology.
    """
    await ctx.info(f"Received request to process paper DOI: {paper_data.doi}, Title: {paper_data.title}")

    if not hasattr(ctx.fastmcp, 'neo4j_handler_instance') or ctx.fastmcp.neo4j_handler_instance is None:
        await ctx.error("Neo4j handler not available. Cannot process paper.")
        return {"status": "error", "doi": paper_data.doi, "message": "Neo4j connection not initialized."}

    neo_handler: Neo4jGraph = ctx.fastmcp.neo4j_handler_instance
    summary = {"status": "success", "doi": paper_data.doi, "message": "Paper processing initiated."}

    try:
        await ctx.report_progress(progress=5, message="Adding Paper node...")
        neo_handler.add_research_paper(
            doi=paper_data.doi,
            title=paper_data.title,
            abstract=paper_data.abstract,
            publication_date=paper_data.publication_date,
            keywords=paper_data.keywords,
            full_text_link=paper_data.full_text_link,
            venue_name=paper_data.publication_venue.name if paper_data.publication_venue else None,
            venue_issn_isbn=paper_data.publication_venue.issn_isbn if paper_data.publication_venue else None,
            venue_publisher=paper_data.publication_venue.publisher if paper_data.publication_venue else None
        )
        await ctx.info(f"Handled Paper: {paper_data.title} ({paper_data.doi})")
        if paper_data.publication_venue and paper_data.publication_venue.name:
             await ctx.info(f"Handled PublicationVenue: {paper_data.publication_venue.name}")

        if paper_data.authors:
            await ctx.report_progress(progress=20, message="Processing Authors...")
            author_ids_for_coauthor_linking = []
            for author_input in paper_data.authors:
                neo_handler.add_author(
                    name=author_input.name,
                    orcid=author_input.orcid,
                    email=author_input.email,
                    affiliation_name=author_input.affiliation_name,
                    affiliation_location=author_input.affiliation_location # Pass location for Affiliation node
                )
                await ctx.info(f"Handled Author: {author_input.name}")

                author_identifier = author_input.orcid if author_input.orcid else author_input.name
                author_ids_for_coauthor_linking.append({"id": author_identifier, "name": author_input.name, "is_orcid": bool(author_input.orcid)})
                neo_handler.link_paper_to_author(paper_data.doi, author_identifier, by_orcid=bool(author_input.orcid))
                await ctx.info(f"Linked Author '{author_input.name}' to Paper '{paper_data.title}'")

            if len(author_ids_for_coauthor_linking) > 1:
                for i in range(len(author_ids_for_coauthor_linking)):
                    for j in range(i + 1, len(author_ids_for_coauthor_linking)):
                        auth1 = author_ids_for_coauthor_linking[i]
                        auth2 = author_ids_for_coauthor_linking[j]
                        neo_handler.link_coauthors(
                            auth1["id"], auth2["id"], paper_data.doi,
                            author1_by_orcid=auth1["is_orcid"], author2_by_orcid=auth2["is_orcid"]
                        )
                        await ctx.info(f"Linked Co-authors: {auth1['name']} and {auth2['name']}")

        if paper_data.keywords: # These are for ResearchTopic
            await ctx.report_progress(progress=40, message="Processing ResearchTopics...")
            for keyword in paper_data.keywords:
                neo_handler.add_research_topic(keyword)
                await ctx.info(f"Handled ResearchTopic: {keyword}")
                neo_handler.link_paper_to_research_topic(paper_data.doi, keyword)
                await ctx.info(f"Linked ResearchTopic '{keyword}' to Paper")

        if paper_data.datasets:
            await ctx.report_progress(progress=50, message="Processing Datasets...")
            for ds_detail in paper_data.datasets:
                neo_handler.add_dataset(name=ds_detail.name, description=ds_detail.description, url=ds_detail.url)
                await ctx.info(f"Handled Dataset: {ds_detail.name}")
                neo_handler.link_paper_to_dataset(paper_data.doi, ds_detail.name)
                await ctx.info(f"Linked Dataset '{ds_detail.name}' to Paper")

        if paper_data.funders:
            await ctx.report_progress(progress=60, message="Processing Funders...")
            for funder_detail in paper_data.funders:
                neo_handler.add_funder(name=funder_detail.name)
                await ctx.info(f"Handled Funder: {funder_detail.name}")
                neo_handler.link_paper_to_funder(paper_data.doi, funder_detail.name)
                await ctx.info(f"Linked Funder '{funder_detail.name}' to Paper")

        text_content_for_nlp = paper_data.abstract
        # Future: could fetch content if paper_data.full_text_link is present and text_content_for_nlp is empty

        if text_content_for_nlp:
            await ctx.report_progress(progress=70, message="Performing NLP text processing...")
            extracted_nlp_data = extract_entities_relations(text_content_for_nlp) # Sync call
            if extracted_nlp_data:
                await ctx.info("Processing entities extracted from text by NLP...")
                # Methods from NLP
                if "methods" in extracted_nlp_data.get("entities", {}):
                    for method_info in extracted_nlp_data.get("entities", {}).get("methods", []):
                        m_name = method_info.get("name")
                        if m_name:
                            neo_handler.add_method(name=m_name, description=method_info.get("description"))
                            neo_handler.link_paper_to_method(paper_data.doi, m_name)
                            await ctx.info(f"Handled Method (from text): {m_name}")
                # Affiliations from NLP (text_processor identifies these as 'institutions')
                if "institutions" in extracted_nlp_data.get("entities", {}):
                    for aff_info in extracted_nlp_data.get("entities", {}).get("institutions",[]):
                        aff_name = aff_info.get("name")
                        if aff_name:
                            # Assuming location might also be extracted by NLP in future
                            neo_handler.add_affiliation(name=aff_name, location=aff_info.get("location"))
                            await ctx.info(f"Handled Affiliation (from text): {aff_name}")
                # ResearchTopics from NLP (text_processor identifies these as 'topics')
                if "topics" in extracted_nlp_data.get("entities", {}):
                    for topic_info in extracted_nlp_data.get("entities", {}).get("topics",[]):
                        rt_name = topic_info.get("name")
                        if rt_name and not (paper_data.keywords and rt_name in paper_data.keywords):
                            neo_handler.add_research_topic(rt_name)
                            neo_handler.link_paper_to_research_topic(paper_data.doi, rt_name)
                            await ctx.info(f"Handled ResearchTopic (from text): {rt_name}")
            else:
                await ctx.info("NLP text processor returned no structured entities.")
        else:
            await ctx.info("No text content (abstract/full_text_link content) for NLP.")

        await ctx.report_progress(progress=100, message="Paper processing complete.")
        summary["message"] = "Paper processed and KG updated successfully."
        await ctx.info(f"Successfully finished processing tasks for paper DOI: {paper_data.doi}")
        return summary
    except Exception as e:
        await ctx.error(f"Major error processing paper {paper_data.doi}: {e}", exc_info=True)
        return {"status": "error", "doi": paper_data.doi, "message": f"An unexpected error occurred: {str(e)}"}

# --- Main execution for running the server ---
if __name__ == "__main__":
    print("Starting FastMCP server for Research Paper KG Processor...")
    if not os.environ.get("NEO4J_PASSWORD"):
        print("WARNING: NEO4J_PASSWORD environment variable not set.")
        print("The server might not connect to Neo4j correctly.")
        print("Please set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD.")
    try:
        mcp_server.run()
    except KeyboardInterrupt:
        print("\nFastMCP server shutting down...")
    except Exception as e:
        print(f"FastMCP server failed to start or run: {e}")

```
