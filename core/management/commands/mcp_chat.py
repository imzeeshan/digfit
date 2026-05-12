"""
Interactive chat that lets a local Ollama model call your DigFit API via MCP.

Usage:
    python manage.py mcp_chat
    python manage.py mcp_chat --model gemma3:4b
    python manage.py mcp_chat --base-url http://localhost:8000

Requires a tool-calling model (gemma3:4b, llama3.1, qwen2.5, mistral, etc.).
"""

import json

import httpx
from django.conf import settings
from django.core.management.base import BaseCommand

from core.ollama_client import get_client


def _mcp_headers() -> dict[str, str]:
    """Return auth headers containing the MCP internal token."""
    from django_drf_mcp.tokens import HEADER_NAME, get_token
    return {HEADER_NAME: get_token()}


def _fetch_mcp_tools(base_url: str) -> list[dict]:
    """Call MCP tools/list and return the raw tool definitions."""
    resp = httpx.post(
        f"{base_url}/mcp/",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        headers=_mcp_headers(),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["result"]["tools"]


def _call_mcp_tool(base_url: str, name: str, arguments: dict) -> str:
    """Execute a single MCP tool call and return the text result."""
    resp = httpx.post(
        f"{base_url}/mcp/",
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
        headers=_mcp_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    content = resp.json()["result"]["content"]
    return "\n".join(c.get("text", "") for c in content)


def _mcp_to_ollama_tools(mcp_tools: list[dict]) -> list[dict]:
    """Convert MCP tool definitions to Ollama's tool-calling format."""
    ollama_tools = []
    for t in mcp_tools:
        schema = t.get("inputSchema", {})
        ollama_tools.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": schema,
            },
        })
    return ollama_tools


class Command(BaseCommand):
    help = "Chat with Ollama using DigFit MCP tools (API-backed function calling)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            default="gemma4:e4b",
            help="Ollama model with tool-calling support (default: gemma4:e4b)",
        )
        parser.add_argument(
            "--base-url",
            default=None,
            help="Django server URL (default: from DJANGO_MCP settings)",
        )

    def handle(self, *args, **options):
        model = options["model"]
        base_url = (
            options["base_url"]
            or getattr(settings, "DJANGO_MCP", {}).get("BASE_URL", "http://localhost:8000")
        )

        self.stdout.write(f"Ollama model : {model}")
        self.stdout.write(f"Django server: {base_url}")
        self.stdout.write("Fetching MCP tools...")

        try:
            mcp_tools = _fetch_mcp_tools(base_url)
        except Exception as exc:
            self.stderr.write(self.style.ERROR(
                f"Could not reach MCP at {base_url}/mcp/ — is the Django server running?\n{exc}"
            ))
            raise SystemExit(1) from exc

        ollama_tools = _mcp_to_ollama_tools(mcp_tools)
        tool_names = [t["function"]["name"] for t in ollama_tools]
        self.stdout.write(self.style.SUCCESS(f"Loaded {len(tool_names)} tools: {', '.join(tool_names)}"))
        self.stdout.write("Type your message (Ctrl+C to quit):\n")

        client = get_client()
        messages: list[dict] = [
            {
                "role": "system",
                "content": (
                    "You are a helpful fitness and health assistant for DigFit. "
                    "You have access to the DigFit API tools. Use them to look up "
                    "and manage user data (weights, meal plans, interventions, etc.). "
                    "Always confirm before creating or deleting records."
                ),
            }
        ]

        while True:
            try:
                user_input = input("\n> ").strip()
            except (KeyboardInterrupt, EOFError):
                self.stdout.write("\nBye!")
                break
            if not user_input:
                continue

            messages.append({"role": "user", "content": user_input})
            response = self._tool_loop(client, model, messages, ollama_tools, base_url)
            self.stdout.write(f"\n{self.style.SUCCESS('Assistant')}: {response}")

    def _tool_loop(
        self, client, model: str, messages: list[dict],
        tools: list[dict], base_url: str, max_rounds: int = 5,
    ) -> str:
        """Run the chat -> tool-call -> result loop until the model gives a final answer."""
        for _ in range(max_rounds):
            resp = client.chat(model=model, messages=messages, tools=tools)

            if not resp.message.tool_calls:
                text = resp.message.content or ""
                messages.append({"role": "assistant", "content": text})
                return text

            messages.append(resp.message)

            for tc in resp.message.tool_calls:
                fn_name = tc.function.name
                fn_args = tc.function.arguments
                self.stdout.write(
                    f"  {self.style.WARNING('Tool call')}: {fn_name}({json.dumps(fn_args, indent=2)})"
                )

                try:
                    result = _call_mcp_tool(base_url, fn_name, fn_args)
                except Exception as exc:
                    result = f"Error: {exc}"

                self.stdout.write(f"  {self.style.HTTP_INFO('Result')}: {result[:500]}")
                messages.append({"role": "tool", "content": result})

        return "(max tool-call rounds reached)"
