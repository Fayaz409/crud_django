# crudapp/views.py
import re
import json
from django.db import models
from django.http import JsonResponse
from django.core.paginator import Paginator,PageNotAnInteger

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.conf import settings # To get API key if stored there

from .models import Employee
from .forms import EmployeeForm
# Remove the old agent import:
# from .agent import process_agent_command
from .llm_agent import DjangoCrudAgent, AgentState # Import the new agent
from .agent_logger import agent_logger
# Import tool functions ONLY for direct execution after confirmation
from .agent_tools import EmployeeData # Use Pydantic model for validation

# Existing views (employee_list, employee_detail, employee_create, etc.) remain the same...


def employee_list(request):
    employees = Employee.objects.all()
    return render(request, 'crudapp/employee_list.html', {'employees': employees})

def employee_detail(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    return render(request, 'crudapp/employee_detail.html', {'employee': employee})

def employee_create(request):
    if request.method == "POST":
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('employee_list')
    else:
        form = EmployeeForm()
    return render(request, 'crudapp/employee_form.html', {'form': form})

def employee_update(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == "POST":
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            return redirect('employee_list')
    else:
        form = EmployeeForm(instance=employee)
    return render(request, 'crudapp/employee_form.html', {'form': form})

def employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == "POST":
        employee.delete()
        return redirect('employee_list')
    return render(request, 'crudapp/employee_confirm_delete.html', {'employee': employee})


def employee_list(request):
    employees = Employee.objects.all().order_by('LastName', 'FirstName')
    agent_message = request.session.pop('agent_message', None)
    if agent_message:
        messages.info(request, agent_message)
    return render(request, 'crudapp/employee_list.html', {'employees': employees})

# --- Agent Views ---

def agent_command(request):
    """Handles commands submitted from the agent input using the LLM Agent."""
    if request.method == 'POST':
        command = request.POST.get('agent_command', '').strip()
        agent_logger.info(f"Received agent command: '{command}'")

        if not command:
            messages.warning(request, "Agent command cannot be empty.")
            return redirect('employee_list')

        try:
            # Instantiate the agent (consider caching or making it a singleton if performance is critical)
            # Pass API key from settings if configured there
            agent = DjangoCrudAgent(api_key=getattr(settings, 'GEMINI_API_KEY', None))

            # Invoke the agent
            final_state = agent.invoke(command)

            # Extract the final response text from the agent
            response_text = agent.get_final_response(final_state)
            agent_logger.info(f"Agent final response text: {response_text}")

            # --- Analyze response for confirmation ---
            # This part requires parsing the LLM's text response to see if it's asking for confirmation.
            # We'll use keywords and simple regex, but more robust NLP could be used.

            action = None
            data_for_session = None
            confirm_message = response_text # Default message is the LLM response

            # Check for CREATE confirmation pattern
            create_match = re.search(r"confirm.*create.*employee.*details:\s*(.*)", response_text, re.IGNORECASE | re.DOTALL)
            if create_match:
                action = 'create'
                # Try to parse details (this is brittle, LLM needs to be consistent)
                details_str = create_match.group(1).strip()
                # Simple parsing: assume "Key: Value" lines
                parsed_data = {}
                for line in details_str.split('\n'):
                    if ':' in line:
                        key, val = line.split(':', 1)
                        # Map to model field names (needs refinement)
                        field_name = key.strip().replace(" ", "") # Remove spaces e.g. "First Name" -> "FirstName"
                        # Find the actual model field name case-insensitively
                        model_field = next((f.name for f in Employee._meta.get_fields() if f.name.lower() == field_name.lower()), None)
                        if model_field:
                           parsed_data[model_field] = val.strip()
                        else:
                           agent_logger.warning(f"Could not map parsed field '{key.strip()}' to Employee model field.")

                if parsed_data:
                    data_for_session = parsed_data
                    agent_logger.info(f"Extracted CREATE data for confirmation: {data_for_session}")
                else:
                     agent_logger.error(f"Failed to parse CREATE details from LLM response: {details_str}")
                     action = None # Reset action if parsing failed


            # Check for UPDATE confirmation pattern (expects PK)
            update_match = re.search(r"confirm.*update.*employee.*PK\s*(\d+).*updates:\s*(.*)|confirm.*update.*employee.*PK\s*(\d+).*changes\?", response_text, re.IGNORECASE | re.DOTALL)
            # update_match_simple = re.search(r"confirm.*update.*employee.*PK\s*(\d+)", response_text, re.IGNORECASE)
            if update_match:
                 action = 'update'
                 pk = update_match.group(1) or update_match.group(3) # Get PK from either capture group
                 updates_str = update_match.group(2) if update_match.group(2) else "" # Get updates string

                 # Try to parse updates (again, brittle)
                 parsed_updates = {}
                 # Example parsing: "Salary to 75000 and Title to 'Senior Developer'"
                 # This requires more complex regex or assuming a clear format from the LLM
                 # Simple Example: Assume "Field to NewValue"
                 for item in re.findall(r"(\w+)\s*to\s*'?([^',]+)'?", updates_str):
                      field_name = item[0].strip()
                      model_field = next((f.name for f in Employee._meta.get_fields() if f.name.lower() == field_name.lower()), None)
                      if model_field:
                          parsed_updates[model_field] = item[1].strip()

                 if pk and parsed_updates:
                     data_for_session = {'employee_pk': int(pk), 'updates': parsed_updates}
                     agent_logger.info(f"Extracted UPDATE data for confirmation: {data_for_session}")
                 else:
                     agent_logger.warning(f"Failed to parse UPDATE details (PK={pk}, Updates='{updates_str}') from LLM response.")
                     action = None # Reset action

            # Check for DELETE confirmation pattern (expects PK)
            delete_match = re.search(r"confirm.*delete.*employee.*PK\s*(\d+)", response_text, re.IGNORECASE)
            if delete_match:
                action = 'delete'
                pk = delete_match.group(1)
                if pk:
                    data_for_session = int(pk) # Store only PK for delete
                    agent_logger.info(f"Extracted DELETE PK for confirmation: {data_for_session}")
                else:
                     agent_logger.warning(f"Failed to parse DELETE PK from LLM response.")
                     action = None # Reset action


            # --- Redirect or Display Message ---
            if action and data_for_session is not None:
                # Confirmation needed
                request.session['agent_action'] = action
                request.session['agent_data'] = data_for_session
                request.session['agent_confirm_message'] = confirm_message # Use LLM text as prompt

                confirmation_url_name = f'agent_confirm_{action}'
                agent_logger.info(f"Redirecting to confirmation: {confirmation_url_name}")
                return redirect(reverse(confirmation_url_name))
            else:
                # No confirmation detected, just display the agent's response
                messages.info(request, response_text)
                return redirect('employee_list')

        except Exception as e:
            agent_logger.error(f"Error processing agent command: {e}", exc_info=True)
            messages.error(request, f"An error occurred while processing your command: {e}")
            return redirect('employee_list')

    # If GET request, just redirect back to list
    return redirect('employee_list')




def PageWiseList(request):
    page_size = int(request.GET.get('page_size',getattr(settings,'PAGE_SIZE',3)))
    page = request.GET.get('page', 1)

    employees = Employee.objects.all()
    paginator = Paginator(employees,page_size)

    try:
        employees_page = paginator.page(page)
    except PageNotAnInteger:
        employees_page = paginator.page(1)

    return render(request,'crudapp/PageWiseEmployees.html',{'employees_page':employees_page,'page_size':page_size})


# agent_confirm view remains largely the same, as it reads from the session
# which agent_command now populates based on LLM output analysis.
# Make sure the templates agent_confirm_*.html can handle the data format stored in the session.
# Specifically, agent_confirm_update.html needs employee_pk and updates dict.
# agent_confirm_create.html needs a dict of field:value.
# agent_confirm_delete_agent.html needs the employee PK.

def agent_confirm(request, action):
    """Displays confirmation page for create, update, or delete."""
    agent_action = request.session.get('agent_action')
    agent_data = request.session.get('agent_data')
    confirm_message = request.session.get('agent_confirm_message', f'Confirm {action}?') # Get message

    # Basic validation
    if not agent_action or agent_action != action or agent_data is None:
        messages.error(request, "Confirmation session expired or invalid. Please try again.")
        request.session.pop('agent_action', None)
        request.session.pop('agent_data', None)
        request.session.pop('agent_confirm_message', None)
        agent_logger.warning(f"Invalid confirmation state for action '{action}'. Session: action='{agent_action}'")
        return redirect('employee_list')

    context = {
        'action': action,
        'message': confirm_message, # Use message from LLM stored in session
    }
    template_name = f'crudapp/agent_confirm_{action}.html'
    # Adjust template name for delete if needed
    if action == 'delete':
         template_name = 'crudapp/agent_confirm_delete_agent.html'

    try:
        if action == 'create':
            # agent_data is a dictionary of proposed values
            # Create a form instance for display validation (optional)
            form = EmployeeForm(initial=agent_data)
            context['form_data'] = agent_data # Pass raw data for display
            context['form'] = form # Pass form for structured display
            agent_logger.info(f"Showing confirmation for CREATE with data: {agent_data}")

        elif action == 'update':
            # agent_data is {'employee_pk': pk, 'updates': {dict of updates}}
            employee_pk = agent_data.get('employee_pk')
            updates = agent_data.get('updates', {})
            employee = get_object_or_404(Employee, pk=employee_pk)
            context['employee'] = employee
            context['updates'] = updates
            agent_logger.info(f"Showing confirmation for UPDATE (pk={employee_pk}) with updates: {updates}")

        elif action == 'delete':
            # agent_data is the employee PK
            employee_pk = agent_data
            employee = get_object_or_404(Employee, pk=employee_pk)
            context['employee'] = employee
            agent_logger.info(f"Showing confirmation for DELETE (pk={employee_pk})")

    except Employee.DoesNotExist:
         messages.error(request, f"Employee not found for confirmation. Please try again.")
         request.session.pop('agent_action', None)
         request.session.pop('agent_data', None)
         request.session.pop('agent_confirm_message', None)
         return redirect('employee_list')
    except Exception as e:
        messages.error(request, f"Error preparing confirmation: {e}")
        agent_logger.error(f"Error in agent_confirm view for action {action}: {e}", exc_info=True)
        return redirect('employee_list')


    return render(request, template_name, context)


def agent_execute(request):
    """
    Executes the action after user confirmation.
    This view now directly calls ORM methods or validation logic,
    using the data prepared by the LLM and stored in the session.
    """
    if request.method == 'POST':
        agent_action = request.session.pop('agent_action', None)
        agent_data = request.session.pop('agent_data', None)
        # Clear message too
        request.session.pop('agent_confirm_message', None)

        if not agent_action or agent_data is None:
            messages.error(request, "Confirmation session expired or invalid. Action cancelled.")
            agent_logger.warning("Execute called with missing session data.")
            return redirect('employee_list')

        try:
            if agent_action == 'create':
                # agent_data is the dictionary of fields prepared by LLM
                agent_logger.info(f"Agent EXECUTE: Creating employee with data: {agent_data}")
                # Validate data using Pydantic model or Django Form
                try:
                    # Use Pydantic for validation before creating
                    # validated_data = EmployeeData(**agent_data).model_dump(exclude_unset=True) # exclude_unset avoids passing None for non-provided fields
                    # Or use Django Form
                    form = EmployeeForm(agent_data)
                    if form.is_valid():
                         employee = form.save()
                         messages.success(request, f"Agent successfully created employee: {employee}.")
                         agent_logger.info(f"Agent EXECUTE: Created employee {employee.pk}")
                    else:
                         error_msg = f"Agent failed to create employee due to validation errors: {form.errors.as_text()}"
                         messages.error(request, error_msg)
                         agent_logger.error(f"Agent EXECUTE: Create validation failed. Data: {agent_data}. Errors: {form.errors.as_json()}")

                except ValidationError as e: # Catch Pydantic or Django validation errors
                     error_msg = f"Agent failed to create employee due to validation errors: {e}"
                     messages.error(request, error_msg)
                     agent_logger.error(f"Agent EXECUTE: Create validation failed. Data: {agent_data}. Error: {e}")


            elif agent_action == 'update':
                # agent_data is {'employee_pk': pk, 'updates': {dict}}
                employee_pk = agent_data.get('employee_pk')
                updates = agent_data.get('updates')
                agent_logger.info(f"Agent EXECUTE: Updating employee pk={employee_pk} with updates: {updates}")

                if not employee_pk or not updates:
                     messages.error(request, "Invalid update data received.")
                     agent_logger.error(f"Agent EXECUTE: Invalid update data format: {agent_data}")
                     return redirect('employee_list')

                employee = get_object_or_404(Employee, pk=employee_pk)

                # Validate updates before applying (using Pydantic or Form partial update)
                # Example using partial form validation:
                form = EmployeeForm(updates, instance=employee, partial=True) # partial=True might need custom form logic or library
                # Simpler: Validate types manually or trust LLM formatting for now
                try:
                    for field, value in updates.items():
                         # Basic type conversion/check (can enhance)
                         model_field = Employee._meta.get_field(field)
                         if isinstance(model_field, models.IntegerField) and not isinstance(value, int):
                             value = int(value)
                         elif isinstance(model_field, models.BooleanField) and not isinstance(value, bool):
                             value = str(value).lower() in ['true', 'yes', '1', 'on']
                         elif isinstance(model_field, models.DateField) and isinstance(value, str):
                             # Add date parsing YYYY-MM-DD
                             from datetime import datetime
                             value = datetime.strptime(value, '%Y-%m-%d').date()

                         setattr(employee, field, value)

                    employee.full_clean() # Run model validation on changed fields
                    employee.save(update_fields=updates.keys()) # Only save changed fields
                    messages.success(request, f"Agent successfully updated employee: {employee}.")
                    agent_logger.info(f"Agent EXECUTE: Updated employee {employee.pk} with fields {list(updates.keys())}")
                except (ValidationError, ValueError, TypeError) as e: # Catch validation/conversion errors
                    messages.error(request, f"Agent failed to update employee {employee} due to invalid data: {e}")
                    agent_logger.error(f"Agent EXECUTE: Failed to update employee {employee.pk}. Updates: {updates}. Error: {e}")


            elif agent_action == 'delete':
                # agent_data is the employee PK
                employee_pk = agent_data
                agent_logger.info(f"Agent EXECUTE: Deleting employee pk={employee_pk}")
                employee = get_object_or_404(Employee, pk=employee_pk)
                employee_name = str(employee)
                employee.delete()
                messages.success(request, f"Agent successfully deleted employee: {employee_name}.")
                agent_logger.info(f"Agent EXECUTE: Deleted employee {employee_name} (pk={employee_pk})")

            else:
                messages.error(request, "Invalid action during execution.")
                agent_logger.error(f"Agent EXECUTE: Invalid action '{agent_action}' found.")

        except Employee.DoesNotExist:
            messages.error(request, "Employee not found during execution. Action cancelled.")
            agent_logger.error(f"Agent EXECUTE: Employee not found for action '{agent_action}'. Data: {agent_data}")
        except Exception as e:
            messages.error(request, f"An unexpected error occurred during execution: {e}")
            agent_logger.exception(f"Agent EXECUTE: Unexpected error during action '{agent_action}'. Data: {agent_data}")

        return redirect('employee_list')

    # If GET request, action was likely cancelled or invalid
    messages.warning(request, "Action cancelled.")
    # Clear potentially stale session data just in case
    request.session.pop('agent_action', None)
    request.session.pop('agent_data', None)
    request.session.pop('agent_confirm_message', None)
    return redirect('employee_list')

