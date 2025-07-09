# MCP Tool for Research Paper Knowledge Graphs

This tool processes details of research papers and creates a knowledge graph in a Neo4j database based on a defined ontology.

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

## Setup

1.  **Clone the repository (or download the files into a directory `mcp_tool_project`):**
    ```bash
    # If this were a git repo:
    # git clone <repository_url>
    # cd mcp_tool_project
    ```
    For now, ensure you have the `mcp_tool_project` directory with all its Python files.

2.  **Install dependencies:**
    Navigate to the `mcp_tool_project` directory and run:
    ```bash
    pip install -r requirements.txt
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

The main tool is `mcp_tool.py`. It takes research paper details as command-line arguments.

**Basic Example:**

```bash
python mcp_tool.py \
    --title "A Study on Knowledge Graph Construction from Scientific Texts" \
    --doi "10.xxxx/example.doi.123" \
    --abstract "This paper explores methods for automatically building knowledge graphs..." \
    --pubdate "2024-01-15" \
    --authors "Dr. Eva Core <0000-0001-2345-0001>" "Dr. Max Headroom" \
    --keywords "Knowledge Graphs" "NLP" "Science" "Ontology" \
    --venue "Journal of Advanced Scientific Computing" \
    # Optional: --uri "bolt://your_neo4j_host:7687" --user "your_user" --password "your_pass"
```

**Required Arguments:**
*   `--title`: Title of the paper.
*   `--doi`: Digital Object Identifier for the paper.

**Optional Arguments for Paper Details:**
*   `--abstract`: Paper's abstract. (Used by `text_processor.py` in the future).
*   `--pubdate`: Publication date (YYYY-MM-DD).
*   `--authors`: Space-separated list of authors.
    *   Format: `"Full Name"` or `"Full Name <ORCID>"`.
    *   Example: `--authors "Jane Doe <0000-0000-0000-0001>" "John Smith"`
*   `--keywords`: Space-separated list of keywords (these become `Topic` nodes).
*   `--venue`: Name of the journal or conference.

*(More advanced text processing to automatically extract methods, institutions, etc., from the abstract or full text will be integrated via `text_processor.py` in future updates.)*

## Modules

*   **`mcp_tool.py`**: The main command-line interface script.
*   **`neo4j_handler.py`**: Contains the `Neo4jGraph` class for all interactions with the Neo4j database (CRUD operations for nodes and relationships).
*   **`text_processor.py`**: Placeholder for NLP logic to extract entities and relations from paper text (e.g., abstract, full text). Currently contains very basic placeholder logic.
*   **`requirements.txt`**: Lists Python package dependencies.
*   **`README.md`**: This file.

## Future Development
*   Integrate robust NLP capabilities into `text_processor.py` using libraries like spaCy or NLTK for Named Entity Recognition (NER) and Relation Extraction (RE) to identify methods, tools, datasets, research questions, etc., from the paper's text.
*   Support for input from structured files (e.g., JSON, BibTeX).
*   Enhanced CLI options for more complex data input (e.g., author affiliations, citations).
*   Batch processing of multiple papers.
```
