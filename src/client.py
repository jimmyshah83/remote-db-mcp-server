"""LangChain-powered MCP client with Azure OpenAI and ReAct agent integration."""

import asyncio
import logging
import os
from typing import List, cast
from contextlib import AsyncExitStack

from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool, tool
from langchain_core.runnables import RunnableConfig
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import StdioConnection
from langchain_openai import AzureChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

load_dotenv()

memory = MemorySaver()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("cosmos_mcp_client")

class MCPClient:
	"""LangChain-powered MCP client with Azure OpenAI and ReAct agent integration."""

	def __init__(self):
		# Initialize MultiServerMCPClient with StdioConnection
		self.mcp_client = MultiServerMCPClient(
			{
				"local": StdioConnection(
					transport="stdio",
					command="python3",
					args=["src/server.py"],
					env=None,
					cwd=None,
					encoding="utf-8",
					encoding_error_handler="strict",
					session_kwargs=None
				)
			}
		)
		self.exit_stack = AsyncExitStack()

		# Initialize Azure OpenAI
		self.llm = AzureChatOpenAI(
			azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
			api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
			temperature=0
		)

		self.tools: List[BaseTool] = []
		self.agent = None
		
		# System instruction for the agent
		self.system_instruction = """You are a helpful AI assistant that can interact with various tools and services. Use the available tools to help users with their requests. Always provide clear and helpful responses.
		You have the following tools available:
		{tools}
		"""

	async def connect_to_server(self):
		"""Connect to the MCP server
		"""
		# Get the tools from the MCP client
		self.tools = await self.mcp_client.get_tools()

		# Create ReAct agent using the new tooling logic
		self.agent = await self._create_azure_mcp_agent()

		print("\nConnected to server with tools:", [tool.name + ": " + tool.description for tool in self.tools])

	async def get_tools(self) -> List[BaseTool]:
		"""Get the available MCP tools"""
		return self.tools

	async def _create_azure_mcp_agent(self):
		"""
		Creates and returns an agent that interacts with Azure MCP server.
		Returns:
			azure_mcp_agent: The created agent.
		"""
		logger.info("Creating Azure MCP Agent")
		langchain_mcp_tools = await self.get_tools()

		sync_tools = []
		for mcp_tool in langchain_mcp_tools:
			logger.info("Available Langchain MCP tool: %s", mcp_tool.name)

			@tool()
			async def sync_tool(input_text: str, mcp_tool=mcp_tool):
				"""Execute the MCP tool with the given input."""
				result = await mcp_tool.ainvoke({"input": input_text})
				return str(result)

			sync_tools.append(sync_tool)

		azure_mcp_agent = create_react_agent(
			self.llm,
			tools=sync_tools,
			prompt=self.system_instruction,
		)
		return azure_mcp_agent

	async def process_query(self, query: str) -> str:
		"""Process a query using LangChain ReAct agent and available tools"""
		if not self.agent:
			return "Error: Agent not initialized. Please connect to server first."

		try:
			# Run the agent with the new message format
			context_id = "demo-thread-1"
			config = cast(RunnableConfig, {'configurable': {'thread_id': context_id}})
			result = await self.agent.ainvoke(
				{"messages": [("user", query)]},
				config=config
			)

			# Extract the final response
			if result and "messages" in result:
				messages = result["messages"]
				if messages:
					# Get the last AI message
					for message in reversed(messages):
						if isinstance(message, AIMessage):
							content = message.content
							if isinstance(content, str):
								return content
							elif isinstance(content, list):
								# Handle list content
								return str(content[0]) if content else ""
							else:
								return str(content)

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
	"""Main function to run the MCP client"""
	client = MCPClient()
	try:
		await client.connect_to_server()
		await client.chat_loop()
	finally:	
		await client.cleanup()

if __name__ == "__main__":
	asyncio.run(main())
