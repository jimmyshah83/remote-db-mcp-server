"""MCP server for Cosmos DB CRUD operations on products database."""

from typing import Optional, List, Dict
import os
import logging
from datetime import datetime
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

logger.info(f"Initializing Cosmos DB connection to endpoint: {COSMOS_ENDPOINT}")
logger.info(f"Database: {DATABASE_NAME}, Container: {CONTAINER_NAME}")

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
    logger.error(f"Failed to connect to Cosmos DB: {str(e)}")
    raise

@mcp.tool()
async def get_product(product_id: str) -> str:
    """Get a product by its ID.

    Args:
        product_id: The unique identifier of the product
    """
    logger.info(f"Attempting to get product with ID: {product_id}")
    try:
        item = container.read_item(item=product_id, partition_key=product_id)
        logger.info(f"Successfully retrieved product: {product_id}")
        return f"Product found:\n{str(item)}"
    except CosmosHttpResponseError as e:
        if e.status_code == 404:
            logger.warning(f"Product with ID '{product_id}' not found")
            return f"Product with ID '{product_id}' not found."
        logger.error(f"CosmosHttpResponseError retrieving product {product_id}: {str(e)}")
        return f"Error retrieving product: {str(e)}"
    except ValueError as e:
        logger.error(f"Invalid product ID {product_id}: {str(e)}")
        return f"Invalid product ID: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error retrieving product {product_id}: {str(e)}")
        return f"Unexpected error: {str(e)}"

@mcp.tool()
async def list_products(category: Optional[str] = None, limit: int = 10) -> str:
    """List products with optional filtering by category.

    Args:
        category: Optional category filter (e.g., 'Electronics', 'Clothing')
        limit: Maximum number of products to return (default: 10)
    """
    logger.info(f"Listing products - category: {category}, limit: {limit}")
    try:
        if category:
            query = "SELECT * FROM c WHERE c.category = @category"
            logger.debug(f"Executing query: {query} with category: {category}")
            items = list(container.query_items(
                query=query,
                parameters=[{"name": "@category", "value": category}],
                max_item_count=limit
            ))
        else:
            query = "SELECT * FROM c"
            logger.debug(f"Executing query: {query}")
            items = list(container.query_items(
                query=query,
                parameters=None,
                max_item_count=limit
            ))
        
        logger.info(f"Retrieved {len(items)} products")
        if not items:
            logger.info("No products found")
            return "No products found."
        
        result = f"Found {len(items)} products:\n"
        for item in items:
            result += f"- {item['name']} (ID: {item['id']}, Price: ${item['price']})\n"
        
        return result
    except CosmosHttpResponseError as e:
        logger.error(f"CosmosHttpResponseError listing products: {str(e)}")
        return f"Error listing products: {str(e)}"
    except ValueError as e:
        logger.error(f"ValueError listing products: {str(e)}")
        return f"Error listing products: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error listing products: {str(e)}")
        return f"Unexpected error: {str(e)}"

@mcp.tool()
async def create_product(product_data: dict) -> str:
    """Create a new product in the database.

    Args:
        product_data: Dictionary containing product information (id, name, category, price, etc.)
    """
    logger.info(f"Creating product with data: {product_data}")
    try:
        # Ensure required fields are present
        required_fields = ['id', 'name', 'category', 'price']
        for field in required_fields:
            if field not in product_data:
                logger.error(f"Missing required field: {field}")
                return f"Missing required field: {field}"
        
        logger.debug(f"Product data validation passed for ID: {product_data.get('id')}")
        
        # Add timestamps if not present
        if 'createdAt' not in product_data:
            product_data['createdAt'] = datetime.utcnow().isoformat() + 'Z'
        if 'updatedAt' not in product_data:
            product_data['updatedAt'] = product_data['createdAt']
        
        container.create_item(body=product_data)
        logger.info(f"Successfully created product: {product_data['name']} (ID: {product_data['id']})")
        return f"Product '{product_data['name']}' created successfully with ID: {product_data['id']}"
    except CosmosHttpResponseError as e:
        if e.status_code == 409:
            logger.warning(f"Product with ID '{product_data.get('id')}' already exists")
            return f"Product with ID '{product_data.get('id')}' already exists."
        logger.error(f"CosmosHttpResponseError creating product: {str(e)}")
        return f"Error creating product: {str(e)}"
    except ValueError as e:
        logger.error(f"ValueError creating product: {str(e)}")
        return f"Invalid product data: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error creating product: {str(e)}")
        return f"Unexpected error: {str(e)}"

