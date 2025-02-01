from sqlalchemy.orm import Session
from models import Contact, user_contact_association
from schemas.contacts import ContactCreate
from sqlalchemy import and_
from datetime import date, timedelta

def create_contact(db: Session, contact_data: ContactCreate, user_id: int) -> Contact:
    db_contact = db.query(Contact).filter(Contact.email == contact_data.email).first()
    if not db_contact:
        db_contact = Contact(**contact_data.dict())
        db.add(db_contact)
        db.commit()
        db.refresh(db_contact)

    db.execute(
        user_contact_association.insert().values(user_id=user_id, contact_id=db_contact.id)
    )
    db.commit()

    return db_contact

def get_user_contacts(db: Session, user_id: int):
    return db.query(Contact).join(user_contact_association).filter(user_contact_association.c.user_id == user_id).all()

def get_contact_by_id(db: Session, contact_id: int, user_id: int):
    return db.query(Contact).join(user_contact_association).filter(
        and_(
            user_contact_association.c.user_id == user_id,
            user_contact_association.c.contact_id == contact_id
        )
    ).first()

def update_contact(db: Session, contact_id: int, contact_data: ContactCreate, user_id: int):
    contact = get_contact_by_id(db, contact_id, user_id)
    if not contact:
        return None
    for key, value in contact_data.dict().items():
        setattr(contact, key, value)
    db.commit()
    return contact

def delete_contact(db: Session, contact_id: int, user_id: int) -> bool:
    contact = get_contact_by_id(db, contact_id, user_id)
    if not contact:
        return False
    db.delete(contact)
    db.commit()
    return True

def get_upcoming_birthdays(db: Session, user_id: int):
    today = date.today()
    next_week = today + timedelta(days=7)
    return db.query(Contact).join(user_contact_association).filter(
        and_(
            user_contact_association.c.user_id == user_id,
            Contact.birthday.between(today, next_week)
        )
    ).all()
