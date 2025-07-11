# Research Paper Knowledge Graph Processor (FastMCP Edition)

This project provides a FastMCP (Model Context Protocol) server with a tool to process research paper details and create/update a knowledge graph in a Neo4j database.

## Overview

The core of this project is a FastMCP server that exposes a tool named `ProcessPaperToKG`. This tool accepts structured data about a research paper (title, DOI, authors, abstract, etc.), processes it (including NLP on the abstract/text via spaCy if available), and then populates a Neo4j graph database according to a defined ontology.

## Ontology

The knowledge graph is built according to the following ontology:

**Core Entities (Node Labels) & Their Properties:**

*   **`Paper`**: A research publication.
    *   `doi` (string, Unique ID): Digital Object Identifier.
    *   `title` (string): Title of the paper.
    *   `abstract` (string, optional): Summary of the paper.
    *   `publication_date` (string, optional): e.g., "YYYY-MM-DD".
    *   `keywords` (list of strings, optional): Keywords assigned to the paper (these become `ResearchTopic` nodes).
    *   `full_text_link` (string, optional): URL to the full text.
*   **`Author`**: An individual contributor.
    *   `name` (string): Full name. (Primary key if ORCID is absent).
    *   `orcid` (string, optional, Unique ID if present): Open Researcher and Contributor ID.
    *   `email` (string, optional): Contact email.
*   **`Affiliation`**: An institution/organization an author is associated with.
    *   `name` (string, Unique ID): Name of the affiliation.
    *   `location` (string, optional): Geographical location.
*   **`PublicationVenue`**: Where the paper is published.
    *   `name` (string, Unique ID): Name of the journal or conference.
    *   `issn_isbn` (string, optional): ISSN or ISBN.
    *   `publisher` (string, optional): Publishing house.
*   **`ResearchTopic`**: A high-level subject area or keyword. (Initially populated from `Paper.keywords`).
    *   `name` (string, Unique ID): Name of the topic.
*   **`Method`**: A specific technique or methodology.
    *   `name` (string, Unique ID): Name of the method.
    *   `description` (string, optional): Brief description.
*   **`Dataset`**: Data used or produced by research.
    *   `name` (string, Unique ID): Name of the dataset.
    *   `description` (string, optional): Description.
    *   `url` (string, optional): Link to the dataset.
*   **`Funder`**: Organization funding the research.
    *   `name` (string, Unique ID): Name of the funder.
*   **`Objective`**: A research goal of a paper.
    *   `description` (string, Unique ID): Text describing the objective.
*   **`Hypothesis`**: A specific hypothesis tested in a paper.
    *   `description` (string, Unique ID): Text describing the hypothesis.
*   **`Concept`**: A granular unit of knowledge (e.g., algorithm, principle).
    *   `name` (string, Unique ID): Name of the concept.
    *   `definition` (string, optional): Short description.
    *   `first_mentioned_doi` (string, optional): DOI of the seminal paper introducing this concept.
*   **`ResearchProblem`**: A problem/question the paper aims to solve.
    *   `description` (string, Unique ID): Statement of the problem.
*   **`Limitation`**: A stated limitation of the research work.
    *   `description` (string, Unique ID): Description of the limitation.
*   **`FutureWork`**: A suggestion for future research.
    *   `description` (string, Unique ID): Description of the future work.

**Relationships (Edge Types):**

*   Paper-Centric Relationships:
    *   `Paper` -[:HAS_AUTHOR]-> `Author` (Inverse: `Author` -[:AUTHORED_BY]-> `Paper`)
    *   `Paper` -[:PUBLISHED_IN]-> `PublicationVenue`
    *   `Paper` -[:HAS_TOPIC]-> `ResearchTopic` (Connects paper to its main keywords/topics)
    *   `Paper` -[:USES_METHOD]-> `Method`
    *   `Paper` -[:USES_DATASET]-> `Dataset`
    *   `Paper` -[:IS_FUNDED_BY]-> `Funder`
    *   `Paper` -[:CITES]-> `Paper` (Inverse: `Paper` -[:REFERENCED_BY]-> `Paper`)
    *   `Paper` -[:HAS_OBJECTIVE]-> `Objective`
    *   `Paper` -[:HAS_HYPOTHESIS]-> `Hypothesis`
    *   `Paper` -[:INTRODUCES_CONCEPT]-> `Concept` (For seminal contributions)
    *   `Paper` -[:MENTIONS_CONCEPT]-> `Concept` (For general discussion of concepts)
    *   `Paper` -[:ADDRESSES]-> `ResearchProblem`
    *   `Paper` -[:HAS_LIMITATION]-> `Limitation`
    *   `Paper` -[:SUGGESTS]-> `FutureWork`
