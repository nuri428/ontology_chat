from typing import Any, Dict, List, Protocol, runtime_checkable

@runtime_checkable
class MCPTool(Protocol):
    name: str
    description: str

    async def call(self, **kwargs) -> Dict[str, Any]:
        ...

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, MCPTool] = {}

    def register(self, tool: MCPTool):
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def list_tools(self) -> List[Dict[str, Any]]:
        return [{"name": t.name, "description": t.description} for t in self._tools.values()]

    def get(self, name: str) -> MCPTool:
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")
        return self._tools[name]

registry = ToolRegistry()