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

## Step 2: Configure Role Assignments (Required for Service Principal Authentication)

Before setting up environment variables, you need to configure proper role assignments for your Cosmos DB account. This is especially important when using service principal authentication.

### 2.1: Create a Service Principal (if not already created)

If you don't have a service principal, create one:

```bash
# Create service principal
az ad sp create-for-rbac --name "cosmos-db-service-principal" --skip-assignment

# This will output something like:
# {
#   "appId": "your-client-id",
#   "displayName": "cosmos-db-service-principal",
#   "name": "http://cosmos-db-service-principal",
#   "password": "your-client-secret",
#   "tenant": "your-tenant-id"
# }
```

### 2.2: Assign Cosmos DB Roles

Assign the appropriate roles to your service principal:

```bash
# Get your Cosmos DB account resource ID
COSMOS_ACCOUNT_ID=$(az cosmosdb show --name YOUR_COSMOS_ACCOUNT_NAME --resource-group YOUR_RESOURCE_GROUP --query id -o tsv)

# Get your service principal object ID
SP_OBJECT_ID=$(az ad sp show --id YOUR_CLIENT_ID --query id -o tsv)

# Assign Cosmos DB Built-in Data Contributor role
az role assignment create \
    --assignee $SP_OBJECT_ID \
    --role "Cosmos DB Built-in Data Contributor" \
    --scope $COSMOS_ACCOUNT_ID

# Alternative: Assign Cosmos DB Built-in Data Reader role (read-only access)
# az role assignment create \
#     --assignee $SP_OBJECT_ID \
#     --role "Cosmos DB Built-in Data Reader" \
#     --scope $COSMOS_ACCOUNT_ID
```

### 2.3: Available Cosmos DB Built-in Roles

| Role | Permissions | Use Case |
|------|-------------|----------|
| **Cosmos DB Built-in Data Contributor** | Full read/write access to data | Applications that need to insert, update, delete data |
| **Cosmos DB Built-in Data Reader** | Read-only access to data | Reporting, analytics, read-only applications |
| **Cosmos DB Built-in Data AEM** | Read/write access with AEM (Azure Event Mesh) | Event-driven applications |
| **Cosmos DB Built-in Data Backup Administrator** | Backup and restore operations | Backup management |
| **Cosmos DB Built-in Data Operator** | Read/write access without schema changes | Limited data operations |

### 2.4: Custom Role Definitions (Advanced)

For more granular control, you can create custom roles:

```bash
# Create custom role definition JSON
cat > cosmos-custom-role.json << EOF
{
  "Name": "Cosmos Custom Data Operator",
  "Description": "Custom role for specific data operations",
  "Actions": [
    "Microsoft.DocumentDB/databaseAccounts/read",
    "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/read",
    "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/read",
    "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/read",
    "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/write"
  ],
  "NotActions": [],
  "DataActions": [
    "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/*"
  ],
  "NotDataActions": [],
  "AssignableScopes": [
    "/subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/YOUR_RESOURCE_GROUP/providers/Microsoft.DocumentDB/databaseAccounts/YOUR_COSMOS_ACCOUNT_NAME"
  ]
}
EOF

# Create the custom role
az role definition create --role-definition cosmos-custom-role.json

# Assign the custom role
az role assignment create \
    --assignee $SP_OBJECT_ID \
    --role "Cosmos Custom Data Operator" \
    --scope $COSMOS_ACCOUNT_ID
```

### 2.5: Verify Role Assignments

Check that your role assignments are working:

```bash
# List role assignments for your service principal
az role assignment list --assignee YOUR_CLIENT_ID --scope $COSMOS_ACCOUNT_ID

# Test authentication (optional)
az cosmosdb sql database list \
    --account-name YOUR_COSMOS_ACCOUNT_NAME \
    --resource-group YOUR_RESOURCE_GROUP \
    --auth-type aad
```

## Step 3: Set Up Environment Variables

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

## Step 4: Install Dependencies

Make sure you have the required dependencies installed:

```bash
pip install azure-cosmos python-dotenv
```

Or if you're using uv:

```bash
uv sync
```

## Step 5: Insert Products into Cosmos DB

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
   - For service principal authentication, ensure proper role assignments are configured

3. **Role Assignment Issues**:
   - Verify the service principal has the correct Cosmos DB roles assigned
   - Check that the role assignment scope includes your Cosmos DB account
   - Ensure the service principal credentials are correct in your `.env` file
   - Run `az role assignment list --assignee YOUR_CLIENT_ID` to verify assignments

4. **Authentication Errors**:
   - For service principal: Check `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, and `AZURE_TENANT_ID`
   - For AAD: Ensure you're logged in with `az login`
   - Verify the service principal hasn't expired or been deleted

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

## Security Best Practices

### Role Assignment Security

1. **Principle of Least Privilege**: Only assign the minimum permissions necessary
   - Use `Cosmos DB Built-in Data Reader` for read-only access
   - Use `Cosmos DB Built-in Data Contributor` only when write access is needed

2. **Scope Limitation**: Assign roles at the most specific scope possible
   - Prefer database-level or container-level scopes over account-level
   - Use resource group scope only when necessary

3. **Regular Auditing**: Periodically review role assignments
   ```bash
   # List all role assignments for your Cosmos DB account
   az role assignment list --scope $COSMOS_ACCOUNT_ID
   
   # Remove unnecessary assignments
   az role assignment delete --assignee SP_OBJECT_ID --role "Role Name" --scope $COSMOS_ACCOUNT_ID
   ```

4. **Service Principal Management**:
   - Rotate service principal secrets regularly
   - Use managed identities when possible (for Azure-hosted applications)
   - Monitor service principal usage in Azure AD

### Network Security

1. **IP Restrictions**: Configure IP allowlists in Cosmos DB
2. **Private Endpoints**: Use private endpoints for secure connectivity
3. **VNet Integration**: Configure virtual network integration when possible

## Next Steps

Once your products are inserted, you can:
1. Use the Azure Portal to explore your data
2. Build queries in the Data Explorer
3. Integrate with your application using the Cosmos DB SDK
4. Set up additional indexes for better query performance
5. Implement monitoring and alerting for your Cosmos DB account 