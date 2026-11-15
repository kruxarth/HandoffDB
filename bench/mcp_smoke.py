"""Drive the Bearings MCP server over stdio: list tools, get a pack, report a task.
  uv run python bench/mcp_smoke.py [team] [repo]
"""
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def main(team: str, repo: str) -> None:
    params = StdioServerParameters(command="uv", args=["run", "--quiet", "--directory", str(ROOT), "bearings-mcp"],
                                   env={**os.environ, "BEARINGS_TEAM": team, "BEARINGS_REPO": repo})
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            print("tools:", [t.name for t in tools.tools])
            task = "QuerySet.bulk_create() crashes on mixed case columns in unique_fields/update_fields"
            res = await s.call_tool("get_context_pack", {"task": task})
            print(res.content[0].text)
            if "--report" in sys.argv:
                res = await s.call_tool("report_task", {"task": task, "changed_files": ["django/db/models/sql/compiler.py"],
                                                        "read_files": ["django/db/models/query.py"], "passed": True})
                print(res.content[0].text)


asyncio.run(main(*(a for a in sys.argv[1:3] if not a.startswith("--")) if len(sys.argv) > 2 else ("bench", "django-tasks")))
