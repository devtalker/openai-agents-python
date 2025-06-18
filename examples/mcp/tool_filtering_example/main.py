import asyncio
import os
import shutil
from typing import Any
import logging

from dotenv import load_dotenv
from openai import AsyncOpenAI

from agents import (
    Agent, 
    Runner, 
    OpenAIChatCompletionsModel,
    ModelProvider,
    Model,
    RunConfig,
    set_tracing_disabled
)
from agents.mcp import MCPServer, MCPServerStdio, ToolFilterContext, create_static_tool_filter
from agents.model_settings import ModelSettings

# Load environment variables from .env file
load_dotenv()

# Read custom model configuration from environment variables
BASE_URL = os.getenv("MODEL_BASE_URL")
API_KEY = os.getenv("MODEL_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o")

print(f"BASE_URL: {BASE_URL}")
print(f"API_KEY: {API_KEY}")
print(f"MODEL_NAME: {MODEL_NAME}")

# Create custom model provider
class CustomModelProvider(ModelProvider):
    def __init__(self, base_url: str | None, api_key: str | None, default_model: str):
        self.base_url = base_url
        self.api_key = api_key
        self.default_model = default_model
        
        # If base_url and api_key are provided, create custom client
        if base_url and api_key:
            self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
            print(f"Using custom model provider: {base_url}")
        else:
            self.client = None
            print("Using default OpenAI model provider")
    
    def get_model(self, model_name: str | None) -> Model:
        model_to_use = model_name or self.default_model
        if self.client:
            return OpenAIChatCompletionsModel(model=model_to_use, openai_client=self.client)
        else:
            return OpenAIChatCompletionsModel(model=model_to_use)


async def run_with_static_filter(mcp_server: MCPServer, model_provider: ModelProvider):
    """Run example using static filter"""
    agent = Agent(
        name="Assistant",
        instructions="Use tools to read the file system and answer questions based on these files.",
        mcp_servers=[mcp_server],
        model_settings=ModelSettings(temperature=0.7),  # Set model parameters
    )

    # tools = await agent.get_all_tools()
    # print(f"static agent tools: {tools}")

    # List readable files
    message = "Read and list available files."
    print(f"Running: {message}")
    try:
        result = await Runner.run(
            starting_agent=agent, 
            input=message,
            run_config=RunConfig(model_provider=model_provider)
        )
        print(result.final_output)
    except Exception as e:
        import traceback
        print("Exception occurred:", e)
        traceback.print_exc()
        # Print underlying cause
        cause = getattr(e, '__cause__', None)
        if cause:
            print("Underlying cause:", repr(cause))
            # If there's a deeper cause, can recursively print
            subcause = getattr(cause, '__cause__', None)
            if subcause:
                print("Deeper cause:", repr(subcause))

    # Try to use filtered out tool
    message = "Delete a file."
    print(f"\n\nRunning: {message}")
    try:
        result = await Runner.run(
            starting_agent=agent, 
            input=message,
            run_config=RunConfig(model_provider=model_provider)
        )
        print(result.final_output)
    except Exception as e:
        print("Exception occurred:", e)
        # traceback.print_exc()


async def run_with_dynamic_filter(mcp_server: MCPServer, model_provider: ModelProvider):
    """Run example using dynamic filter"""
    agent = Agent(
        name="Assistant",
        instructions="Use tools to read the file system and answer questions based on these files.",
        mcp_servers=[mcp_server],
        model_settings=ModelSettings(temperature=0.7),  # Set model parameters
    )

    tools = await agent.get_all_tools()
    print(f"dynamic agent tools: {tools}")

    # List readable files
    message = "Read and list available files."
    print(f"Running: {message}")
    try:
        result = await Runner.run(
            starting_agent=agent, 
            input=message,
            run_config=RunConfig(model_provider=model_provider)
        )
        print(result.final_output)
    except Exception as e:
        import traceback
        print("Exception occurred:", e)
        traceback.print_exc()

    # Try to use filtered out tool
    message = "Write to a file."
    print(f"\n\nRunning: {message}")
    try:
        result = await Runner.run(
            starting_agent=agent, 
            input=message,
            run_config=RunConfig(model_provider=model_provider)
        )
        print(result.final_output)
    except Exception as e:
        import traceback
        print("Exception occurred:", e)
        traceback.print_exc()


async def main():
    # Create custom model provider
    model_provider = CustomModelProvider(
        base_url=BASE_URL,
        api_key=API_KEY,
        default_model=MODEL_NAME
    )
    
    # May need to disable tracing if using custom model provider
    if BASE_URL and API_KEY:
        set_tracing_disabled(True)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    samples_dir = os.path.join(parent_dir, "filesystem_example", "sample_files")

    # Create sample directory (if it doesn't exist)
    if not os.path.exists(samples_dir):
        os.makedirs(samples_dir)
        with open(os.path.join(samples_dir, "example.txt"), "w") as f:
            f.write("This is a sample file.")

    print("=== Example 1: Static Tool Filtering ===")
    print("Only allow read_file and list_directory tools, block delete_file tool")
    
    async with MCPServerStdio(
        name="Filesystem server with static filtering",
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", samples_dir],
        },
        tool_filter=create_static_tool_filter(
            # allowed_tool_names=["read_file", "list_directory", "write_file", "delete_file"],
            blocked_tool_names=["delete_file"]
        ),
    ) as server:
        tools = await server.list_tools()
        tool_names = [tool.name for tool in tools]
        print(f"server tools: {tool_names}")

        await run_with_static_filter(server, model_provider)

    print("\n\n=== Example 2: Dynamic Tool Filtering ===")
    print("Use custom function to filter tools, only allow tools starting with 'read_' or 'list_'")

    # Define dynamic tool filter function
    def custom_filter(context: ToolFilterContext, tool) -> bool:
        """Custom tool filter function that only allows read and list operations"""
        # Only allow tools starting with 'read_' or 'list_'
        return tool.name.startswith("read_") or tool.name.startswith("list_")

    async with MCPServerStdio(
        name="Filesystem server with dynamic filtering",
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", samples_dir],
        },
        tool_filter=custom_filter,
    ) as server:
        tools = await server.list_tools() 
        tool_names = [tool.name for tool in tools]
        print(f"server tools: {tool_names}")

        await run_with_dynamic_filter(server, model_provider)


if __name__ == "__main__":
    # Ensure user has npx installed
    if not shutil.which("npx"):
        raise RuntimeError(
            "npx is not installed. Please install Node.js and npm: https://nodejs.org/"
        )

    # Print model configuration information
    print(f"Model configuration:")
    print(f"- MODEL_NAME: {MODEL_NAME}")
    print(f"- MODEL_BASE_URL: {'configured' if BASE_URL else 'not configured'}")
    print(f"- MODEL_API_KEY: {'configured' if API_KEY else 'not configured'}")
    print()

    # logging.basicConfig(level=logging.DEBUG)
    # logging.getLogger("httpx").setLevel(logging.INFO)

    asyncio.run(main())
