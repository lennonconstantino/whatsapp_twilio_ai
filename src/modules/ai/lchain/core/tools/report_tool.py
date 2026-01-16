from typing import Type
from pydantic import BaseModel


from src.modules.ai.lchain.core.tools.tool import Tool
from src.modules.ai.lchain.core.models.tool_result import ToolResult
from src.modules.ai.lchain.core.models.report_schema import ReportSchema

class ReportTool(Tool):
    name: str = "report_tool"
    description: str = "Report the results of your work or answer user questions"
    args_schema: Type[BaseModel] = ReportSchema
    model: Type[BaseModel] = ReportSchema
    parse_model: bool = True 
    
    def _run(self, **kwargs) -> ToolResult:
        return super()._run(**kwargs)
    
    async def _arun(self, **kwargs) -> ToolResult:
        return self._run(**kwargs)
    
    def execute(self, input_data) -> str:
        return ReportSchema.report_function(input_data)

report_tool = ReportTool()