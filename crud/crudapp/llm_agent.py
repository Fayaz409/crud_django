# crudapp/llm_agent.py
import os
import json
from typing import Annotated, List, Dict, Any, TypedDict
from operator import add
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from dotenv import load_dotenv

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages  # Manages adding messages to the state
from pydantic import BaseModel, Field

# Remove ogle.generativeai imports; we now use ChatogleGenerativeAI
#from ogle.generativeai.types import Tool, FunctionDeclaration
#from ogle.generativeai.types import RequestOptions
#from ogle.api_core import retry

# Import tools and ToolResult model
from .agent_tools import find_employee, list_employees, ToolResult
from .agent_logger import agent_logger
from .models import Employee  # For getting field names
load_dotenv()

# --- State Definition ---
# Using standard list of dicts for messages; add_messages handles accumulation
class AgentState(TypedDict):
    """Represents the state of our agent."""
    messages: Annotated[List[Dict[str, Any]], add_messages]

# --- Agent Class ---
class DjanCrudAgent:
    def __init__(self, model_name="models/gemini-2.0-flash", api_key=None):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        print(f"API Key: {self.api_key}")  # Debugging line to check API key
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables or provided.")

        # Instead of using ogle.generativeai, we now use ChatogleGenerativeAI.
        from langchain_ogle_genai import ChatogleGenerativeAI
        self.model = ChatogleGenerativeAI(
            api_key=self.api_key,
            model=self.model_name,
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            # add other parameters as needed...
        )

        self.tools = [
            find_employee,
            list_employees,
        ]
        self.tool_mapping = {tool.__name__: tool for tool in self.tools}

        employee_fields = [f.name for f in Employee._meta.get_fields() if not f.is_relation]
        employee_fields_str = ", ".join(employee_fields)
        countries_str = ", ".join([c[0] for c in Employee.Countries])

        self.system_prompt = (
            f"You are a helpful assistant for managing Employee records in a Djan application database.\n"
            f"The Employee model has the following fields: {employee_fields_str}.\n"
            f"The 'Country' field accepts one of the following values: {countries_str}.\n"
            "Dates (DateOfBirth, HireDate) should be in YYYY-MM-DD format.\n"
            "HasPassport is a boolean (true/false). Salary is an integer.\n\n"
            "Your tasks are:\n"
            "1. Understand user requests to create, update, delete, or list employees.\n"
            "2. Use the available tools to find employees or list all employees when necessary.\n"
            "3. **For CREATE requests:** Extract all the provided details for the new employee. Then, respond with the extracted details and ask the user to confirm before proceeding. Format the details clearly.\n"
            "4. **For UPDATE requests:** First, use the 'find_employee' tool to get the employee's PK (primary key). If found, extract the fields to be updated and their new values. Then, respond with the employee's PK, current identifying information (like name), the proposed updates, and ask the user to confirm. If the employee is not found or multiple are found, report the error from the tool.\n"
            "5. **For DELETE requests:** First, use the 'find_employee' tool to get the employee's PK. If found, respond by stating the employee's PK and name, and ask the user to confirm the deletion. If the employee is not found or multiple are found, report the error from the tool.\n"
            "6. **For LIST requests:** Use the 'list_employees' tool and present the results clearly.\n"
            "7. **Tool Usage:** When you need to call a tool, generate a function call with the correct arguments. Do not execute create, update, or delete actions yourself; only prepare the data and ask for confirmation.\n"
            "8. **Clarity:** If a request is ambiguous, ask clarifying questions.\n"
            "9. **Errors:** If a tool returns an error, report that error to the user.\n\n"
            "Example Confirmation Request (Update):\n"
            "\"Okay, I found employee John Doe with PK 15. You want to update their Salary to 75000 and Title to 'Senior Developer'. Please confirm you want to proceed with these changes.\"\n\n"
            "Example Confirmation Request (Delete):\n"
            "\"Okay, I found employee Jane Smith with PK 22. Please confirm you want to delete this employee.\"\n\n"
            "Example Confirmation Request (Create):\n"
            "\"Okay, I understand you want to create a new employee with the following details:\n"
            "FirstName: Bob\n"
            "LastName: Builder\n"
            "Title: Foreman\n"
            "Salary: 60000\n"
            "... (other fields) ...\n"
            "Please confirm you want to create this employee record.\""
        )

        # Optionally, you can inject the system prompt as the first message in your state.
        self.initial_system_message = {"role": "system", "content": [{"text": self.system_prompt}]}

        self.graph = self._build_graph()

    def _build_graph(self):
        """Builds the LangGraph state machine."""
        builder = StateGraph(AgentState)

        builder.add_node("call_llm", self.call_llm)
        builder.add_node("use_tool", self.use_tool)

        builder.add_edge(START, "call_llm")
        builder.add_conditional_edges(
            "call_llm",
            self.should_continue,
            {
                "use_tool": "use_tool",
                END: END,
            },
        )
        builder.add_edge("use_tool", "call_llm")

        graph = builder.compile()
        agent_logger.info("LangGraph agent compiled.")
        return graph

    def call_llm(self, state: AgentState):
        """Invokes the LLM with the current state using ChatogleGenerativeAI."""
        agent_logger.debug(f"Calling LLM. Current messages: {state['messages']}")
        # Convert agent messages (list of message objects) into a list of tuples (role, text)
        converted_messages = []
        for msg in state['messages']:
            if isinstance(msg, SystemMessage):
                role = "system"
            elif isinstance(msg, HumanMessage):
                role = "user"
            elif isinstance(msg, AIMessage):
                role = "assistant"
            else:
                role = "user"  # Default role if type is unknown

            # Access the content attribute directly
            content = msg.content
            converted_messages.append((role, content))

        try:
            # Invoke the LLM with the prepared messages.
            ai_msg = self.model.invoke(converted_messages)
            # The response from ChatogleGenerativeAI is expected to be a string.
            response_content = {"role": "ai", "content": [{"text": str(ai_msg)}]}
            agent_logger.debug(f"LLM raw response: {response_content}")
            return {"messages": [response_content]}
        except Exception as e:
            agent_logger.error(f"Error calling LLM: {e}", exc_info=True)
            error_message = {"role": "ai", "content": [{"text": f"Error communicating with LLM: {e}"}]}
            return {"messages": [error_message]}




    def use_tool(self, state: AgentState):
        """Executes tools called by the LLM."""
        agent_logger.debug("Entering use_tool node.")
        last_message = state["messages"][-1]
        tool_calls = []

        # Check if last_message is a dict and has 'content'
        if isinstance(last_message, dict) and 'content' in last_message:
            # Iterate through content to find function calls
            for part in last_message.get('content', []):
                # Check if part is a dict and has 'function_call'
                if isinstance(part, dict) and 'function_call' in part:
                    tool_calls.append(part['function_call'])
        else:
            agent_logger.warning(f"Unexpected format for last message in use_tool: {last_message}")

        if not tool_calls:
            agent_logger.warning("No function calls found in the last message.")
            # Return an empty tool response to allow LLM to possibly retry
            return {"messages": [{"role": "tool", "content": []}]}

        tool_results_content = []
        for tool_call in tool_calls:
            tool_name = tool_call.get('name')
            args = tool_call.get('args', {})

            agent_logger.info(f"LLM requested tool call: {tool_name} with args: {args}")

            if not tool_name or tool_name not in self.tool_mapping:
                agent_logger.error(f"Tool '{tool_name}' not found or name missing.")
                error_result = ToolResult(status="error", message=f"Tool '{tool_name}' not available or name missing.")
                result_content = error_result.model_dump_json()
            else:
                func = self.tool_mapping[tool_name]
                try:
                    result = func(**args)  # Assumes tool returns a dict
                    if isinstance(result, dict):
                        result_content = json.dumps(result)
                    else:
                        result_content = str(result)
                    agent_logger.info(f"Tool '{tool_name}' executed successfully.")
                    agent_logger.debug(f"Tool '{tool_name}' result: {result_content}")
                except Exception as e:
                    agent_logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
                    error_result = ToolResult(status="error", message=f"Error executing tool {tool_name}: {e}")
                    result_content = error_result.model_dump_json()

            tool_results_content.append(
                {
                    "function_response": {
                        "name": tool_name,
                        "response": {"content": result_content},
                    }
                }
            )

        agent_logger.debug(f"Returning tool results content: {tool_results_content}")
        return {"messages": [{"role": "tool", "content": tool_results_content}]}

    @staticmethod
    def should_continue(state: AgentState) -> str:
        """Determines whether to continue with tools or end."""
        last_message = state["messages"][-1]
        if isinstance(last_message, dict) and 'content' in last_message:
            for part in last_message.get('content', []):
                if isinstance(part, dict) and 'function_call' in part:
                    agent_logger.debug("LLM requested tool use. Continuing.")
                    return "use_tool"
        agent_logger.debug("LLM did not request tool use. Ending agent turn.")
        return END

    def invoke(self, user_query: str) -> Dict[str, Any]:
        """
        Invokes the agent graph with the user query.
        Returns the final state dictionary.
        """
        agent_logger.info(f"Invoking agent with query: '{user_query}'")
        # Begin with the system prompt as the first message followed by the user's message.
        initial_state = AgentState(messages=[self.initial_system_message, {"role": "user", "content": [{"text": user_query}]}])
        config = {"recursion_limit": 10}
        try:
            final_state = self.graph.invoke(initial_state, config=config)
            agent_logger.info("Agent invocation finished.")
            agent_logger.debug(f"Final agent state: {final_state}")
            return final_state
        except Exception as e:
            agent_logger.error(f"Error invoking agent graph: {e}", exc_info=True)
            error_message = {"role": "ai", "content": [{"text": f"Agent error: {e}"}]}
            return AgentState(messages=[initial_state['messages'][0], error_message])

    def get_final_response(self, final_state: AgentState) -> str:
        """Extracts the text response from the final agent state dictionary."""
        if not final_state or not final_state.get("messages"):
            return "Agent did not produce a final state."

        last_message = final_state["messages"][-1]
        if isinstance(last_message, dict) and last_message.get("role") == "ai":
            content = last_message.get("content", [])
            if isinstance(content, list):
                return "".join(part.get("text", "") for part in content if isinstance(part, dict))
            else:
                agent_logger.warning(f"Unexpected format for 'content' in model message: {content}")
                return "Could not extract text from model response content."
        elif isinstance(last_message, dict) and last_message.get("role") == "tool":
            return "Agent ended after a tool call, awaiting LLM processing."
        else:
            return f"Could not extract final response. Last message: {last_message}"
