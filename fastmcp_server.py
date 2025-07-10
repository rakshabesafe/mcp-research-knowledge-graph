import os
import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field
from fastmcp import FastMCP, Context # Assuming FastMCP and Context are top-level imports

# Assuming these custom modules are in the same directory orPYTHONPATH
from neo4j_handler import Neo4jGraph
from text_processor import extract_entities_relations

# --- Pydantic Models for Tool Input ---
class AuthorDetail(BaseModel):
    name: str = Field(..., description="Full name of the author.")
    orcid: Optional[str] = Field(default=None, description="ORCID identifier for the author.")
    affiliation: Optional[str] = Field(default=None, description="Author's affiliation for this paper.")

class PaperDetails(BaseModel):
    title: str = Field(..., description="Title of the research paper.")
    doi: str = Field(..., description="Digital Object Identifier, used as the primary key.")
    abstract: Optional[str] = Field(default=None, description="Abstract of the paper.")
    publication_date: Optional[str] = Field(default=None, description="Publication date, preferably YYYY-MM-DD.")
    authors: Optional[List[AuthorDetail]] = Field(default_factory=list, description="List of authors with their details.")
    keywords: Optional[List[str]] = Field(default_factory=list, description="List of keywords or topics.")
    venue_name: Optional[str] = Field(default=None, description="Name of the publication venue (journal or conference).")
    full_text: Optional[str] = Field(default=None, description="Full text of the paper, if available.")

# --- Lifespan Management for Neo4j Connection ---
@asynccontextmanager
async def lifespan(app: FastMCP):
    """Manages Neo4j connection lifecycle for the FastMCP application."""
    print("[Lifespan] MCP Server starting up...")
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "your_secure_password") # Placeholder

    neo4j_client_instance = None
    try:
        neo4j_client_instance = Neo4jGraph(uri, user, password)
        # Storing on app.state if that's the convention, or directly on app
        # For now, let's try a custom attribute on app directly, as app.state is not explicitly documented for FastMCP yet
        app.neo4j_handler = neo4j_client_instance
        print("[Lifespan] Neo4j handler initialized and attached to FastMCP instance.")
        yield
    except Exception as e:
        print(f"[Lifespan] Critical error: Failed to initialize Neo4j client during startup: {e}")
        # If Neo4j connection is critical, might re-raise or prevent server from fully starting
        # For now, allow server to start but tools will fail if they need neo4j_handler
        app.neo4j_handler = None # Ensure it's None
        yield # Must yield for lifespan manager protocol
    finally:
        if hasattr(app, 'neo4j_handler') and app.neo4j_handler:
            print("[Lifespan] MCP Server shutting down. Closing Neo4j connection.")
            app.neo4j_handler.close()
        else:
            print("[Lifespan] MCP Server shutting down. No active Neo4j connection to close or was not initialized.")

# --- FastMCP Server Instance ---
# Initialize FastMCP with the lifespan manager and dependencies
# Dependencies are important for `fastmcp install`
mcp_server = FastMCP(
    name="ResearchPaperKGProcessor",
    instructions="A FastMCP server to process research paper details and build a knowledge graph in Neo4j.",
    lifespan=lifespan,
    dependencies=[
        "fastmcp", # The framework itself
        "neo4j>=5.0.0,<6.0.0",
        "spacy>=3.0.0,<4.0.0", # If text_processor uses it
        "pydantic>=2.0.0,<3.0.0" # For data models
    ]
)

