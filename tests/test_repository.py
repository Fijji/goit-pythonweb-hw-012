from unittest.mock import MagicMock
from repository.contacts import create_contact, get_contact_by_id, delete_contact
from schemas.contacts import ContactCreate
from models import Contact

def test_create_contact():
    db_mock = MagicMock()
    contact_data = ContactCreate(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        phone="1234567890",
        birthday=None,
        additional_info="Friend"
    )

    db_mock.query.return_value.filter.return_value.first.return_value = None
    db_mock.add = MagicMock()
    db_mock.commit = MagicMock()
    db_mock.refresh = MagicMock()

    contact = create_contact(db_mock, contact_data, user_id=1)

    assert contact.email == "john@example.com"
    db_mock.add.assert_called_once()
    db_mock.commit.assert_called()

def test_get_contact_by_id():
    db_mock = MagicMock()
    contact = Contact(id=1, first_name="Alice", email="alice@example.com")

    db_mock.query.return_value.join.return_value.filter.return_value.first.return_value = contact
    fetched_contact = get_contact_by_id(db_mock, contact_id=1, user_id=1)

    assert fetched_contact is not None
    assert fetched_contact.email == "alice@example.com"

def test_delete_contact():
    db_mock = MagicMock()
    contact = Contact(id=2, first_name="Mike", email="mike@example.com")

    db_mock.query.return_value.join.return_value.filter.return_value.first.return_value = contact
    db_mock.delete = MagicMock()
    db_mock.commit = MagicMock()

    success = delete_contact(db_mock, contact_id=2, user_id=1)

    assert success is True
    db_mock.delete.assert_called_once()
    db_mock.commit.assert_called_once()

