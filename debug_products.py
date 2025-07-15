#!/usr/bin/env python3
"""
Debug script to list all products in the database
"""


import asyncio
from src.server import list_products, get_product

async def debug_products():
    """List all products to see what's in the database"""
    
    print("Listing all products in the database...")
    print("=" * 50)
    
    result = await list_products(limit=50)
    print(result)
    
async def debug_product(product_id: str):
    """Get a specific product by ID"""
    print(f"Getting product with ID: {product_id}")
    print("=" * 50)
    
    result = await get_product(product_id)
    print(result)

if __name__ == "__main__":
    asyncio.run(debug_product("prod-001")) 
    # asyncio.run(debug_products()) 