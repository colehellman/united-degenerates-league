import subprocess
import sys
from fastapi import FastAPI, HTTPException

app = FastAPI(
    title="MCP Server",
    description="A server to execute Playwright scripts for Gemini Code Assist.",
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the MCP Server"}

@app.post("/run-playwright")
def run_playwright():
    try:
        # Ensure we are using the same python interpreter
        # that is running the server.
        python_executable = sys.executable
        script_path = "mcp_server/playwright_script.py"
        result = subprocess.run(
            [python_executable, script_path],
            capture_output=True,
            text=True,
            check=True,
        )
        return {
            "message": "Playwright script executed successfully.",
            "output": result.stdout,
            "screenshot": "example.png"
        }
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Playwright script failed: {e.stderr}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}",
        )

@app.post("/run-tests")
def run_tests():
    try:
        python_executable = sys.executable
        result = subprocess.run(
            [python_executable, "-m", "pytest"],
            capture_output=True,
            text=True,
            cwd="backend",  # Run pytest in the backend directory
        )
        return {
            "message": "Tests executed.",
            "exit_code": result.returncode,
            "output": result.stdout + result.stderr,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}",
        )
