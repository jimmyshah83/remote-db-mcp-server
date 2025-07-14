"""LangChain-powered MCP client with Azure OpenAI and ReAct agent integration."""

import asyncio
import sys
import os
from typing import Optional, List
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_openai import AzureChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv

load_dotenv() # load environment variables from .env

class MCPTool(BaseTool):
	"""Wrapper for MCP tools to work with LangChain"""

	def __init__(self, session: ClientSession, tool_name: str, description: str, input_schema: dict):
		# Store session and tool_name before calling super().__init__
		self._session = session
		self._tool_name = tool_name
		
		super().__init__(
			name=tool_name,
			description=description or f"Tool: {tool_name}",
			args_schema=input_schema
		)

	async def _arun(self, **kwargs) -> str:
		"""Async execution of the MCP tool"""
		result = await self._session.call_tool(self._tool_name, kwargs)
		# Handle the result content properly
		if hasattr(result, 'content'):
			if isinstance(result.content, list):
				# If content is a list, join it or take the first element
				return str(result.content[0]) if result.content else ""
			return str(result.content)
		return str(result)

	def _run(self, **kwargs) -> str:
		"""Sync execution - not used but required by BaseTool"""
		raise NotImplementedError("Use async version")

class MCPClient:
	"""LangChain-powered MCP client with Azure OpenAI and ReAct agent integration."""

	def __init__(self):
		# Initialize session and client objects
		self.session: Optional[ClientSession] = None
		self.exit_stack = AsyncExitStack()

		# Initialize Azure OpenAI
		self.llm = AzureChatOpenAI(
			azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
			api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
			temperature=0
		)

		self.tools: List[MCPTool] = []
		self.agent = None

	async def connect_to_server(self, server_script_path: str):
		"""Connect to an MCP server
		
		Args:
		    server_script_path: Path to the server script (.py or .js)
		"""
		is_python = server_script_path.endswith('.py')
		is_js = server_script_path.endswith('.js')
		if not (is_python or is_js):
			raise ValueError("Server script must be a .py or .js file")

		command = "python" if is_python else "node"
		server_params = StdioServerParameters(
			command=command,
			args=[server_script_path],
			env=None
		)

		stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
		self.stdio, self.write = stdio_transport
		self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

		await self.session.initialize()

		# List available tools and create LangChain tool wrappers
		response = await self.session.list_tools()
		self.tools = []

		for tool in response.tools:
			mcp_tool = MCPTool(
				session=self.session,
				tool_name=tool.name,
				description=tool.description or f"Tool: {tool.name}",
				input_schema=tool.inputSchema
			)
			self.tools.append(mcp_tool)

		# Create ReAct agent
		self.agent = create_react_agent(self.llm, self.tools)

		print("\nConnected to server with tools:", [tool.name for tool in self.tools])

	async def process_query(self, query: str) -> str:
		"""Process a query using LangChain ReAct agent and available tools"""
		if not self.agent:
			return "Error: Agent not initialized. Please connect to server first."

		try:
			# Create the agent state
			config = {"configurable": {"thread_id": "default"}}

			# Run the agent
			result = await self.agent.ainvoke(
				{"messages": [HumanMessage(content=query)]},
				config=config
			)

			# Extract the final response
			if result and "messages" in result:
				messages = result["messages"]
				if messages:
					# Get the last AI message
					for message in reversed(messages):
						if isinstance(message, AIMessage):
							return message.content

			return "No response generated"

		except Exception as e:
			return f"Error processing query: {str(e)}"

	async def chat_loop(self):
		"""Run an interactive chat loop"""
		print("\nMCP Client Started!")
		print("Type your queries or 'quit' to exit.")

		while True:
			try:
				query = input("\nQuery: ").strip()

				if query.lower() == 'quit':
					break

				response = await self.process_query(query)
				print("\n" + response)

			except Exception as e:
				print(f"\nError: {str(e)}")

	async def cleanup(self):
		"""Clean up resources"""
		await self.exit_stack.aclose()

async def main():
	if len(sys.argv) < 2:
		print("Usage: python client.py <path_to_server_script>")
		sys.exit(1)

	client = MCPClient()
	try:
		await client.connect_to_server(sys.argv[1])
		await client.chat_loop()
	finally:
		await client.cleanup()

if __name__ == "__main__":
	asyncio.run(main())
