# Cosmos DB Setup Guide

This guide will help you insert the test product JSON documents into your Azure Cosmos DB.

## Prerequisites

1. **Azure Cosmos DB Account**: You need an existing Cosmos DB account in Azure
2. **Connection Details**: Your Cosmos DB endpoint and primary key

## Step 1: Get Your Cosmos DB Connection Details

1. Go to the [Azure Portal](https://portal.azure.com)
2. Navigate to your Cosmos DB account
3. Go to **Keys** in the left sidebar
4. Copy the **URI** (endpoint) and **PRIMARY KEY**

## Step 2: Set Up Environment Variables

Create a `.env` file in your project root with the following variables:

### Option A: Key-based Authentication (Traditional)
```bash
# Cosmos DB Connection Settings
COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
COSMOS_KEY=your-primary-key-here

# Optional: Custom database and container names
COSMOS_DATABASE=products-db
COSMOS_CONTAINER=products
```

### Option B: Service Principal Authentication (Recommended for production)
```bash
# Cosmos DB Connection Settings
COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
# COSMOS_KEY=  # Leave this empty for service principal authentication

# Service Principal Credentials
AZURE_CLIENT_ID=your-service-principal-client-id
AZURE_CLIENT_SECRET=your-service-principal-client-secret
AZURE_TENANT_ID=your-azure-tenant-id

# Optional: Custom database and container names
COSMOS_DATABASE=products-db
COSMOS_CONTAINER=products
```

### Option C: AAD Authentication (Interactive login)
```bash
# Cosmos DB Connection Settings
COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
# COSMOS_KEY=  # Leave this empty for AAD authentication

# Optional: Custom database and container names
COSMOS_DATABASE=products-db
COSMOS_CONTAINER=products
```

**For AAD authentication, you need to be logged in with Azure CLI:**
```bash
az login
```

**Replace the placeholder values with your actual Cosmos DB connection details.**

## Step 3: Install Dependencies

Make sure you have the required dependencies installed:

```bash
pip install azure-cosmos python-dotenv
```

Or if you're using uv:

```bash
uv sync
```

## Step 4: Insert Products into Cosmos DB

Run the insertion script:

```bash
python src/insert_products.py
```

This script will:
- Create a database called `products-db` (or your custom name)
- Create a container called `products` with partition key on `category`
- Load the product data from `src/db.json`
- Insert all 10 products into the container
- Display insertion statistics and example queries

## Expected Output

You should see output similar to:

```
Database 'products-db' ready
Container 'products' ready with partition key on 'category'
Loaded 10 products from src/db.json

Inserting products into Cosmos DB...
✓ Inserted product: MacBook Pro 16-inch (ID: prod-001)
✓ Inserted product: Sony WH-1000XM5 Wireless Headphones (ID: prod-002)
...

=== Insertion Results ===
Successful: 10
Failed: 0

=== Container Statistics ===
container_id: products
partition_key: ['/category']
item_count: 10
last_modified: 2024-01-15T10:30:00Z

=== Example Queries ===
Total products in database: 10
Electronics products: 4
Products over $1000: 3

✅ Product insertion completed successfully!
```

## Troubleshooting

### Common Issues:

1. **Connection Error**: 
   - Verify your endpoint and key are correct
   - Check that your Cosmos DB account is running
   - Ensure your IP is whitelisted if using IP restrictions

2. **Permission Error**:
   - Make sure you're using the **PRIMARY KEY** (not the secondary key)
   - Verify your account has the necessary permissions

3. **Container Already Exists**:
   - The script will use the existing container if it exists
   - If you want to start fresh, delete the container manually in the Azure portal

## Query Examples

After insertion, you can run queries like:

```sql
-- Get all products
SELECT * FROM c

-- Get electronics products
SELECT * FROM c WHERE c.category = 'Electronics'

-- Get expensive products
SELECT * FROM c WHERE c.price > 1000

-- Get products by brand
SELECT * FROM c WHERE c.brand = 'Apple'

-- Get products in stock
SELECT * FROM c WHERE c.inStock = true

-- Get products with high ratings
SELECT * FROM c WHERE c.rating >= 4.5
```

## Next Steps

Once your products are inserted, you can:
1. Use the Azure Portal to explore your data
2. Build queries in the Data Explorer
3. Integrate with your application using the Cosmos DB SDK
4. Set up additional indexes for better query performance 