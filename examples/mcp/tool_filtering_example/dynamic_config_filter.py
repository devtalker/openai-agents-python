import asyncio
import os
import shutil
from dotenv import load_dotenv
from agents import (
    Agent,
    Runner,
    ModelProvider,
    OpenAIChatCompletionsModel,
    RunConfig,
    set_tracing_disabled,
    RunContextWrapper
)
from agents.mcp import MCPServerStdio, ToolFilterContext
from agents.model_settings import ModelSettings

# Load environment variables from .env file
load_dotenv()

BASE_URL = os.getenv("MODEL_BASE_URL")
API_KEY = os.getenv("MODEL_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o")

class CustomModelProvider(ModelProvider):
    def __init__(self, base_url: str | None, api_key: str | None, default_model: str):
        self.base_url = base_url
        self.api_key = api_key
        self.default_model = default_model
        if base_url and api_key:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
            print(f"Using custom model provider: {base_url}")
        else:
            self.client = None
            print("Using default OpenAI model provider")
    def get_model(self, model_name: str | None):
        model_to_use = model_name or self.default_model
        if self.client:
            return OpenAIChatCompletionsModel(model=model_to_use, openai_client=self.client)
        else:
            return OpenAIChatCompletionsModel(model=model_to_use)

def context_aware_filter(context: ToolFilterContext, tool) -> bool:
    """Context-aware tool filter based on agent role."""
    agent_name = context.agent.name
    # ReadOnlyAgent: only allow read_ and list_ tools
    if agent_name == "ReadOnlyAgent":
        return tool.name.startswith("read_") or tool.name.startswith("list_")
    # AdminAgent: allow all tools
    if agent_name == "AdminAgent":
        return True
    # BasicAgent: only allow specific basic tools
    if agent_name == "BasicAgent":
        return tool.name in ["read_file", "list_directory"]
    # Default: deny all
    return False

async def print_agent_tools(agent: Agent, run_context: RunContextWrapper):
    tools = await agent.get_all_tools(run_context)
    tool_names = [tool.name for tool in tools]
    print(f"Agent '{agent.name}' available tools: {tool_names}")

async def run_agent(agent: Agent, model_provider: ModelProvider, message: str):
    print(f"\n=== Agent: {agent.name} ===")
    # Print available tools
    run_context = RunContextWrapper(context=None)
    await print_agent_tools(agent, run_context)
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

async def main():
    model_provider = CustomModelProvider(
        base_url=BASE_URL,
        api_key=API_KEY,
        default_model=MODEL_NAME
    )
    if BASE_URL and API_KEY:
        set_tracing_disabled(True)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    samples_dir = os.path.join(parent_dir, "filesystem_example", "sample_files")
    if not os.path.exists(samples_dir):
        os.makedirs(samples_dir)
        with open(os.path.join(samples_dir, "example.txt"), "w") as f:
            f.write("This is a sample file.")
    print("=== Context-aware dynamic tool filtering example ===")
    print("Dynamically determine available tools based on agent role\n")
    async with MCPServerStdio(
        name="Filesystem server with context-aware filtering",
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", samples_dir],
        },
        tool_filter=context_aware_filter,
    ) as server:
        # Three agents with different roles
        agents = [
            Agent(
                name="ReadOnlyAgent",
                instructions="Can only read and list files.",
                mcp_servers=[server],
                model_settings=ModelSettings(temperature=0.7),
            ),
            Agent(
                name="AdminAgent",
                instructions="Has all file operation permissions.",
                mcp_servers=[server],
                model_settings=ModelSettings(temperature=0.7),
            ),
            Agent(
                name="BasicAgent",
                instructions="Can only perform basic file reading and directory listing operations.",
                mcp_servers=[server],
                model_settings=ModelSettings(temperature=0.7),
            ),
        ]
        # Each agent tries different operations
        for agent in agents:
            await run_agent(agent, model_provider, "List all available files.")
            await run_agent(agent, model_provider, "Delete a file.")
            await run_agent(agent, model_provider, "Write to a file.")

if __name__ == "__main__":
    if not shutil.which("npx"):
        raise RuntimeError(
            "npx is not installed. Please install Node.js and npm: https://nodejs.org/"
        )
    print(f"Model configuration:")
    print(f"- MODEL_NAME: {MODEL_NAME}")
    print(f"- MODEL_BASE_URL: {'configured' if BASE_URL else 'not configured'}")
    print(f"- MODEL_API_KEY: {'configured' if API_KEY else 'not configured'}")
    print()
    asyncio.run(main())
