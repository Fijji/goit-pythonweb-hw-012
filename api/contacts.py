from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from schemas.contacts import ContactCreate, ContactRead
from repository.contacts import (
    create_contact,
    get_user_contacts,
    get_contact_by_id,
    update_contact,
    delete_contact,
    get_upcoming_birthdays
)
from auth import get_current_user

router = APIRouter()

@router.get("/", response_model=List[ContactRead])
async def get_contacts(
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Retrieve a list of contacts for the authenticated user.
    """
    return get_user_contacts(db, current_user.id)

@router.post("/", response_model=ContactRead, status_code=201)
async def create_new_contact(
        contact: ContactCreate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Create a new contact.
    """
    return create_contact(db, contact, current_user.id)

@router.get("/{contact_id}/", response_model=ContactRead)
async def get_contact(
        contact_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    contact = get_contact_by_id(db, contact_id, current_user.id)
    """
    Return contact by id.
    """
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact

@router.put("/{contact_id}/", response_model=ContactRead)
async def update_contact_info(
        contact_id: int,
        contact_data: ContactCreate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    contact = update_contact(db, contact_id, contact_data, current_user.id)
    """
    Update an existing contact's information.
    """
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact

@router.delete("/{contact_id}/", status_code=204)
async def delete_contact(
        contact_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    success = delete_contact(db, contact_id, current_user.id)
    """
    Delete a contact by its ID.
    """
    if not success:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"detail": "Contact deleted"}

@router.get("/upcoming-birthdays/", response_model=List[ContactRead])
async def upcoming_birthdays(
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Retrieve a list of contacts with upcoming birthdays.
    """
    return get_upcoming_birthdays(db, current_user.id)
