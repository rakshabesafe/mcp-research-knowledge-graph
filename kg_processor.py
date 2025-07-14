from typing import List, Optional, Dict, Any

from neo4j_handler import Neo4jGraph
from text_processor import extract_entities_relations
from kg_models import PaperDetails, ObjectiveInput, HypothesisInput, ConceptInput, ResearchProblemInput, LimitationInput, FutureWorkInput

class KnowledgeGraphProcessor:
    def __init__(self, neo4j_handler: Neo4jGraph):
        self.neo4j_handler = neo4j_handler

    async def process_paper_data(self, paper_data: PaperDetails, ctx: Any) -> Dict[str, Any]:
        neo_handler = self.neo4j_handler
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