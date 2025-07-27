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

## Deploying to Azure Container Apps

You can deploy the MCP server (`src/server.py`) as a standalone application to Azure Container Apps. Follow these steps:

### 1. Create a Dockerfile

Add a `Dockerfile` to your project root:

```dockerfile
FROM mcr.microsoft.com/azure-functions/python:4-python3.11
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install poetry && poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi
COPY . .
EXPOSE 8000
ENV PYTHONUNBUFFERED=1
CMD ["python", "src/server.py"]
```

If you use `requirements.txt` instead of Poetry, adjust the Dockerfile accordingly.

### 2. Build and Push the Docker Image

Replace `<your-registry>` and `<your-image-name>` as needed:

```bash
# Log in to Azure Container Registry (ACR) or Docker Hub
az acr login --name <your-registry>
# or
docker login

# Build the image
docker build -t <your-registry>/<your-image-name>:latest .

# Push the image
docker push <your-registry>/<your-image-name>:latest

# run locally
docker run -p 8000:8000 \
  -v $(pwd)/.env:/app/.env \
  remote-db-mcp-server
```


### 3. Deploy to Azure Container Apps

```bash
# Create a resource group (if needed)
az group create --name myResourceGroup --location eastus

# Create a Container App environment
az containerapp env create --name my-environment --resource-group myResourceGroup --location eastus

# Create the Container App (Make sure to add your environment variables)
az containerapp create \
  --name my-mcp-server \
  --resource-group myResourceGroup \
  --environment my-environment \
  --image <your-registry>/<your-image-name>:latest \
  --target-port 8000 \
  --ingress 'external' \
  --env-vars COSMOS_ENDPOINT=<your-cosmos-endpoint> \
               COSMOS_DATABASE=<your-db-name> \
               COSMOS_CONTAINER=<your-container-name> \
               AZURE_OPENAI_DEPLOYMENT_NAME=<your-openai-deployment> \
               AZURE_OPENAI_API_VERSION=<your-openai-api-version>
```

### 4. (Optional) Set up Azure Managed Identity

If your code uses `DefaultAzureCredential`, assign a managed identity to your Container App and grant it access to Cosmos DB and Azure OpenAI.

### 5. Verify Deployment

Get the external URL:

```bash
az containerapp show --name my-mcp-server --resource-group myResourceGroup --query properties.configuration.ingress.fqdn
```

Visit the URL to test your deployed MCP server.