# MCP Tool Filtering Example

This example demonstrates how to use the tool filtering feature of the MCP server, including both static and dynamic filtering. It also shows how to read custom model configuration from environment variables.

## How to Run

Basic example (static and simple dynamic filtering):
```bash
uv run python examples/mcp/tool_filtering_example/main.py
```

Context-aware dynamic filtering example:
```bash
uv run python examples/mcp/tool_filtering_example/dynamic_config_filter.py
```

## Custom Model Configuration

This example supports reading custom model configuration from environment variables:

```bash
# Set environment variables
export MODEL_BASE_URL="https://your-custom-model-endpoint.com/v1"
export MODEL_API_KEY="your-api-key"
export MODEL_NAME="your-model-name"

# Run the example
uv run python examples/mcp/tool_filtering_example/main.py
```

If these environment variables are not set, the example will use the default OpenAI model (gpt-4o).

## Example Details

This example uses the `MCPServerStdio` class from `agents.mcp` and the [filesystem MCP server](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem), running locally via `npx`.

The example is divided into three parts:

### 1. Static Tool Filtering (main.py)

Uses the `create_static_tool_filter` function to create a static tool filter, configured with:
- `allowed_tool_names`: List of allowed tools (whitelist)
- `blocked_tool_names`: List of blocked tools (blacklist)

In this example:
- `read_file`, `list_directory`, and `write_file` tools are allowed
- `delete_file` tool is blocked

### 2. Simple Dynamic Tool Filtering (main.py)

Implements a custom function for dynamic tool filtering, which can filter based on:
- Tool name
- Context information (run context, agent, server name, etc.)
- Other custom logic

In this example, we create a filter that only allows tools starting with `read_` or `list_`.

### 3. Context-Aware Dynamic Filtering (dynamic_config_filter.py)

This advanced example demonstrates how to dynamically filter tools based on the agent's role and context information:

- **ReadOnlyAgent**: Can only access tools starting with `read_` or `list_`
- **AdminAgent**: Can access all tools
- **BasicAgent**: Can only access specific basic tools (`read_file`, `list_directory`)

This example shows how to implement role-based tool access control in a multi-agent system.

## How It Works

1. The MCP server is started as a subprocess, providing file system related tools such as `list_directory()`, `read_file()`, `write_file()`, `delete_file()`, etc.
2. The `tool_filter` parameter is used to configure the tool filter
3. Each time an agent runs, the system calls the MCP server to get the tool list and applies the filter
4. If the LLM tries to use a tool that is filtered out, it will not be able to access that tool

## Filter Processing Order

When both `allowed_tool_names` and `blocked_tool_names` are configured, the processing order is:
1. Apply `allowed_tool_names` (whitelist) first - only keep specified tools
2. Then apply `blocked_tool_names` (blacklist) - remove specified tools from the remaining list

## Async Filters

Dynamic filters can be either synchronous or asynchronous functions. If you need to perform async operations (such as database queries or API calls) during filtering, you can define the filter function with `async def`. 