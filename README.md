# Remote DB MCP Server

A Model Context Protocol (MCP) server that provides database access capabilities, with a LangChain-powered client for intelligent query processing.

## Features

- **MCP Server**: Provides database tools and operations
- **LangChain Client**: Uses Azure OpenAI and ReAct agent for intelligent tool usage
- **Async Support**: Full async/await support for better performance
- **Tool Integration**: Seamless integration between MCP tools and LangChain agents

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy `config.example` to `.env` and configure your Azure OpenAI settings:

```bash
cp config.example .env
```

Required environment variables:
- `AZURE_OPENAI_DEPLOYMENT_NAME`: Your Azure OpenAI deployment name
- `AZURE_OPENAI_API_KEY`: Your Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI endpoint URL
- `AZURE_OPENAI_API_VERSION`: API version (default: 2024-02-15-preview)

### 3. Usage

#### Start the MCP Server

```bash
python src/server.py
```

#### Run the LangChain Client

```bash
python src/client.py path/to/server.py
```

The client will:
1. Connect to the MCP server
2. Discover available tools
3. Create a ReAct agent with the tools
4. Start an interactive chat loop

## Architecture

### MCPTool Class
- Wraps MCP tools to work with LangChain
- Handles async tool execution
- Provides proper error handling

### MCPClient Class
- Manages connection to MCP server
- Creates LangChain ReAct agent
- Handles query processing with tool integration

## Dependencies

- `langchain-openai`: Azure OpenAI integration
- `langgraph`: ReAct agent implementation
- `langchain-core`: Core LangChain functionality
- `mcp[cli]`: Model Context Protocol
- `python-dotenv`: Environment variable management

## Example Usage

```python
# The client automatically discovers tools from the MCP server
# and creates a ReAct agent that can use them intelligently

# Start the client
client = MCPClient()
await client.connect_to_server("path/to/server.py")

# Ask questions that will use the available tools
response = await client.process_query("Show me all products in the database")
print(response)
```

## Deploying to Azure

You can deploy the MCP server to Azure using either Azure Container Apps (recommended) or Azure Developer CLI (azd). Both approaches provide scalable, managed hosting for your application.

### Option 1: Quick Deployment with Azure Developer CLI (Recommended)

The fastest way to deploy is using Azure Developer CLI, which handles infrastructure provisioning and deployment automatically.

#### Prerequisites

