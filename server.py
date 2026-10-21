from typing import Dict
from mcp.server import MCPServer
from hrms import *
from utils import seed_services
from emails import EmailSender
import os
from dotenv import load_dotenv

load_dotenv()

email_sender = EmailSender(
    smtp_server="smtp.gmail.com",
    port=587,
    username=os.getenv("GOOGLE_EMAIL"),
    password=os.getenv("GOOGLE_EMAIL_PWD"),
    use_tls=True
)

mcp = MCPServer("atliq-hr-assist")

employee_manager = EmployeeManager()
leave_manager = LeaveManager()
ticket_manager = TicketManager()
meeting_manager = MeetingManager()

seed_services(employee_manager, leave_manager, meeting_manager, ticket_manager)


@mcp.tool()
def add_employee(emp_name: str, manager_id: str, email: str) -> str:
    """
    Add an employee to the HRMS system.
    :param emp_name: Employee name
    :param manager_id: Manager ID
    :param email: Employee email
    :return: Confirmation message
    """
    emp = EmployeeCreate(
        name=emp_name,
        manager_id=manager_id,
        email=email,
        emp_id=employee_manager.get_next_emp_id()
    )
    employee_manager.add_employee(emp)
    return f"Employee {emp_name} added successfully"

@mcp.tool()
def get_employee_details(name: str) -> Dict[str, str]:
    """
    Get employee details by name.
    :param name: Name of the employee.
    :return: Employee ID and manager ID
    """
    matches = employee_manager.search_employee_by_name(name)
    if len(matches) == 0:
        raise ValueError(f'No matching employee found for {name}')

    emp_id = matches[0]
    return employee_manager.get_employee_details(emp_id)

@mcp.tool()
def send_email(subject: str, body: str, to_emails: List[str]):
    email_sender.send_email(
        subject=subject,
        body=body,
        to_emails=to_emails,
        from_email=email_sender.username
    )
    return "Email sent successfully"

@mcp.tool()
def create_ticket(emp_id: str, item: str, reason: str) -> str:
    ticket_req = TicketCreate(
        emp_id=emp_id,
        item=item,
        reason=reason
    )
    return ticket_manager.create_ticket(ticket_req)

@mcp.tool()
def create_meeting(meeting_dt: str, emp_id: str, topic: str) -> str:
    meeting_req = MeetingCreate(
        emp_id=emp_id,
        topic=topic,
        meeting_dt=meeting_dt
    )
    return meeting_manager.schedule_meeting(meeting_req)

@mcp.prompt("Onboard_new_employee")
def onboard_new_employee(employee_name: str, manager_name: str):
    return f"""
    Onboard a new employee with following details:
    - Name: {employee_name}
    - Manager Name: {manager_name}
    Steps to follow:
    - Add the employee to the HRMS system
    - Send a welcome email to the employee with their login credentials. (Format: employee_name@atliq.com)
    - Notify the manager about the new employee's onboarding.
    - Raise tickets for new laptop, id card and other necessary equipments.
    - Schedule an introductory meeting of the new employee with their manager.
"""


if __name__=="__main__":
    mcp.run(transport="stdio")