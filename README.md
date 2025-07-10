# Research Paper Knowledge Graph Processor (FastMCP Edition)

This project provides a FastMCP (Model Context Protocol) server with a tool to process research paper details and create/update a knowledge graph in a Neo4j database.

## Overview

The core of this project is a FastMCP server that exposes a tool named `ProcessPaperToKG`. This tool accepts structured data about a research paper (title, DOI, authors, abstract, etc.), processes it (including NLP on the abstract/text via spaCy if available), and then populates a Neo4j graph database according to a defined ontology.

## Ontology

The knowledge graph aims to capture:

**Core Concepts:**
*   **ResearchPaper:** Title, Abstract, Publication Date, DOI, Keywords, Full Text, Venue.
*   **Author:** Name, Affiliation, OrcID.
*   **Topic:** Name/Keywords.
*   **Institution:** Name, Location.
*   **Method:** Name, Description.
*   **Venue:** Name (e.g., conference, journal).

**Relationships:** (Examples)
*   `HAS_AUTHOR`, `PUBLISHED_IN`, `FOCUSES_ON`, `EMPLOYS_METHOD`, `AFFILIATED_WITH`, `CITES`, `COAUTHORED_WITH_ON`.

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
fastmcp run fastmcp_server.py:mcp_server --transport http --port 8000
```

Alternatively, you can run the server directly using Python for basic stdio operation:
```bash
python fastmcp_server.py
```
(Make sure environment variables for Neo4j are set.)

## Interacting with the `ProcessPaperToKG` Tool

Once the server is running, MCP clients can call the `ProcessPaperToKG` tool. The tool expects a JSON object matching the `PaperDetails` Pydantic model.

**Example Input for `ProcessPaperToKG` tool:**
```json
{
  "title": "A Study on Knowledge Graph Construction",
  "doi": "10.xxxx/example.doi.123",
  "abstract": "This paper explores methods for automatically building knowledge graphs. Research at Example University.",
  "publication_date": "2024-01-15",
  "authors": [
    {"name": "Dr. Eva Core", "orcid": "0000-0001-2345-0001", "affiliation": "Example University"},
    {"name": "Dr. Max Headroom", "affiliation": "Some Other University"}
  ],
  "keywords": ["Knowledge Graphs", "NLP", "Science"],
  "venue_name": "Journal of Advanced Scientific Computing",
  "full_text": null
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
