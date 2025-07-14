from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

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