*   Author-Centric Relationships:
    *   `Author` -[:IS_AFFILIATED_WITH]-> `Affiliation`
    *   `Author` -[:COAUTHORED_WITH_ON {paper_doi: "..."}]-> `Author` (Bidirectional, paper-specific)
*   Objective/Hypothesis/Method Inter-links:
    *   `Objective` -[:IS_ADDRESSED_BY]-> `Hypothesis`
    *   `Hypothesis` -[:IS_TESTED_BY]-> `Method`
*   Conceptual Hierarchy & Links:
    *   `Concept` -[:PART_OF]-> `ResearchTopic` (Groups concepts under broader topics)
    *   `Concept` -[:IS_SUB_CONCEPT_OF]-> `Concept`
    *   `Concept` -[:IS_PREREQUISITE_FOR]-> `Concept`
    *   `Concept` -[:IS_RELATED_TO]-> `Concept`

## Prerequisites

*   Python 3.8+ (FastMCP and Pydantic v2 benefit from newer Python versions)
*   Access to a running Neo4j instance (Version 4.x or 5.x recommended).
*   `uv` (recommended by FastMCP for environment management, especially for `fastmcp install`) or `pip`.
*   For text processing features: `spaCy` library and a model (e.g., `en_core_web_sm`).

## Setup

1.  **Clone the repository (or ensure all files are in the root project directory).**

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  **Install dependencies:**
    Navigate to the project root directory and run:
    ```bash
    pip install -r requirements.txt
    ```
    If you intend to use the NLP features for entity extraction from text, you also need to download a spaCy model (this is done once after installing spaCy):
    ```bash
    python -m spacy download en_core_web_sm
    ```

4.  **Configure Neo4j Connection:**
    The FastMCP server requires Neo4j connection details, which are read from environment variables at startup:
    *   `NEO4J_URI`: e.g., `bolt://localhost:7687` (Default)
    *   `NEO4J_USER`: e.g., `neo4j` (Default)
    *   `NEO4J_PASSWORD`: Your Neo4j password (Required, e.g., `your_secure_password`)

    Set these environment variables in your shell before running the server. For example:
    ```bash
    export NEO4J_URI="bolt://localhost:7687"
    export NEO4J_USER="neo4j"
    export NEO4J_PASSWORD="yourpassword"
    ```

## Running the FastMCP Server

The server is defined in `fastmcp_server.py` and the FastMCP instance is named `mcp_server`.

You can run the server using the `fastmcp` CLI (recommended):

```bash
fastmcp run fastmcp_server.py:mcp_server
```

This will typically start the server using `stdio` transport. To run it with HTTP transport (e.g., for testing with tools like `curl` or other HTTP-based MCP clients):

```bash
fastmcp run fastmcp_server.py:mcp_server --transport http --host 0.0.0.0 --port 8000
```

To run with Server-Sent Events (SSE) transport:
```bash
fastmcp run fastmcp_server.py:mcp_server --transport sse # Default port/path for SSE may vary
```

To run with standard input/output (stdio) transport (often the default if `--transport` is omitted with `fastmcp run`):
```bash
fastmcp run fastmcp_server.py:mcp_server --transport stdio
```

You can also run the server directly using `python fastmcp_server.py`, which will use the default transport specified in its `mcp_server.run()` call (currently stdio).

Using the `fastmcp run` command with the `--transport` flag is generally the most flexible way to control the transport mechanism.

### FastMCP Server Configuration

The server's behavior and settings are configured in several ways:

