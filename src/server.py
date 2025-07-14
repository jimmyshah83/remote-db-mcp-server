"""MCP server for Cosmos DB CRUD operations on products database."""

from typing import Optional, List, Dict
import os
from datetime import datetime
from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError
from azure.identity import DefaultAzureCredential

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("remote-db-mcp-server")

# Cosmos DB Configuration
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
DATABASE_NAME = os.getenv("COSMOS_DATABASE", "products-db")
CONTAINER_NAME = os.getenv("COSMOS_CONTAINER", "products")

# Initialize Cosmos DB client
if not COSMOS_ENDPOINT:
    raise ValueError("COSMOS_ENDPOINT environment variables must be set")

cosmos_client = CosmosClient(COSMOS_ENDPOINT, credential=DefaultAzureCredential())
database = cosmos_client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

@mcp.tool()
async def get_product(product_id: str) -> str:
    """Get a product by its ID.

    Args:
        product_id: The unique identifier of the product
    """
    try:
        item = container.read_item(item=product_id, partition_key=product_id)
        return f"Product found:\n{str(item)}"
    except CosmosHttpResponseError as e:
        if e.status_code == 404:
            return f"Product with ID '{product_id}' not found."
        return f"Error retrieving product: {str(e)}"
    except ValueError as e:
        return f"Invalid product ID: {str(e)}"

@mcp.tool()
async def list_products(category: Optional[str] = None, limit: int = 10) -> str:
    """List products with optional filtering by category.

    Args:
        category: Optional category filter (e.g., 'Electronics', 'Clothing')
        limit: Maximum number of products to return (default: 10)
    """
    try:
        if category:
            query = "SELECT * FROM c WHERE c.category = @category"
            items = list(container.query_items(
                query=query,
                parameters=[{"name": "@category", "value": category}],
                max_item_count=limit
            ))
        else:
            query = "SELECT * FROM c"
            items = list(container.query_items(
                query=query,
                parameters=None,
                max_item_count=limit
            ))
        
        if not items:
            return "No products found."
        
        result = f"Found {len(items)} products:\n"
        for item in items:
            result += f"- {item['name']} (ID: {item['id']}, Price: ${item['price']})\n"
        
        return result
    except (CosmosHttpResponseError, ValueError) as e:
        return f"Error listing products: {str(e)}"

@mcp.tool()
async def create_product(product_data: dict) -> str:
    """Create a new product in the database.

    Args:
        product_data: Dictionary containing product information (id, name, category, price, etc.)
    """
    try:
        # Ensure required fields are present
        required_fields = ['id', 'name', 'category', 'price']
        for field in required_fields:
            if field not in product_data:
                return f"Missing required field: {field}"
        
        # Add timestamps if not present
        if 'createdAt' not in product_data:
            product_data['createdAt'] = datetime.utcnow().isoformat() + 'Z'
        if 'updatedAt' not in product_data:
            product_data['updatedAt'] = product_data['createdAt']
        
        container.create_item(body=product_data)
        return f"Product '{product_data['name']}' created successfully with ID: {product_data['id']}"
    except CosmosHttpResponseError as e:
        if e.status_code == 409:
            return f"Product with ID '{product_data.get('id')}' already exists."
        return f"Error creating product: {str(e)}"
    except ValueError as e:
        return f"Invalid product data: {str(e)}"

@mcp.tool()
async def update_product(product_id: str, updates: dict) -> str:
    """Update an existing product.

    Args:
        product_id: The ID of the product to update
        updates: Dictionary containing the fields to update
    """
    try:
        # Get the existing item
        existing_item = container.read_item(item=product_id, partition_key=product_id)
        
        # Update the item
        for key, value in updates.items():
            existing_item[key] = value
        
        # Update timestamp
        existing_item['updatedAt'] = datetime.utcnow().isoformat() + 'Z'
        
        container.replace_item(item=product_id, body=existing_item)
        return f"Product '{existing_item['name']}' updated successfully."
    except CosmosHttpResponseError as e:
        if e.status_code == 404:
            return f"Product with ID '{product_id}' not found."
        return f"Error updating product: {str(e)}"
    except ValueError as e:
        return f"Invalid update data: {str(e)}"

@mcp.tool()
async def delete_product(product_id: str) -> str:
    """Delete a product by its ID.

    Args:
        product_id: The unique identifier of the product to delete
    """
    try:
        container.delete_item(item=product_id, partition_key=product_id)
        return f"Product with ID '{product_id}' deleted successfully."
    except CosmosHttpResponseError as e:
        if e.status_code == 404:
            return f"Product with ID '{product_id}' not found."
        return f"Error deleting product: {str(e)}"

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
            max_item_count=limit
        ))
        
        if not items:
            return f"No products found matching '{query}'."
        
        result = f"Found {len(items)} products matching '{query}':\n"
        for item in items:
            result += f"- {item['name']} (ID: {item['id']}, Price: ${item['price']})\n"
        
        return result
    except CosmosHttpResponseError as e:
        return f"Error searching products: {str(e)}"
    except ValueError as e:
        return f"Invalid search query: {str(e)}"

if __name__ == "__main__":
    import asyncio
    asyncio.run(mcp.run())