1. Install [Azure Developer CLI (azd)](https://aka.ms/azure-dev/install)
2. Install [Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli)
3. Have an Azure subscription

#### Deployment Steps

1. **Initialize azd project:**

   ```bash
   azd init --template minimal
   ```

2. **Configure environment variables:**

   Copy your `.env` file values to azd environment:

   ```bash
   azd env set AZURE_OPENAI_DEPLOYMENT_NAME "<your-deployment-name>"
   azd env set AZURE_OPENAI_ENDPOINT "<your-openai-endpoint>"
   azd env set COSMOS_DB_ENDPOINT "<your-cosmos-endpoint>"
   azd env set COSMOS_DB_DATABASE "<your-database-name>"
   azd env set COSMOS_DB_CONTAINER "<your-container-name>"
   ```

3. **Deploy to Azure:**

   ```bash
   azd up
   ```

   This command will:
   - Provision Azure resources (Container Apps, Container Registry, etc.)
   - Build and push your Docker image
   - Deploy your application
   - Configure managed identity and RBAC permissions

### Option 2: Manual Deployment with Azure Container Apps

For more control over the deployment process, you can manually deploy using Azure CLI.

#### Setup Prerequisites

1. Azure CLI installed and configured
2. Docker installed locally
3. An Azure Container Registry (ACR) or Docker Hub account

#### Step 1: Prepare Your Environment

1. **Login to Azure:**

   ```bash
   az login
   az account set --subscription "<your-subscription-id>"
   ```

2. **Set deployment variables:**

   ```bash
   RESOURCE_GROUP="rg-mcp-server"
   LOCATION="eastus"
   ACR_NAME="mcpserveracr$(date +%s)"
   CONTAINER_APP_ENV="mcp-server-env"
   CONTAINER_APP_NAME="mcp-server"
   IMAGE_NAME="remote-db-mcp-server"
   ```

#### Step 2: Create Azure Resources

1. **Create resource group:**

   ```bash
   az group create --name $RESOURCE_GROUP --location $LOCATION
   ```

2. **Create Azure Container Registry:**

   ```bash
   az acr create \
     --resource-group $RESOURCE_GROUP \
     --name $ACR_NAME \
     --sku Basic \
     --admin-enabled true
   ```

3. **Create Container Apps environment:**

   ```bash
   az containerapp env create \
     --name $CONTAINER_APP_ENV \
     --resource-group $RESOURCE_GROUP \
     --location $LOCATION
   ```

#### Step 3: Build and Push Container Image

1. **Login to Azure Container Registry:**

   ```bash
   az acr login --name $ACR_NAME
   ```

2. **Build and push Docker image:**

   ```bash
   # Build the image
   docker build -t $ACR_NAME.azurecr.io/$IMAGE_NAME:latest .
   
   # Push to ACR
   docker push $ACR_NAME.azurecr.io/$IMAGE_NAME:latest
   ```

#### Step 4: Deploy Container App

1. **Create the Container App:**

   ```bash
   az containerapp create \
     --name $CONTAINER_APP_NAME \
     --resource-group $RESOURCE_GROUP \
     --environment $CONTAINER_APP_ENV \
     --image $ACR_NAME.azurecr.io/$IMAGE_NAME:latest \
     --target-port 8000 \
     --ingress 'external' \
     --registry-server $ACR_NAME.azurecr.io \
     --min-replicas 1 \
     --max-replicas 3 \
     --cpu 0.25 \
     --memory 0.5Gi \
     --env-vars \
       AZURE_OPENAI_DEPLOYMENT_NAME="<your-deployment-name>" \
       AZURE_OPENAI_ENDPOINT="<your-openai-endpoint>" \
       AZURE_OPENAI_API_VERSION="2024-02-15-preview" \
       COSMOS_DB_ENDPOINT="<your-cosmos-endpoint>" \
       COSMOS_DB_DATABASE="<your-database-name>" \
       COSMOS_DB_CONTAINER="<your-container-name>"
   ```

#### Step 5: Configure Managed Identity (Recommended)

For production deployments, use managed identity instead of API keys:

1. **Enable system-assigned managed identity:**

   ```bash
   az containerapp identity assign \
     --name $CONTAINER_APP_NAME \
     --resource-group $RESOURCE_GROUP \
     --system-assigned
   ```

2. **Grant permissions to Azure OpenAI:**

   ```bash
   # Get the managed identity principal ID
   PRINCIPAL_ID=$(az containerapp identity show \
     --name $CONTAINER_APP_NAME \
     --resource-group $RESOURCE_GROUP \
     --query principalId \
     --output tsv)
   
   # Assign Cognitive Services OpenAI User role
   az role assignment create \
     --role "Cognitive Services OpenAI User" \
     --assignee $PRINCIPAL_ID \
     --scope "<your-openai-resource-id>"
   ```

3. **Grant permissions to Cosmos DB:**

   ```bash
   # Assign Cosmos DB Built-in Data Contributor role
   az role assignment create \
     --role "Cosmos DB Built-in Data Contributor" \
     --assignee $PRINCIPAL_ID \
     --scope "<your-cosmos-db-resource-id>"
   ```

4. **Update Container App to remove API keys:**

   ```bash
   az containerapp update \
     --name $CONTAINER_APP_NAME \
     --resource-group $RESOURCE_GROUP \
     --remove-env-vars AZURE_OPENAI_API_KEY COSMOS_DB_KEY
   ```

#### Step 6: Verify Deployment

1. **Get the application URL:**

   ```bash
   FQDN=$(az containerapp show \
     --name $CONTAINER_APP_NAME \
     --resource-group $RESOURCE_GROUP \
     --query properties.configuration.ingress.fqdn \
     --output tsv)
   
   echo "Application URL: https://$FQDN"
   ```

2. **Check application health:**

   ```bash
   curl -f https://$FQDN/health
   ```

3. **View application logs:**

   ```bash
   az containerapp logs show \
     --name $CONTAINER_APP_NAME \
     --resource-group $RESOURCE_GROUP \
     --follow
   ```

### Security Best Practices

- **Use Managed Identity**: Always prefer managed identity over API keys for authentication
- **Secure Secrets**: Store sensitive configuration in Azure Key Vault
- **Network Security**: Consider using private endpoints for database connections
- **Resource Isolation**: Deploy to a dedicated resource group for easier management
- **Monitoring**: Enable Application Insights for monitoring and diagnostics

### Troubleshooting

- **Container App not starting**: Check logs using `az containerapp logs show`
- **Authentication issues**: Verify managed identity permissions and role assignments
- **Network connectivity**: Ensure firewall rules allow Container Apps to access resources
- **Resource limits**: Monitor CPU and memory usage, adjust scaling parameters if needed

### Cost Optimization

- **Right-size resources**: Start with minimal CPU/memory and scale based on usage
- **Auto-scaling**: Configure appropriate min/max replicas based on expected load
- **Resource cleanup**: Use `az group delete` to remove all resources when no longer needed