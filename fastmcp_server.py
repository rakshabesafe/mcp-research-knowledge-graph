import os
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastmcp import FastMCP, Context

from kg_models import PaperDetails
from kg_processor import KnowledgeGraphProcessor
from neo4j_handler import Neo4jGraph


# --- Lifespan Management for Neo4j Connection ---
@asynccontextmanager
async def lifespan(app: FastMCP):
    print("[Lifespan] MCP Server starting up...")
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "your_secure_password")

    neo4j_client_instance = None
    kg_processor_instance = None
    try:
        neo4j_client_instance = Neo4jGraph(uri, user, password)
        kg_processor_instance = KnowledgeGraphProcessor(neo4j_client_instance)
        app.kg_processor_instance = kg_processor_instance
        print("[Lifespan] Neo4j handler and KG Processor initialized and attached to FastMCP app instance.")
        yield
    except Exception as e:
        print(f"[Lifespan] Critical error: Failed to initialize Neo4j client or KG Processor during startup: {e}")
        app.kg_processor_instance = None
        yield
    finally:
        if hasattr(app, 'kg_processor_instance') and app.kg_processor_instance and hasattr(app.kg_processor_instance, 'neo4j_handler') and app.kg_processor_instance.neo4j_handler:
            print("[Lifespan] MCP Server shutting down. Closing Neo4j connection.")
            app.kg_processor_instance.neo4j_handler.close()
        else:
            print("[Lifespan] MCP Server shutting down. No active Neo4j connection to close or was not initialized.")

# --- FastMCP Server Instance ---
mcp_server = FastMCP(
    name="ResearchPaperKGProcessorV2",
    instructions="Processes research paper details (including objectives, hypotheses, concepts, gaps) to build a Neo4j knowledge graph.",
    lifespan=lifespan,
    dependencies=["fastmcp", "neo4j>=5.0.0,<6.0.0", "spacy>=3.0.0,<4.0.0", "pydantic>=2.0.0,<3.0.0"]
)

# --- Core Tool Definition ---
@mcp_server.tool(
    name="ProcessPaperToKG_V2",
    description="Processes detailed research paper data, including semantic elements, into a Neo4j knowledge graph."
)
async def process_paper_to_kg_v2(paper_data: PaperDetails, ctx: Context) -> Dict[str, Any]:
    await ctx.info(f"V2: Received request for DOI: {paper_data.doi}, Title: {paper_data.title}")

    if not hasattr(ctx.fastmcp, 'kg_processor_instance') or ctx.fastmcp.kg_processor_instance is None:
        await ctx.error("V2: Knowledge Graph Processor unavailable.")
        return {"status": "error", "doi": paper_data.doi, "message": "Knowledge Graph Processor not initialized."}

    kg_processor: KnowledgeGraphProcessor = ctx.fastmcp.kg_processor_instance
    return await kg_processor.process_paper_data(paper_data, ctx)

# --- Main execution ---
if __name__ == "__main__":
    print("Starting FastMCP server (V2 Ontology) for Research Paper KG Processor...")
    if not os.environ.get("NEO4J_PASSWORD"):
        print("WARNING: NEO4J_PASSWORD environment variable not set.")
    try:
        mcp_server.run()
    except KeyboardInterrupt:
        print("\nFastMCP server (V2 Ontology) shutting down...")
    except Exception as e:
        print(f"FastMCP server (V2 Ontology) failed to start or run: {e}")