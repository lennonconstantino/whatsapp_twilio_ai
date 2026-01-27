import json
from datetime import datetime
from typing import List, Optional

import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from src.modules.ai.engines.lchain.core.utils.utils import (
    convert_langchain_to_openai_tool, convert_pydantic_to_openai_function,
    convert_to_langchain_tool, date_to_string, generate_query_context,
    get_tool_from_response, parse_date, parse_function_args,
    pydantic_model_to_string, run_tool_from_response, weekday_by_date)


class MockTool(BaseTool):
    name: str = "test_tool"
    description: str = "Test tool"

    def _run(self, query: str):
        return f"Ran with {query}"


class TestUtils:

    def test_parse_function_args_dict(self):
        response = AIMessage(
            content="",
            tool_calls=[{"name": "test", "args": {"arg1": "val1"}, "id": "1"}],
        )
        args = parse_function_args(response)
        assert args == {"arg1": "val1"}

    def test_parse_function_args_attribute(self):
        response = AIMessage(content="no tool calls")
        assert parse_function_args(response) == {}

    def test_get_tool_from_response_success(self):
        tool = MockTool()
        response = AIMessage(
            content="", tool_calls=[{"name": "test_tool", "args": {}, "id": "1"}]
        )
        found_tool = get_tool_from_response(response, [tool])
        assert found_tool == tool

    def test_get_tool_from_response_failure(self):
        tool = MockTool()
        response = AIMessage(
            content="", tool_calls=[{"name": "unknown", "args": {}, "id": "1"}]
        )
        with pytest.raises(ValueError):
            get_tool_from_response(response, [tool])

    def test_run_tool_from_response(self):
        tool = MockTool()
        response = AIMessage(
            content="",
            tool_calls=[{"name": "test_tool", "args": {"query": "hello"}, "id": "1"}],
        )
        result = run_tool_from_response(response, [tool])
        assert result == "Ran with hello"

    def test_date_utils(self):
        dt = datetime(2023, 10, 27)  # Friday
        assert weekday_by_date(dt) == "Friday"
        assert parse_date(dt) == "2023-10-27"
        assert date_to_string(dt) == "Friday 2023-10-27"

    def test_pydantic_model_to_string(self):
        class TestModel(BaseModel):
            id: int
            name: str
            optional: Optional[str] = None
            tags: List[str]

        s = pydantic_model_to_string(TestModel)
        # Check components because order might vary or format might change
        assert "id = <int>" in s
        assert "name = <str>" in s
        assert "optional = <str>" in s
        assert "tags = <List>" in s or "tags = <list>" in s

    def test_generate_query_context(self):
        class Table1(BaseModel):
            id: int

        class Table2(BaseModel):
            name: str

        ctx = generate_query_context(Table1, Table2)
        assert "table1" in ctx
        assert "table2" in ctx
        assert "id = <int>" in ctx
        assert "name = <str>" in ctx

    def test_convert_to_langchain_tool(self):
        class Args(BaseModel):
            """Args description"""

            query: str = Field(description="Query string")

        tool = convert_to_langchain_tool(
            Args, name="MyTool", description="My Description"
        )
        assert tool["function"]["name"] == "MyTool"
        assert tool["function"]["description"] == "My Description"
        assert "query" in tool["function"]["parameters"]["properties"]

    def test_convert_langchain_to_openai_tool(self):
        tool = MockTool()
        openai_tool = convert_langchain_to_openai_tool(tool)
        assert openai_tool["function"]["name"] == "test_tool"
