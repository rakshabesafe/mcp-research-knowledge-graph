import os
import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field
from fastmcp import FastMCP, Context

from neo4j_handler import Neo4jGraph
from text_processor import extract_entities_relations

# --- Pydantic Models for new Ontology Elements ---
class ObjectiveInput(BaseModel):
    description: str = Field(..., description="Description of the research objective.")

class HypothesisInput(BaseModel):
    description: str = Field(..., description="Description of the hypothesis.")
    # Optional: Link to method names if provided directly in input
    tested_by_methods: Optional[List[str]] = Field(default_factory=list, description="Names of methods testing this hypothesis.")

class ConceptInput(BaseModel):
    name: str = Field(..., description="Name of the concept (e.g., 'BERT', 'Knowledge Graph').")
    definition: Optional[str] = Field(default=None, description="A short definition or description of the concept.")
    first_mentioned_in_paper_doi: Optional[str] = Field(default=None, description="DOI of the seminal paper that first introduced this concept.")
    # For hierarchical linking, if provided directly with paper input
    is_sub_concept_of: Optional[List[str]] = Field(default_factory=list, description="Names of parent concepts.")
    is_prerequisite_for: Optional[List[str]] = Field(default_factory=list, description="Names of concepts it's a prerequisite for.")
    is_related_to: Optional[List[str]] = Field(default_factory=list, description="Names of related concepts.")
    part_of_topics: Optional[List[str]] = Field(default_factory=list, description="Names of research topics this concept is part of.")


class ResearchProblemInput(BaseModel):
    description: str = Field(..., description="Statement of the research problem.")

class LimitationInput(BaseModel):
    description: str = Field(..., description="Description of a limitation of the research.")

class FutureWorkInput(BaseModel):
    description: str = Field(..., description="Description of a future work suggestion.")

# --- Main Pydantic Model for Tool Input (Aligned with new ontology) ---
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
    keywords: Optional[List[str]] = Field(default_factory=list, description="List of keywords (main research topics).")
    full_text_link: Optional[str] = Field(default=None, description="URL to the full text of the paper.")
    publication_venue: Optional[PublicationVenueDetail] = Field(default=None, description="Details of the publication venue.")
    datasets: Optional[List[DatasetDetail]] = Field(default_factory=list, description="List of datasets used or produced.")
    funders: Optional[List[FunderDetail]] = Field(default_factory=list, description="List of funding organizations.")

    objectives: Optional[List[ObjectiveInput]] = Field(default_factory=list, description="List of research objectives.")
    # Hypotheses now includes a list of method names that test it
    hypotheses: Optional[List[HypothesisInput]] = Field(default_factory=list, description="List of hypotheses tested, potentially linked to methods.")

    # Concepts introduced by or significantly detailed by THIS paper
    introduced_concepts: Optional[List[ConceptInput]] = Field(default_factory=list, description="Key concepts introduced or significantly detailed by this paper.")

    research_problems_addressed: Optional[List[ResearchProblemInput]] = Field(default_factory=list, description="Research problems the paper addresses.")
    limitations_stated: Optional[List[LimitationInput]] = Field(default_factory=list, description="Limitations of the work stated in the paper.")
    future_work_suggested: Optional[List[FutureWorkInput]] = Field(default_factory=list, description="Future work suggested by the paper.")

