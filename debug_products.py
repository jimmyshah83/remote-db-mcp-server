#!/usr/bin/env python3
"""
Debug script to list all products in the database
"""


import asyncio
from src.server import list_products, get_product, search_products

async def _debug_products():
    """List all products to see what's in the database"""
    
    print("Listing all products in the database...")
    print("=" * 50)
    
    result = await list_products(limit=50)
    print(result)
    
async def _debug_product(product_id: str, partition_key: str):
    """Get a specific product by ID"""
    print(f"Getting product with ID: {product_id}")
    print("=" * 50)
    
    result = await get_product(product_id, partition_key)
    print(result)
    
async def _debug_search_product(query: str):
    """Search for a product by name or description"""
    print(f"Searching for product with name: {query}")
    print("=" * 50)
    
    result = await search_products(query)
    print(result)

if __name__ == "__main__":
    # asyncio.run(_debug_product("prod-001", "Electronics")) 
    # asyncio.run(debug_products()) 
    asyncio.run(_debug_search_product("MacBook Pro 16-inch")) 