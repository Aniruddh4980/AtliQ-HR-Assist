"""Pytest tests for the MCP tools exposed by :mod:`server`."""

from types import SimpleNamespace
from unittest.mock import ANY, Mock, patch

import pytest

import server
from emails import EmailSender


@pytest.fixture
def managers(monkeypatch):
    """Replace server dependencies with mocks for an isolated tool call."""
    dependencies = SimpleNamespace(
        employee_manager=Mock(),
        leave_manager=Mock(),
        ticket_manager=Mock(),
        meeting_manager=Mock(),
        email_sender=Mock(),
    )

    for name, dependency in vars(dependencies).items():
        monkeypatch.setattr(server, name, dependency)

    return dependencies


def test_add_employee_uses_next_id_and_returns_confirmation(managers):
    managers.employee_manager.get_next_emp_id.return_value = "E009"

    result = server.add_employee("Asha Rao", "E001", "asha@atliq.com")

    assert result == "Employee Asha Rao added successfully"
    employee = managers.employee_manager.add_employee.call_args.args[0]
    assert employee.emp_id == "E009"
    assert employee.name == "Asha Rao"
    assert employee.manager_id == "E001"
    assert employee.email == "asha@atliq.com"


def test_get_employee_details_returns_first_name_match(managers):
    expected = {"emp_id": "E003", "name": "David Wilson", "manager_id": "E001"}
    managers.employee_manager.search_employee_by_name.return_value = ["E003", "E008"]
    managers.employee_manager.get_employee_details.return_value = expected

    result = server.get_employee_details("David Wilson")

    assert result == expected
    managers.employee_manager.search_employee_by_name.assert_called_once_with("David Wilson")
    managers.employee_manager.get_employee_details.assert_called_once_with("E003")


def test_get_employee_details_raises_when_no_match(managers):
    managers.employee_manager.search_employee_by_name.return_value = []

    with pytest.raises(ValueError, match="No matching employee found for Unknown"):
        server.get_employee_details("Unknown")

    managers.employee_manager.get_employee_details.assert_not_called()


def test_send_email_forwards_arguments_and_returns_confirmation(managers):
    result = server.send_email("Welcome", "Hello!", ["new@atliq.com"])

    assert result == "Email sent successfully"
    managers.email_sender.send_email.assert_called_once_with(
        subject="Welcome",
        body="Hello!",
        to_emails=["new@atliq.com"],
        from_email=managers.email_sender.username,
    )


@pytest.mark.parametrize("use_tls, smtp_class", [(True, "SMTP"), (False, "SMTP_SSL")])
def test_email_sender_successfully_delivers_message(use_tls, smtp_class):
    sender = EmailSender(
        smtp_server="smtp.example.com",
        port=587 if use_tls else 465,
        username="hr@atliq.com",
        password="test-password",
        use_tls=use_tls,
    )

    with patch(f"emails.smtplib.{smtp_class}") as smtp_factory:
        smtp_client = smtp_factory.return_value.__enter__.return_value

        sender.send_email(
            subject="Welcome to AtliQ",
            body="Your onboarding is complete.",
            to_emails=["asha@atliq.com", "sarah@atliq.com"],
        )

    if use_tls:
        smtp_factory.assert_called_once_with(sender.smtp_server, sender.port)
    else:
        smtp_factory.assert_called_once_with(sender.smtp_server, sender.port, context=ANY)
    smtp_client.login.assert_called_once_with(sender.username, sender.password)
    smtp_client.send_message.assert_called_once()
    message = smtp_client.send_message.call_args.args[0]
    assert message["Subject"] == "Welcome to AtliQ"
    assert message["From"] == sender.username
    assert message["To"] == "asha@atliq.com, sarah@atliq.com"
    assert message.get_content().strip() == "Your onboarding is complete."
    if use_tls:
        smtp_client.starttls.assert_called_once()
    else:
        smtp_client.starttls.assert_not_called()


def test_create_ticket_builds_request_and_returns_manager_result(managers):
    managers.ticket_manager.create_ticket.return_value = "Ticket T0012 created for E009."

    result = server.create_ticket("E009", "Laptop", "New hire setup")

    assert result == "Ticket T0012 created for E009."
    request = managers.ticket_manager.create_ticket.call_args.args[0]
    assert request.emp_id == "E009"
    assert request.item == "Laptop"
    assert request.reason == "New hire setup"


def test_create_meeting_builds_request_and_returns_manager_result(managers):
    meeting_dt = "2026-11-02T10:30:00"
    managers.meeting_manager.schedule_meeting.return_value = (
        "Meeting scheduled for E009 on 2026-11-02T10:30:00 about 'Welcome'."
    )

    result = server.create_meeting(meeting_dt, "E009", "Welcome")

    assert result == "Meeting scheduled for E009 on 2026-11-02T10:30:00 about 'Welcome'."
    request = managers.meeting_manager.schedule_meeting.call_args.args[0]
    assert request.emp_id == "E009"
    assert request.topic == "Welcome"
    assert request.meeting_dt.isoformat() == meeting_dt


def test_onboarding_prompt_includes_employee_details_and_steps():
    prompt = server.onboard_new_employee("Asha Rao", "Sarah Johnson")

    assert "Name: Asha Rao" in prompt
    assert "Manager Name: Sarah Johnson" in prompt
    assert "Add the employee to the HRMS system" in prompt
    assert "Schedule an introductory meeting" in prompt
