# crudapp/agent_tools.py
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field # Using pydantic for tool input/output definition (optional but good practice)
from .models import Employee
from .forms import EmployeeForm # To leverage validation if needed
from .agent_logger import agent_logger
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, ValidationError

# --- Pydantic Models for Tool Inputs/Outputs (Optional but Recommended) ---

class EmployeeData(BaseModel):
    """Schema for employee data used in creation or updates."""
    FirstName: Optional[str] = None
    LastName: Optional[str] = None
    Title: Optional[str] = None
    HasPassport: Optional[bool] = None
    Salary: Optional[int] = None
    DateOfBirth: Optional[str] = Field(None, description="Date in YYYY-MM-DD format")
    HireDate: Optional[str] = Field(None, description="Date in YYYY-MM-DD format")
    Notes: Optional[str] = None
    Country: Optional[str] = None
    Email: Optional[str] = None
    PhoneNumber: Optional[str] = None

class FindEmployeeArgs(BaseModel):
    first_name: str
    last_name: str

class UpdateEmployeeArgs(BaseModel):
    employee_pk: int
    updates: Dict[str, Any] # Dictionary of fields to update

class DeleteEmployeeArgs(BaseModel):
    employee_pk: int

class EmployeeInfo(BaseModel):
    """Simplified Employee representation for LLM"""
    pk: int
    FirstName: str
    LastName: str
    Title: Optional[str] = None
    Email: Optional[str] = None
    Country: Optional[str] = None

class ToolResult(BaseModel):
    """Standard structure for tool results"""
    status: str = Field(..., description="success or error")
    message: Optional[str] = None
    data: Optional[Union[List[EmployeeInfo], EmployeeInfo, Dict[str, Any]]] = None # Flexible data field


# --- Tool Functions ---

def find_employee(first_name: str, last_name: str) -> Dict[str, Any]:
    """
    Finds a single employee by their first and last name.
    Returns employee details including PK if found, otherwise an error message.
    Use this BEFORE attempting to update or delete an employee by name.
    """
    agent_logger.info(f"Tool: find_employee called with name='{first_name} {last_name}'")
    try:
        employee = Employee.objects.get(FirstName__iexact=first_name, LastName__iexact=last_name)
        result = ToolResult(
            status="success",
            message=f"Found employee {employee.FirstName} {employee.LastName}.",
            data=EmployeeInfo.model_validate(employee).model_dump() # Convert model instance to dict/Pydantic model
        )
        agent_logger.info(f"Tool: find_employee success - found pk={employee.pk}")
        return result.model_dump()
    except ObjectDoesNotExist:
        msg = f"Employee '{first_name} {last_name}' not found."
        agent_logger.warning(f"Tool: find_employee failed - {msg}")
        return ToolResult(status="error", message=msg).model_dump()
    except MultipleObjectsReturned:
        msg = f"Multiple employees found for '{first_name} {last_name}'. Please be more specific (e.g., provide email or ID if possible)."
        agent_logger.warning(f"Tool: find_employee failed - {msg}")
        return ToolResult(status="error", message=msg).model_dump()
    except Exception as e:
        msg = f"An error occurred while searching for the employee: {e}"
        agent_logger.error(f"Tool: find_employee error - {msg}")
        return ToolResult(status="error", message=msg).model_dump()

def list_employees() -> Dict[str, Any]:
    """
    Lists all employees with basic information (PK, Name, Title, Email, Country).
    """
    agent_logger.info("Tool: list_employees called")
    try:
        employees = Employee.objects.all().order_by('LastName', 'FirstName')
        # Convert each employee model instance to the EmployeeInfo structure
        employee_list = [EmployeeInfo.model_validate(emp).model_dump() for emp in employees]
        result = ToolResult(
            status="success",
            message=f"Found {len(employee_list)} employees.",
            data=employee_list
        )
        agent_logger.info(f"Tool: list_employees success - found {len(employee_list)} employees")
        return result.model_dump()
    except Exception as e:
        msg = f"An error occurred while listing employees: {e}"
        agent_logger.error(f"Tool: list_employees error - {msg}")
        return ToolResult(status="error", message=msg).model_dump()

# Note: The actual CUD operations are NOT defined as tools here.
# The LLM's role is to understand the intent, gather necessary info (like PK using find_employee),
# and prepare the data. The final execution (create, update, delete) happens in the
# Django view *after* user confirmation, directly calling ORM methods.
# This avoids needing the LLM to manage the confirmation state.

# If you wanted the LLM to *execute* the changes (less recommended due to confirmation complexity):
# You would add tools like create_employee_tool, update_employee_tool, delete_employee_tool here.
# Example (if LLM were to execute directly):
#
# def create_employee_tool(employee_data: Dict[str, Any]) -> Dict[str, Any]:
#     """Creates a new employee. Use ONLY after user confirmation."""
#     agent_logger.info(f"Tool: create_employee_tool called with data: {employee_data}")
#     form = EmployeeForm(employee_data)
#     if form.is_valid():
#         try:
#             employee = form.save()
#             agent_logger.info(f"Tool: create_employee_tool success - created pk={employee.pk}")
#             return ToolResult(status="success", message=f"Employee {employee} created successfully.", data=EmployeeInfo.model_validate(employee).model_dump()).model_dump()
#         except Exception as e:
#             msg = f"Error saving employee: {e}"
#             agent_logger.error(f"Tool: create_employee_tool error - {msg}")
#             return ToolResult(status="error", message=msg).model_dump()
#     else:
#         errors = form.errors.as_json()
#         agent_logger.warning(f"Tool: create_employee_tool failed validation - {errors}")
#         return ToolResult(status="error", message=f"Validation failed: {errors}", data=form.errors.get_json_data()).model_dump()
#
# def delete_employee_tool(employee_pk: int) -> Dict[str, Any]:
#      """Deletes an employee by PK. Use ONLY after user confirmation."""
#      # ... implementation ...
#
# def update_employee_tool(employee_pk: int, updates: Dict[str, Any]) -> Dict[str, Any]:
#      """Updates an employee by PK. Use ONLY after user confirmation."""
#      # ... implementation ...

