"""MCP server for Cosmos DB CRUD operations on products database."""

from typing import List, Dict
import os
import logging
from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError
from azure.identity import DefaultAzureCredential
from langgraph.prebuilt import create_react_agent

from langchain_openai import AzureChatOpenAI
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from schema_info import SCHEMA_INFO
load_dotenv()

# Configure logging
LOG_DIR = "/app/logs" if os.path.exists("/app/logs") else "."
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'{LOG_DIR}/server.log')
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("remote-db-mcp-server", host="0.0.0.0", port=8000)

# Cosmos DB Configuration
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
DATABASE_NAME = os.getenv("COSMOS_DATABASE", "products-db")
CONTAINER_NAME = os.getenv("COSMOS_CONTAINER", "products")

# Initialize Cosmos DB client
if not COSMOS_ENDPOINT:
    logger.error("COSMOS_ENDPOINT environment variable is not set")
    raise ValueError("COSMOS_ENDPOINT environment variables must be set")

try:
    cosmos_client = CosmosClient(COSMOS_ENDPOINT, credential=DefaultAzureCredential())
    database = cosmos_client.get_database_client(DATABASE_NAME)
    container = database.get_container_client(CONTAINER_NAME)
    logger.info("Successfully connected to Cosmos DB")
except Exception as e:
    logger.error("Failed to connect to Cosmos DB: %s", str(e))
    raise

llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
    temperature=0,
)

query_prompt = f"""
You are a Cosmos DB query assistant. Based on user requests, generate appropriate Cosmos DB SQL queries.
{SCHEMA_INFO}

Analyze the user query, determine what product information they need, and formulate a Cosmos DB SQL query string.

IMPORTANT: Return ONLY the SQL query string without any additional text, markdown formatting, or code blocks.

For example:
- For searching by name: SELECT * FROM c WHERE CONTAINS(c.name, 'MacBook', true)
- For filtering by price: SELECT * FROM c WHERE c.price < 1000

Be specific and precise with your queries.
"""

@mcp.tool()
async def search_products(query: str, limit: int = 10) -> str:
    """Search products by name or description.

    Args:
        query: Search term to look for in product names and descriptions
        limit: Maximum number of results to return (default: 10)
    """
    try:
        agent = create_react_agent(
            llm,
            tools=[],
            prompt=query_prompt,
        )
        result = await agent.ainvoke({"messages": [("user", query)]})
        sql_query = result["messages"][-1].content
        parameters: List[Dict[str, object]] = [{"name": "@query", "value": query}]
        items = list(container.query_items(
            query=sql_query,
            parameters=parameters,
            max_item_count=limit,
            enable_cross_partition_query=True
        ))
        logger.info("Search returned %s results for query: '%s'", len(items), query)
        if not items:
            logger.info("No products found matching query: '%s'", query)
            return f"No products found matching '{query}'."
        result = f"Found {len(items)} products matching '{query}':\n"
        for item in items:
            result += f"- {item['name']} (ID: {item['id']}, Price: ${item['price']})\n"
        
        return result
    except CosmosHttpResponseError as e:
        logger.error("CosmosHttpResponseError searching products: %s", str(e))
        return f"Error searching products: {str(e)}"
    except ValueError as e:
        logger.error("ValueError searching products: %s", str(e))
        return f"Invalid search query: {str(e)}"

# Add health check endpoint
@mcp.custom_route("/health", methods=["GET"])
async def health_check():
    """Health check endpoint for Azure Container Apps"""
    try:
        # Simple check to verify Cosmos DB connection
        database.read()
        return {"status": "healthy", "cosmos_db": "connected"}
    except CosmosHttpResponseError as e:
        logger.error("Health check failed: %s", e)
        return {"status": "unhealthy", "error": str(e)}, 503

if __name__ == "__main__":
    logger.info("Starting MCP server")
    try:
        mcp.run(transport="streamable-http", host="0.0.0.0", port=8000, path="/mcptest")
        logger.info("MCP server started successfully")
    except (OSError, RuntimeError, ValueError) as e:
        logger.error("Failed to start MCP server: %s", str(e))
        raise