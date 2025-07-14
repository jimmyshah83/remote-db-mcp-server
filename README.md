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