@mcp.tool()
async def update_product(product_id: str, updates: dict) -> str:
    """Update an existing product.

    Args:
        product_id: The ID of the product to update
        updates: Dictionary containing the fields to update
    """
    logger.info(f"Updating product {product_id} with updates: {updates}")
    try:
        # Get the existing item
        existing_item = container.read_item(item=product_id, partition_key=product_id)
        logger.debug(f"Retrieved existing product: {existing_item.get('name', 'Unknown')}")
        
        # Update the item
        for key, value in updates.items():
            existing_item[key] = value
            logger.debug(f"Updated field '{key}' to '{value}'")
        
        # Update timestamp
        existing_item['updatedAt'] = datetime.utcnow().isoformat() + 'Z'
        
        container.replace_item(item=product_id, body=existing_item)
        logger.info(f"Successfully updated product: {existing_item.get('name', 'Unknown')} (ID: {product_id})")
        return f"Product '{existing_item['name']}' updated successfully."
    except CosmosHttpResponseError as e:
        if e.status_code == 404:
            logger.warning(f"Product with ID '{product_id}' not found for update")
            return f"Product with ID '{product_id}' not found."
        logger.error(f"CosmosHttpResponseError updating product {product_id}: {str(e)}")
        return f"Error updating product: {str(e)}"
    except ValueError as e:
        logger.error(f"ValueError updating product {product_id}: {str(e)}")
        return f"Invalid update data: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error updating product {product_id}: {str(e)}")
        return f"Unexpected error: {str(e)}"

@mcp.tool()
async def delete_product(product_id: str) -> str:
    """Delete a product by its ID.

    Args:
        product_id: The unique identifier of the product to delete
    """
    logger.info(f"Attempting to delete product with ID: {product_id}")
    try:
        container.delete_item(item=product_id, partition_key=product_id)
        logger.info(f"Successfully deleted product with ID: {product_id}")
        return f"Product with ID '{product_id}' deleted successfully."
    except CosmosHttpResponseError as e:
        if e.status_code == 404:
            logger.warning(f"Product with ID '{product_id}' not found for deletion")
            return f"Product with ID '{product_id}' not found."
        logger.error(f"CosmosHttpResponseError deleting product {product_id}: {str(e)}")
        return f"Error deleting product: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error deleting product {product_id}: {str(e)}")
        return f"Unexpected error: {str(e)}"

@mcp.tool()
async def search_products(query: str, limit: int = 10) -> str:
    """Search products by name or description.

    Args:
        query: Search term to look for in product names and descriptions
        limit: Maximum number of results to return (default: 10)
    """
    logger.info(f"Searching products with query: '{query}', limit: {limit}")
    try:
        sql_query = """
        SELECT * FROM c 
        WHERE CONTAINS(c.name, @query, true) 
        OR CONTAINS(c.description, @query, true)
        """
        parameters: List[Dict[str, object]] = [{"name": "@query", "value": query}]
        
        logger.debug(f"Executing search query: {sql_query.strip()}")
        items = list(container.query_items(
            query=sql_query,
            parameters=parameters,
            max_item_count=limit
        ))
        
        logger.info(f"Search returned {len(items)} results for query: '{query}'")
        if not items:
            logger.info(f"No products found matching query: '{query}'")
            return f"No products found matching '{query}'."
        
        result = f"Found {len(items)} products matching '{query}':\n"
        for item in items:
            result += f"- {item['name']} (ID: {item['id']}, Price: ${item['price']})\n"
        
        return result
    except CosmosHttpResponseError as e:
        logger.error(f"CosmosHttpResponseError searching products: {str(e)}")
        return f"Error searching products: {str(e)}"
    except ValueError as e:
        logger.error(f"ValueError searching products: {str(e)}")
        return f"Invalid search query: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error searching products: {str(e)}")
        return f"Unexpected error: {str(e)}"

if __name__ == "__main__":
    logger.info("Starting MCP server...")
    try:
        mcp.run(transport="stdio")
        logger.info("MCP server started successfully")
    except Exception as e:
        logger.error(f"Failed to start MCP server: {str(e)}")
        raise