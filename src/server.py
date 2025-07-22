"""MCP server for Cosmos DB CRUD operations on products database."""

from typing import Optional, List, Dict
import os
import logging
from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError
from azure.identity import DefaultAzureCredential

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('server.log')
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("remote-db-mcp-server")

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

@mcp.tool()
async def search_products(query: str, limit: int = 10) -> str:
    """Search products by name or description.

    Args:
        query: Search term to look for in product names and descriptions
        limit: Maximum number of results to return (default: 10)
    """
    try:
        sql_query = """
        SELECT * FROM c 
        WHERE CONTAINS(c.name, @query, true) 
        OR CONTAINS(c.description, @query, true)
        """
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

if __name__ == "__main__":
    logger.info("Starting MCP server...")
    try:
        mcp.run(transport="streamable-http")
        logger.info("MCP server started successfully")
    except Exception as e:
        logger.error("Failed to start MCP server: %s", str(e))
        raise