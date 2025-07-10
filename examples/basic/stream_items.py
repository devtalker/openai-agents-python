"""
Stream Items Example with Custom Model Configuration

This example demonstrates how to use streaming events with a custom model provider.
Before running this example, you need to create a .env file in this directory with the following variables:

MODEL_API_KEY=your_api_key_here
MODEL_BASE_URL=https://api.openai.com/v1  
MODEL_NAME=gpt-4o-mini

Example configurations for different providers:

OpenAI:
MODEL_API_KEY=sk-your-openai-api-key
MODEL_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4o-mini

Azure OpenAI:
MODEL_API_KEY=your-azure-api-key
MODEL_BASE_URL=https://your-resource.openai.azure.com/openai/deployments/your-deployment-name
MODEL_NAME=gpt-4

Anthropic Claude (via compatible API):
MODEL_API_KEY=your-claude-api-key
MODEL_BASE_URL=https://api.anthropic.com/v1
MODEL_NAME=claude-3-sonnet-20240229
"""

import asyncio
import random
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

from agents import Agent, ItemHelpers, Runner, function_tool, Model, ModelProvider, OpenAIChatCompletionsModel, RunConfig
from agents.tracing import set_tracing_disabled

# Load environment variables
load_dotenv()
set_tracing_disabled(disabled=True)

# Get configuration from environment variables
MODEL_API_KEY = os.getenv("MODEL_API_KEY")
MODEL_BASE_URL = os.getenv("MODEL_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME")

# Create custom OpenAI client
client = AsyncOpenAI(
    api_key=MODEL_API_KEY,
    base_url=MODEL_BASE_URL,
)


class CustomModelProvider(ModelProvider):
    """自定义模型提供器"""

    def get_model(self, model_name: str | None) -> Model:
        return OpenAIChatCompletionsModel(
            model=model_name or MODEL_NAME,
            openai_client=client,
        )


CUSTOM_MODEL_PROVIDER = CustomModelProvider()


@function_tool
def how_many_jokes() -> int:
    return random.randint(1, 10)


async def main():
    agent = Agent(
        name="Joker",
        instructions="First call the `how_many_jokes` tool, then tell that many jokes.",
        tools=[how_many_jokes],
    )

    result = Runner.run_streamed(
        agent,
        input="Hello",
        run_config=RunConfig(model_provider=CUSTOM_MODEL_PROVIDER),
    )
    print("=== Run starting ===")
    async for event in result.stream_events():
        # We'll ignore the raw responses event deltas
        if event.type == "raw_response_event":
            continue
        elif event.type == "agent_updated_stream_event":
            print(f"Agent updated: {event.new_agent.name}")
            continue
        elif event.type == "run_item_stream_event":
            if event.item.type == "tool_call_item":
                print("-- Tool was called")
            elif event.item.type == "tool_call_output_item":
                print(f"-- Tool output: {event.item.output}")
            elif event.item.type == "message_output_item":
                print(f"-- Message output:\n {ItemHelpers.text_message_output(event.item)}")
            else:
                pass  # Ignore other event types

    print("=== Run complete ===")


if __name__ == "__main__":
    # Check if required environment variables are set
    if not MODEL_API_KEY or not MODEL_BASE_URL or not MODEL_NAME:
        print("Error: Please set MODEL_API_KEY, MODEL_BASE_URL, and MODEL_NAME in your .env file")
        exit(1)
    
    asyncio.run(main())

    # === Run starting ===
    # Agent updated: Joker
    # -- Tool was called
    # -- Tool output: 4
    # -- Message output:
    #  Sure, here are four jokes for you:

    # 1. **Why don't skeletons fight each other?**
    #    They don't have the guts!

    # 2. **What do you call fake spaghetti?**
    #    An impasta!

    # 3. **Why did the scarecrow win an award?**
    #    Because he was outstanding in his field!

    # 4. **Why did the bicycle fall over?**
    #    Because it was two-tired!
    # === Run complete ===
