# MCP Tool for Research Paper Knowledge Graphs

This tool processes details of research papers and creates a knowledge graph in a Neo4j database based on a defined ontology. It is structured to allow modular components for text processing and graph generation, aligning with a Model Context Project (MCP) concept.

## Ontology Overview

The knowledge graph aims to capture the following core concepts and relationships:

**Core Concepts:**
*   **ResearchPaper:** Title, Abstract, Publication Date, DOI, Keywords, Full Text, Venue.
*   **Author:** Name, Affiliation, OrcID.
*   **Topic:** Name/Keywords, Subtopics.
*   **Institution:** Name, Location.
*   **Method:** Name, Description.
*   **Venue:** Name (e.g., conference, journal).

**Relationships:**
*   `HAS_AUTHOR` (ResearchPaper -> Author) / `AUTHORED_BY` (Author -> ResearchPaper)
*   `PUBLISHED_IN` (ResearchPaper -> Venue)
*   `FOCUSES_ON` (ResearchPaper -> Topic)
*   `EMPLOYS_METHOD` (ResearchPaper -> Method)
*   `AFFILIATED_WITH` (Author -> Institution)
*   `CITES` (ResearchPaper -> ResearchPaper) / `REFERENCED_BY` (ResearchPaper <- ResearchPaper)
*   `COAUTHORED_WITH_ON` (Author -> Author, on a specific paper)
*   *(Future: `HAS_RESEARCH_QUESTION`, `PRODUCES_DATA/MODEL/SOFTWARE`)*

## Prerequisites

*   Python 3.7+
*   Access to a running Neo4j instance (Version 4.x or 5.x recommended).
*   For advanced text processing features: `spaCy` library and a model (e.g., `en_core_web_sm`).

## Setup

1.  **Clone the repository (or ensure all files are in the root project directory):**
    ```bash
    # If this were a git repo:
    # git clone <repository_url>
    # cd <repository_name>
    ```

2.  **Install dependencies:**
    Navigate to the project root directory and run:
    ```bash
    pip install -r requirements.txt
    ```
    If you intend to use the NLP features for entity extraction from text, you also need to download a spaCy model (this is done once):
    ```bash
    python -m spacy download en_core_web_sm
    ```

3.  **Configure Neo4j Connection:**
    The tool can be configured to connect to your Neo4j instance via command-line arguments or environment variables.

    *   **Environment Variables (Recommended for security):**
        *   `NEO4J_URI`: e.g., `bolt://localhost:7687`
        *   `NEO4J_USERNAME`: e.g., `neo4j`
        *   `NEO4J_PASSWORD`: Your Neo4j password
    *   **Command-line Arguments:**
        You can override these by passing `--uri`, `--user`, and `--password` when running the tool.

## Usage

The main command-line interface is `mcp_tool.py`. It takes research paper details as arguments and uses the `KnowledgeGraphGenerator` to process the data.

**Basic Example:**

```bash
python mcp_tool.py \
    --title "A Study on Knowledge Graph Construction from Scientific Texts" \
    --doi "10.xxxx/example.doi.123" \
    --abstract "This paper explores methods for automatically building knowledge graphs. Research at Example University." \
    --pubdate "2024-01-15" \
    --authors "Dr. Eva Core <0000-0001-2345-0001>" "Dr. Max Headroom" \
    --author-affiliations "Example University" "Some Other University" \
    --keywords "Knowledge Graphs" "NLP" "Science" "Ontology" \
    --venue "Journal of Advanced Scientific Computing" \
    # Optional: --uri "bolt://your_neo4j_host:7687" --user "your_user" --password "your_pass"
```

**Required Arguments:**
*   `--title`: Title of the paper.
*   `--doi`: Digital Object Identifier for the paper.

**Optional Arguments for Paper Details:**
*   `--abstract`: Paper's abstract. (Used by `text_processor.py`).
*   `--pubdate`: Publication date (YYYY-MM-DD).
*   `--authors`: Space-separated list of authors.
    *   Format: `"Full Name"` or `"Full Name <ORCID>"`.
*   `--author-affiliations`: Space-separated list of affiliations, one per author in the order authors are listed. Use "None" or an empty string for authors without a listed affiliation.
*   `--keywords`: Space-separated list of keywords (these become `Topic` nodes).
*   `--venue`: Name of the journal or conference.
*   `--fulltext`: Path to a file containing the full text of the paper (optional, for more detailed processing by `text_processor.py`).

## Project Structure & Modules

*   **`mcp_tool.py`**: The main command-line interface (CLI) script. It parses arguments and passes them to the `KnowledgeGraphGenerator`.
*   **`knowledge_graph_generator.py`**: Contains the `KnowledgeGraphGenerator` class, which encapsulates the core logic for processing paper data and building the knowledge graph. It utilizes `neo4j_handler.py` for database interactions and `text_processor.py` for NLP tasks. This module is designed to be potentially usable as a library component.
*   **`neo4j_handler.py`**: Contains the `Neo4jGraph` class for all interactions with the Neo4j database (CRUD operations for nodes and relationships based on the defined ontology).
*   **`text_processor.py`**: Handles Natural Language Processing (NLP) tasks. It aims to extract entities (like methods, institutions, additional topics) and potentially relations from the paper's text (abstract or full text). Currently uses `spaCy` for basic NER if available, with fallbacks. This module is designed to be replaceable with other NLP tools or frameworks (e.g., a future FastMCP component).
*   **`requirements.txt`**: Lists Python package dependencies.
*   **`README.md`**: This file.

This structure promotes modularity:
*   The CLI is separate from the core graph generation logic.
*   The NLP component is separate and can be evolved or replaced.
*   The Neo4j interaction layer is also distinct.

## Future Development
*   **Advanced NLP Integration:** Enhance `text_processor.py` with more sophisticated NLP models (e.g., SciSpaCy, transformer-based models) for better entity recognition (methods, tools, datasets, research questions) and relation extraction from scientific text.
*   **FastMCP Integration:** If FastMCP or a similar framework becomes available, `text_processor.py` could be adapted or replaced to integrate with it.
*   **Input from Structured Files:** Support for input from formats like JSON, BibTeX, or XML (e.g., JATS).
*   **Batch Processing:** Allow processing of multiple papers from a directory or a manifest file.
*   **Enhanced Relation Extraction:** Move beyond entity spotting to more robustly extract relationships defined in the ontology directly from text.
*   **Configuration File:** Support for managing settings (e.g., Neo4j credentials, NLP model choices) via a configuration file.
```