# --- Core Tool Definition ---
@mcp_server.tool(
    name="ProcessPaperToKG",
    description="Processes research paper details (metadata, abstract, etc.) and ingests them into a Neo4j knowledge graph."
)
async def process_paper_to_kg(paper_data: PaperDetails, ctx: Context) -> Dict[str, Any]:
    """
    MCP Tool to process a research paper and generate knowledge graph entries.
    """
    await ctx.info(f"Received request to process paper DOI: {paper_data.doi}, Title: {paper_data.title}")

    if not hasattr(ctx.fastmcp, 'neo4j_handler') or ctx.fastmcp.neo4j_handler is None:
        await ctx.error("Neo4j handler not available in FastMCP context. Cannot process paper.")
        return {"status": "error", "doi": paper_data.doi, "message": "Neo4j connection not initialized."}

    neo_handler: Neo4jGraph = ctx.fastmcp.neo4j_handler
    processed_entities = {"nodes_created": 0, "rels_created": 0} # Basic tracking

    try:
        # 1. Add Research Paper node
        # The add_research_paper method in neo4j_handler is synchronous.
        # FastMCP tools can be async, allowing internal sync calls if needed,
        # but ideally, I/O bound operations (like DB calls) should be async if the driver supports it.
        # For now, assuming neo4j_handler methods are blocking.
        # In a fully async setup, neo4j_handler methods would be async too.

        # Synchronous calls within an async tool are generally run in a thread pool by the ASGI server.
        # This is acceptable for now.

        await ctx.report_progress(progress=10, message="Adding research paper node...")
        neo_handler.add_research_paper(
            title=paper_data.title,
            abstract=paper_data.abstract,
            publication_date=paper_data.publication_date,
            doi=paper_data.doi,
            keywords=paper_data.keywords,
            full_text=paper_data.full_text,
            venue_name=paper_data.venue_name
        )
        await ctx.info(f"Added/Merged ResearchPaper: {paper_data.title} ({paper_data.doi})")
        processed_entities["nodes_created"] +=1 # Simplified count

        if paper_data.venue_name:
            await ctx.info(f"Handled Venue: {paper_data.venue_name} and linked to paper.")
            processed_entities["nodes_created"] +=1 # Venue node
            processed_entities["rels_created"] +=1 # Paper-Venue link

        # 2. Add Authors and link to Paper
        if paper_data.authors:
            await ctx.report_progress(progress=30, message="Processing authors...")
            author_ids_for_coauthor_linking = []
            for author_detail in paper_data.authors:
                if not author_detail.name:
                    await ctx.warning("Skipping author with no name.")
                    continue

                neo_handler.add_author(name=author_detail.name, orcid=author_detail.orcid, affiliation_name=author_detail.affiliation)
                await ctx.info(f"Added/Merged Author: {author_detail.name}" + (f" (ORCID: {author_detail.orcid})" if author_detail.orcid else "") + (f" (Affiliation: {author_detail.affiliation})" if author_detail.affiliation else ""))
                processed_entities["nodes_created"] +=1 # Author node
                if author_detail.affiliation:
                    processed_entities["nodes_created"] +=1 # Institution node (if new)
                    processed_entities["rels_created"] +=1 # Author-Institution link

                author_identifier = author_detail.orcid if author_detail.orcid else author_detail.name
                author_ids_for_coauthor_linking.append({"id": author_identifier, "name": author_detail.name, "is_orcid": bool(author_detail.orcid)})

                neo_handler.link_paper_to_author(
                    paper_identifier=paper_data.doi,
                    author_identifier=author_identifier,
                    paper_by_doi=True,
                    author_by_orcid=bool(author_detail.orcid)
                )
                processed_entities["rels_created"] +=2 # HAS_AUTHOR, AUTHORED_BY
                await ctx.info(f"Linked Author '{author_detail.name}' to Paper '{paper_data.title}'")

            if len(author_ids_for_coauthor_linking) > 1:
                for i in range(len(author_ids_for_coauthor_linking)):
                    for j in range(i + 1, len(author_ids_for_coauthor_linking)):
                        auth1 = author_ids_for_coauthor_linking[i]
                        auth2 = author_ids_for_coauthor_linking[j]
                        neo_handler.link_coauthors(
                            author1_identifier=auth1["id"],
                            author2_identifier=auth2["id"],
                            paper_identifier=paper_data.doi,
                            author1_by_orcid=auth1["is_orcid"],
                            author2_by_orcid=auth2["is_orcid"],
                            paper_by_doi=True
                        )
                        processed_entities["rels_created"] +=2 # COAUTHORED_WITH_ON (bidirectional)
                        await ctx.info(f"Linked Co-authors: '{auth1['name']}' and '{auth2['name']}' on paper '{paper_data.doi}'")

        # 3. Add Topics from Keywords
        if paper_data.keywords:
            await ctx.report_progress(progress=60, message="Processing keywords as topics...")
            for keyword in paper_data.keywords:
                neo_handler.add_topic(keyword)
                processed_entities["nodes_created"] +=1 # Topic node (if new)
                await ctx.info(f"Added/Merged Topic (from keyword): {keyword}")
                neo_handler.link_paper_to_topic(
                    paper_identifier=paper_data.doi,
                    topic_name=keyword,
                    paper_by_doi=True
                )
                processed_entities["rels_created"] +=1 # Paper-Topic link
                await ctx.info(f"Linked Topic '{keyword}' to Paper '{paper_data.title}'")

        # 4. Text Processing for additional entities
        text_to_process = paper_data.abstract
        if paper_data.full_text:
            text_to_process = paper_data.full_text

        if text_to_process:
            await ctx.report_progress(progress=75, message="Performing text processing for additional entities...")
            # extract_entities_relations is synchronous
            extracted_nlp_data = extract_entities_relations(text_to_process)

            if extracted_nlp_data:
                if "methods" in extracted_nlp_data.get("entities", {}):
                    for method_info in extracted_nlp_data["entities"]["methods"]:
                        m_name = method_info.get("name")
                        m_desc = method_info.get("description")
                        if m_name:
                            neo_handler.add_method(name=m_name, description=m_desc)
                            processed_entities["nodes_created"] +=1
                            await ctx.info(f"Added/Merged Method (from text): {m_name}")
                            neo_handler.link_paper_to_method(paper_data.doi, m_name)
                            processed_entities["rels_created"] +=1
                            await ctx.info(f"Linked Method '{m_name}' to Paper '{paper_data.title}'")

                if "institutions" in extracted_nlp_data.get("entities", {}):
                    for inst_info in extracted_nlp_data["entities"]["institutions"]:
                        i_name = inst_info.get("name")
                        i_loc = inst_info.get("location")
                        if i_name:
                            neo_handler.add_institution(name=i_name, location=i_loc)
                            processed_entities["nodes_created"] +=1
                            await ctx.info(f"Added/Merged Institution (from text): {i_name}")

                if "topics" in extracted_nlp_data.get("entities", {}):
                    for topic_info in extracted_nlp_data["entities"]["topics"]:
                        t_name = topic_info.get("name")
                        if t_name and not (paper_data.keywords and t_name in paper_data.keywords):
                            neo_handler.add_topic(t_name)
                            processed_entities["nodes_created"] +=1
                            await ctx.info(f"Added/Merged Topic (from text): {t_name}")
                            neo_handler.link_paper_to_topic(paper_data.doi, t_name)
                            processed_entities["rels_created"] +=1
                            await ctx.info(f"Linked Topic '{t_name}' to Paper '{paper_data.title}'")
        else:
            await ctx.info("No abstract or full text provided for NLP extraction.")

        await ctx.report_progress(progress=100, message="Paper processing complete.")
        await ctx.info(f"Successfully processed paper DOI: {paper_data.doi}")
        return {"status": "success", "doi": paper_data.doi, "message": "Paper processed and KG updated.", "summary": processed_entities}

    except Exception as e:
        await ctx.error(f"Error processing paper {paper_data.doi}: {e}", exc_info=True)
        return {"status": "error", "doi": paper_data.doi, "message": str(e)}


# --- Main execution for running the server ---
if __name__ == "__main__":
    print("Starting FastMCP server for Research Paper KG Processor...")
    # mcp_server.run() will use stdio by default.
    # For HTTP, use: mcp_server.run(transport="http", host="0.0.0.0", port=8000)
    # The fastmcp CLI `fastmcp run fastmcp_server.py:mcp_server` is often preferred for more options.

    # For simplicity in direct python execution:
    # Check if NEO4J_PASSWORD is set, if not, maybe don't run or warn.
    if not os.environ.get("NEO4J_PASSWORD"):
        print("WARNING: NEO4J_PASSWORD environment variable not set.")
        print("The server might not connect to Neo4j correctly.")
        print("Please set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD.")

    # FastMCP's mcp.run() is blocking.
    # If run via `python fastmcp_server.py`, it will start here.
    # If run via `fastmcp run fastmcp_server.py:mcp_server`, this block is ignored.
    try:
        mcp_server.run() # Defaults to stdio transport
    except KeyboardInterrupt:
        print("\nFastMCP server shutting down...")
    except Exception as e:
        print(f"FastMCP server failed to start or run: {e}")

```