1.  **Neo4j Database Connection:**
    *   Set these environment variables before starting the server:
        *   `NEO4J_URI`: (Defaults to `bolt://localhost:7687`)
        *   `NEO4J_USER`: (Defaults to `neo4j`)
        *   `NEO4J_PASSWORD`: (Required, e.g., `your_secure_password`)
    *   These are used by the `lifespan` manager in `fastmcp_server.py` to connect to your Neo4j instance.

2.  **`FastMCP` Instance Settings (in `fastmcp_server.py`):**
    *   **Server Name & Instructions:** Defined when `FastMCP(...)` is instantiated (e.g., `name="ResearchPaperKGProcessor"`).
    *   **Dependencies:** Python package dependencies required for the server to run correctly in isolated environments (e.g., when deployed using `fastmcp install`) are listed in the `dependencies` argument of the `FastMCP` constructor. Our server lists `fastmcp`, `neo4j`, `spacy`, and `pydantic`.
    *   **Lifespan Management:** The `@asynccontextmanager def lifespan(app: FastMCP)` function in `fastmcp_server.py` handles startup (Neo4j connection) and shutdown (Neo4j disconnection) logic.

3.  **FastMCP Framework Global Settings:**
    *   FastMCP offers global settings configurable via environment variables prefixed with `FASTMCP_` (e.g., `FASTMCP_LOG_LEVEL=DEBUG`).
    *   Refer to the official FastMCP documentation for a complete list of these global settings.

4.  **Transport-Specific Settings (with `fastmcp run`):**
    *   When using `fastmcp run`, you can specify transport-related options like:
        *   `--host <hostname>` (for HTTP/SSE)
        *   `--port <port_number>` (for HTTP/SSE)
        *   `--log-level <level>` (can override global log level for this run)
    *   Consult `fastmcp run --help` and the FastMCP documentation for all available runtime options.