# --- Lifespan Management for Neo4j Connection ---
@asynccontextmanager
async def lifespan(app: FastMCP):
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

    if not hasattr(ctx.fastmcp, 'neo4j_handler_instance') or ctx.fastmcp.neo4j_handler_instance is None:
        await ctx.error("V2: Neo4j handler unavailable.")
        return {"status": "error", "doi": paper_data.doi, "message": "Neo4j connection not initialized."}

    neo_handler: Neo4jGraph = ctx.fastmcp.neo4j_handler_instance
    summary = {"status": "success", "doi": paper_data.doi, "message": "V2: Paper processing initiated."}

    try:
        # --- Basic Paper Info ---
        await ctx.report_progress(progress=5, message="Handling Paper and PublicationVenue...")
        neo_handler.add_research_paper(
            doi=paper_data.doi, title=paper_data.title, abstract=paper_data.abstract,
            publication_date=paper_data.publication_date, keywords=paper_data.keywords,
            full_text_link=paper_data.full_text_link,
            venue_name=paper_data.publication_venue.name if paper_data.publication_venue else None,
            venue_issn_isbn=paper_data.publication_venue.issn_isbn if paper_data.publication_venue else None,
            venue_publisher=paper_data.publication_venue.publisher if paper_data.publication_venue else None
        )
        await ctx.info(f"V2: Handled Paper: {paper_data.title}")

        # --- Authors & Affiliations ---
        if paper_data.authors:
            await ctx.report_progress(progress=10, message="Handling Authors...")
            # Co-author linking part remains similar
            author_ids_for_coauthor_linking = []
            for author_input in paper_data.authors:
                neo_handler.add_author(
                    name=author_input.name, orcid=author_input.orcid, email=author_input.email,
                    affiliation_name=author_input.affiliation_name,
                    affiliation_location=author_input.affiliation_location
                )
                author_identifier = author_input.orcid if author_input.orcid else author_input.name
                author_ids_for_coauthor_linking.append({"id": author_identifier, "name": author_input.name, "is_orcid": bool(author_input.orcid)})
                neo_handler.link_paper_to_author(paper_data.doi, author_identifier, by_orcid=bool(author_input.orcid))
            await ctx.info(f"V2: Handled {len(paper_data.authors)} authors.")
            if len(author_ids_for_coauthor_linking) > 1:
                for i in range(len(author_ids_for_coauthor_linking)):
                    for j in range(i + 1, len(author_ids_for_coauthor_linking)):
                        auth1, auth2 = author_ids_for_coauthor_linking[i], author_ids_for_coauthor_linking[j]
                        neo_handler.link_coauthors(auth1["id"], auth2["id"], paper_data.doi, auth1["is_orcid"], auth2["is_orcid"])
                await ctx.info("V2: Handled co-author links.")


        # --- Keywords (ResearchTopics) ---
        if paper_data.keywords:
            await ctx.report_progress(progress=20, message="Handling ResearchTopics from keywords...")
            for keyword in paper_data.keywords:
                neo_handler.add_research_topic(keyword)
                neo_handler.link_paper_to_research_topic(paper_data.doi, keyword)
            await ctx.info(f"V2: Handled {len(paper_data.keywords)} ResearchTopics from keywords.")

        # --- Datasets & Funders ---
        if paper_data.datasets:
            await ctx.report_progress(progress=25, message="Handling Datasets...")
            for ds in paper_data.datasets:
                neo_handler.add_dataset(name=ds.name, description=ds.description, url=ds.url)
                neo_handler.link_paper_to_dataset(paper_data.doi, ds.name)
            await ctx.info(f"V2: Handled {len(paper_data.datasets)} Datasets.")
        if paper_data.funders:
            await ctx.report_progress(progress=30, message="Handling Funders...")
            for funder in paper_data.funders:
                neo_handler.add_funder(name=funder.name)
                neo_handler.link_paper_to_funder(paper_data.doi, funder.name)
            await ctx.info(f"V2: Handled {len(paper_data.funders)} Funders.")

        # --- Objectives ---
        if paper_data.objectives:
            await ctx.report_progress(progress=35, message="Handling Objectives...")
            for obj_input in paper_data.objectives:
                neo_handler.add_objective(description=obj_input.description)
                neo_handler.link_paper_to_objective(paper_data.doi, obj_input.description)
            await ctx.info(f"V2: Handled {len(paper_data.objectives)} Objectives.")

        # --- Hypotheses (and links to Objectives/Methods if provided) ---
        if paper_data.hypotheses:
            await ctx.report_progress(progress=40, message="Handling Hypotheses...")
            for hyp_input in paper_data.hypotheses:
                neo_handler.add_hypothesis(description=hyp_input.description)
                neo_handler.link_paper_to_hypothesis(paper_data.doi, hyp_input.description)
                # Link to objectives if this paper's objectives list is also processed
                if paper_data.objectives: # Simple: link to all objectives of this paper for now
                    for obj_input in paper_data.objectives:
                        neo_handler.link_objective_to_hypothesis(obj_input.description, hyp_input.description)
                # Link to methods if specified in input
                if hyp_input.tested_by_methods:
                    for method_name in hyp_input.tested_by_methods:
                        # Ensure method node exists (could be from NLP or prior input)
                        neo_handler.add_method(name=method_name) # Idempotent
                        neo_handler.link_hypothesis_to_method(hyp_input.description, method_name)
            await ctx.info(f"V2: Handled {len(paper_data.hypotheses)} Hypotheses.")

        # --- Introduced Concepts (and links to topics/other concepts if provided) ---
        if paper_data.introduced_concepts:
            await ctx.report_progress(progress=50, message="Handling Introduced Concepts...")
            for concept_input in paper_data.introduced_concepts:
                neo_handler.add_concept(name=concept_input.name, definition=concept_input.definition, first_mentioned_doi=concept_input.first_mentioned_in_paper_doi)
                neo_handler.link_paper_to_concept(paper_data.doi, concept_input.name, relationship_type="INTRODUCES_CONCEPT")
                if concept_input.part_of_topics:
                    for topic_name in concept_input.part_of_topics:
                        neo_handler.add_research_topic(topic_name) # Ensure topic exists
                        neo_handler.link_concept_to_research_topic(concept_input.name, topic_name)
                # Handle other conceptual links if provided
                if concept_input.is_sub_concept_of:
                    for parent_concept_name in concept_input.is_sub_concept_of:
                        neo_handler.add_concept(name=parent_concept_name) # Ensure parent exists
                        neo_handler.link_concept_to_concept(concept_input.name, parent_concept_name, "IS_SUB_CONCEPT_OF")
                if concept_input.is_prerequisite_for:
                     for child_concept_name in concept_input.is_prerequisite_for:
                        neo_handler.add_concept(name=child_concept_name)
                        neo_handler.link_concept_to_concept(concept_input.name, child_concept_name, "IS_PREREQUISITE_FOR")
                if concept_input.is_related_to:
                    for related_concept_name in concept_input.is_related_to:
                        neo_handler.add_concept(name=related_concept_name)
                        neo_handler.link_concept_to_concept(concept_input.name, related_concept_name, "IS_RELATED_TO")
            await ctx.info(f"V2: Handled {len(paper_data.introduced_concepts)} Introduced Concepts.")

        # --- Research Problems Addressed ---
        if paper_data.research_problems_addressed:
            await ctx.report_progress(progress=60, message="Handling Research Problems...")
            for rp_input in paper_data.research_problems_addressed:
                neo_handler.add_research_problem(description=rp_input.description)
                neo_handler.link_paper_to_research_problem(paper_data.doi, rp_input.description)
            await ctx.info(f"V2: Handled {len(paper_data.research_problems_addressed)} Research Problems.")

        # --- Limitations Stated ---
        if paper_data.limitations_stated:
            await ctx.report_progress(progress=65, message="Handling Limitations...")
            for lim_input in paper_data.limitations_stated:
                neo_handler.add_limitation(description=lim_input.description)
                neo_handler.link_paper_to_limitation(paper_data.doi, lim_input.description)
            await ctx.info(f"V2: Handled {len(paper_data.limitations_stated)} Limitations.")

        # --- Future Work Suggested ---
        if paper_data.future_work_suggested:
            await ctx.report_progress(progress=70, message="Handling Future Work...")
            for fw_input in paper_data.future_work_suggested:
                neo_handler.add_future_work(description=fw_input.description)
                neo_handler.link_paper_to_future_work(paper_data.doi, fw_input.description)
            await ctx.info(f"V2: Handled {len(paper_data.future_work_suggested)} Future Work suggestions.")

        # --- NLP Text Processing (for Methods, Affiliations, ResearchTopics from text) ---
        text_content_for_nlp = paper_data.abstract
        if text_content_for_nlp:
            await ctx.report_progress(progress=80, message="Performing NLP text processing...")
            extracted_nlp_data = extract_entities_relations(text_content_for_nlp)
            if extracted_nlp_data:
                await ctx.info("V2: Processing entities extracted by NLP...")
                # Methods
                for method_info in extracted_nlp_data.get("entities", {}).get("methods", []):
                    m_name = method_info.get("name")
                    if m_name:
                        neo_handler.add_method(name=m_name, description=method_info.get("description"))
                        neo_handler.link_paper_to_method(paper_data.doi, m_name)
                # Affiliations (from 'institutions' key)
                for aff_info in extracted_nlp_data.get("entities", {}).get("institutions",[]):
                    aff_name = aff_info.get("name")
                    if aff_name:
                        neo_handler.add_affiliation(name=aff_name, location=aff_info.get("location"))
                # ResearchTopics (from 'topics' key)
                for topic_info in extracted_nlp_data.get("entities", {}).get("topics",[]):
                    rt_name = topic_info.get("name")
                    if rt_name and not (paper_data.keywords and rt_name in paper_data.keywords):
                        neo_handler.add_research_topic(rt_name)
                        neo_handler.link_paper_to_research_topic(paper_data.doi, rt_name)
                await ctx.info("V2: Finished processing NLP entities.")
            else:
                await ctx.info("V2: NLP text processor returned no structured entities.")
        else:
            await ctx.info("V2: No text content for NLP.")

        await ctx.report_progress(progress=100, message="Paper processing complete.")
        summary["message"] = "V2: Paper and its semantic elements processed successfully."
        await ctx.info(f"V2: Successfully finished processing tasks for DOI: {paper_data.doi}")
        return summary
    except Exception as e:
        await ctx.error(f"V2: Major error processing paper {paper_data.doi}: {e}", exc_info=True)
        return {"status": "error", "doi": paper_data.doi, "message": f"An unexpected error occurred: {str(e)}"}

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
