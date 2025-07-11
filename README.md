# Research Paper Knowledge Graph Processor (FastMCP Edition)

This project provides a FastMCP (Model Context Protocol) server with a tool to process research paper details and create/update a knowledge graph in a Neo4j database.

## Overview

The core of this project is a FastMCP server that exposes a tool named `ProcessPaperToKG`. This tool accepts structured data about a research paper (title, DOI, authors, abstract, etc.), processes it (including NLP on the abstract/text via spaCy if available), and then populates a Neo4j graph database according to a defined ontology.

## Ontology

The knowledge graph is built according to the following ontology:

**Core Entities (Node Labels):**
*   **`Paper`**: Represents a research publication.
    *   *Properties:* `title`, `abstract`, `publication_date`, `doi` (unique ID), `keywords` (list), `full_text_link` (URL).
*   **`Author`**: An individual who contributed to a paper.
    *   *Properties:* `name`, `orcid` (unique ID, optional), `email` (optional).
*   **`Affiliation`**: An institution or organization an author is associated with.
    *   *Properties:* `name` (unique ID), `location` (optional).
*   **`PublicationVenue`**: The entity where the paper is published (e.g., journal, conference).
    *   *Properties:* `name` (unique ID), `issn_isbn` (optional), `publisher` (optional).
*   **`ResearchTopic`**: The subject area or keyword associated with a paper.
    *   *Properties:* `name` (unique ID).
*   **`Method`**: A specific technique, algorithm, or methodology used.
    *   *Properties:* `name` (unique ID), `description` (optional).
*   **`Dataset`**: A collection of data used or produced.
    *   *Properties:* `name` (unique ID), `description` (optional), `url` (optional).
*   **`Funder`**: An organization that funded the research.
    *   *Properties:* `name` (unique ID).

**Relationships (Edge Types):**
*   `Paper` -[:HAS_AUTHOR]-> `Author` (Inverse: `Author` -[:AUTHORED_BY]-> `Paper`)
*   `Author` -[:IS_AFFILIATED_WITH]-> `Affiliation`
*   `Paper` -[:PUBLISHED_IN]-> `PublicationVenue`
*   `Paper` -[:HAS_TOPIC]-> `ResearchTopic`
*   `Paper` -[:USES_METHOD]-> `Method`
*   `Paper` -[:USES_DATASET]-> `Dataset`
*   `Paper` -[:IS_FUNDED_BY]-> `Funder`
*   `Paper` -[:CITES]-> `Paper` (Inverse: `Paper` -[:REFERENCED_BY]-> `Paper`)
*   `Author` -[:COAUTHORED_WITH_ON {paper_doi: "..."}]-> `Author` (Bidirectional for a specific paper)

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

**Example Input for `ProcessPaperToKG` tool (reflecting updated `PaperDetails` model):**
```json
{
  "title": "Advanced Techniques in Scientific KG Construction",
  "doi": "10.sample/advkg2024",
  "abstract": "This paper details advanced methods for building knowledge graphs from scientific literature, focusing on NLP and machine learning. Research funded by The Science Foundation and conducted at Premier University.",
  "publication_date": "2024-07-15",
  "authors": [
    {
      "name": "Dr. Jane Smith",
      "orcid": "0000-0002-1825-0097",
      "email": "jane.smith@example.com",
      "affiliation_name": "Premier University",
      "affiliation_location": "Tech City"
    },
    {
      "name": "Dr. John Doe",
      "email": "john.doe@research.org",
      "affiliation_name": "Independent Research Lab"
    }
  ],
  "keywords": ["Knowledge Representation", "Scientific Data", "Machine Learning"],
  "full_text_link": "https://example.com/papers/advkg2024.pdf",
  "publication_venue": {
    "name": "Journal of Semantic Web Technologies",
    "issn_isbn": "1234-567X",
    "publisher": "Tech Press"
  },
  "datasets": [
    {
      "name": "SciGraph Dataset v2",
      "description": "A benchmark dataset for scientific KG construction.",
      "url": "https://example.com/datasets/scigraph_v2"
    }
  ],
  "funders": [
    {"name": "The Science Foundation"},
    {"name": "National Research Council"}
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