For comprehensive details on all FastMCP configuration options, please refer to the [official FastMCP documentation](https://gofastmcp.com/).

## Interacting with the `ProcessPaperToKG` Tool

Once the server is running, MCP clients can call the `ProcessPaperToKG` tool. The tool expects a JSON object matching the `PaperDetails` Pydantic model.

**Example Input for `ProcessPaperToKG_V2` tool (reflecting expanded `PaperDetails` model):**
```json
{
  "title": "Comprehensive Analysis of AI in Scientific Discovery",
  "doi": "10.synthetic/ai-discovery-2024",
  "abstract": "This paper presents a comprehensive analysis of AI techniques applied to scientific discovery. It details several objectives, tests specific hypotheses using advanced machine learning methods, and introduces the 'DynamicConcept' framework. Key datasets like 'OpenSciData' were used. Funding was provided by 'FutureTech Grant Program'. Limitations include model interpretability, and future work suggests exploring hybrid AI models.",
  "publication_date": "2024-08-01",
  "authors": [
    {
      "name": "Dr. Alex Chen",
      "orcid": "0000-0001-2345-6789",
      "email": "alex.chen@innovate.edu",
      "affiliation_name": "Innovation University",
      "affiliation_location": "Tech Hub City"
    },
    {
      "name": "Dr. Maria Garcia",
      "orcid": "0000-0002-9876-5432",
      "email": "m.garcia@researchglobal.org",
      "affiliation_name": "Global Research Institute"
    }
  ],
  "keywords": ["Artificial Intelligence", "Scientific Discovery", "Machine Learning", "Knowledge Graphs"],
  "full_text_link": "https://example.com/papers/ai-discovery-2024.pdf",
  "publication_venue": {
    "name": "Journal of AI in Science",
    "issn_isbn": "2222-111X",
    "publisher": "Academic Innovations Press"
  },
  "datasets": [
    {
      "name": "OpenSciData",
      "description": "A large-scale dataset of scientific publications and experimental results.",
      "url": "https://example.com/datasets/openscidata"
    }
  ],
  "funders": [
    {"name": "FutureTech Grant Program"}
  ],
  "objectives": [
    {"description": "To evaluate the effectiveness of current AI models in hypothesis generation."},
    {"description": "To propose a new framework for AI-driven experimental design."}
  ],
  "hypotheses": [
    {
      "description": "Deep learning models outperform traditional statistical methods in predicting experimental outcomes.",
      "tested_by_methods": ["Deep Learning Comparative Analysis", "Statistical Outcome Modeling"]
    },
    {"description": "The 'DynamicConcept' framework reduces time to discovery by 30%."}
  ],
  "introduced_concepts": [
    {
      "name": "DynamicConcept Framework",
      "definition": "A novel computational framework for representing and evolving scientific concepts.",
      "part_of_topics": ["Knowledge Representation", "Computational Science"]
    },
    {
      "name": "Predictive Experimentation AI",
      "definition": "AI systems capable of autonomously designing and predicting outcomes of experiments.",
      "is_sub_concept_of": ["Artificial Intelligence"]
    }
  ],
  "research_problems_addressed": [
    {"description": "High cost and slow pace of traditional scientific experimentation."},
    {"description": "Difficulty in integrating and reasoning over vast amounts of scientific data."}
  ],
  "limitations_stated": [
    {"description": "The proposed 'DynamicConcept' framework has only been validated in simulated environments."},
    {"description": "Current AI models used lack full interpretability in their decision-making processes."}
  ],
  "future_work_suggested": [
    {"description": "Extend validation of the 'DynamicConcept' framework to real-world laboratory experiments."},
    {"description": "Develop new techniques for enhancing the interpretability of AI models in scientific discovery."},
    {"description": "Explore the integration of quantum computing with AI for complex scientific simulations."}
  ]
}
```

**How to call the tool (Conceptual):**

*   **Using a Python FastMCP Client (e.g., in a separate `client_example.py`):**
    ```python
    import asyncio
    from fastmcp import Client

    async def main():
        # Assumes server is running via stdio from `python fastmcp_server.py`
        # or `fastmcp run fastmcp_server.py:mcp_server` (stdio is default)
        # client = Client("fastmcp_server.py:mcp_server")
        # If server is running on HTTP:
        # client = Client("http://localhost:8000/mcp/") # Adjust URL if path is different

        # For stdio, you might point to the process directly if running `python fastmcp_server.py`
        # This part can be tricky with stdio and might require specific client setup.
        # The most robust way is often HTTP or using FastMCP's dev/install features for specific clients.

        # This example assumes you have a way to target the running server.
        # For local testing with stdio, often `Client(mcp_server_object)` is used if client and server are in the same process.
        # For separate processes, a transport like HTTP is easier to target.

        # Let's assume an HTTP client for clarity:
        client = Client("http://localhost:8000/mcp/") # if server run with --transport http

        paper_payload = {
            "title": "Test Paper via Client", "doi": "10.client/test001",
            "abstract": "Testing FastMCP tool call with a client. Mentions machine learning.",
            "authors": [{"name": "Client User"}]
        }
        async with client:
            result = await client.call_tool("ProcessPaperToKG", paper_payload)
            print(result)

    if __name__ == "__main__":
        # asyncio.run(main()) # Uncomment to run if you have a client setup
        print("Client example: Run the server first, then adapt and run this client.")
    ```

*   **Using `curl` (if server is on HTTP, e.g., `http://localhost:8000/mcp/`):**
    The exact `curl` command depends on how FastMCP exposes tools over HTTP and the MCP specification for tool calls via HTTP. This usually involves a POST request with a specific JSON structure for the tool call. Refer to MCP protocol specs for HTTP transport details.

## Project Structure

*   **`fastmcp_server.py`**: Defines the FastMCP server, Pydantic data models, the `lifespan` manager for Neo4j, and the main `ProcessPaperToKG` tool.
*   **`neo4j_handler.py`**: Contains the `Neo4jGraph` class for all Neo4j database interactions.
*   **`text_processor.py`**: Handles NLP tasks (entity extraction from text using spaCy).
*   **`requirements.txt`**: Lists Python package dependencies.
*   **`README.md`**: This file.

## Future Development
*   Develop a dedicated, simple Python client CLI for easier testing and interaction with the `ProcessPaperToKG` tool.
*   Enhance `text_processor.py` with more advanced NLP models.
*   Support for batch processing or input from other sources (e.g., Zotero, arXiv).
*   Expand the ontology and extraction capabilities.
```
