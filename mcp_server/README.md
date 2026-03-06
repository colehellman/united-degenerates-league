# MCP Server

This server extends Gemini Code Assist with Playwright capabilities. It allows the AI assistant to run browser automation scripts.

## Setup

1.  Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Install Playwright browsers:
    ```bash
    playwright install
    ```
3.  Run the server:
    ```bash
    uvicorn main:app --reload
    ```

## Configuration

To use this server with Gemini Code Assist, you need to add it to your IDE's settings. For example, in VS Code, you would add the following to your `.vscode/settings.json` file:

```json
{
    "google.gemini.experimental.mcp.server": {
        "command": ["uvicorn", "main:app", "--port=8001"],
        "cwd": "${workspaceFolder}/mcp_server",
        "startupTimeout": 30,
        "http": {
          "baseUrl": "http://localhost:8001"
        }
    }
}
```
