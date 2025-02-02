import uuid

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi_limiter.depends import RateLimiter
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from auth import Hash, create_access_token, get_current_user, send_verification_email, SECRET_KEY, ALGORITHM, \
    send_password_reset_email, is_admin
from models import User
from database import get_db
import cloudinary.uploader
from fastapi import UploadFile

router = APIRouter()
hash_handler = Hash()

class SignupModel(BaseModel):
    """
    Schema for user signup.
    """
    username: str
    email: str
    password: str
    model_config = ConfigDict(from_attributes=True)

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(
        body: SignupModel,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(User.email == body.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
    hashed_password = hash_handler.get_password_hash(body.password)
    new_user = User(username=body.username, email=body.email, hashed_password=hashed_password, role="user")
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    verification_token = await create_access_token(data={"sub": new_user.email, "email": new_user.email}, expires_delta=60*60)

    await send_verification_email(new_user.email, verification_token, background_tasks)
    """
    Create a new user account.
    """
    return {"message": "User created successfully, please verify your email"}

@router.post("/login")
async def login(
        body: SignupModel,
        db: Session = Depends(get_db)
):
    """
    Authenticate a user and return an access token.
    """
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not hash_handler.verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = await create_access_token(data={"email": user.email, "sub": user.username})

    return {"access_token": token, "token_type": "bearer"}

@router.get("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_verified = True
    db.commit()
    """
    Verify user email using the provided token.
    """
    return {"message": "Email verified successfully"}

@router.get("/me", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def get_user_profile(current_user=Depends(get_current_user)):
    """
    Retrieve the profile of the currently authenticated user.
    """
    return {
        "username": current_user["username"],
        "email": current_user["email"],
        "role": current_user["role"]
    }

@router.post("/avatar/")
async def upload_avatar(
        file: UploadFile,
        current_user=Depends(is_admin),
        db: Session = Depends(get_db)
):
    result = cloudinary.uploader.upload(file.file, folder="avatars")
    current_user.avatar_url = result.get("url")
    db.commit()
    """
    Upload a new avatar for the authenticated user.
    """
    return {"avatar_url": current_user.avatar_url}

@router.post("/forgot-password")
def forgot_password(email: str, db: Session = Depends(get_db)):
    """
    Generates a password reset token and sends it via email.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    reset_token = str(uuid.uuid4())
    user.reset_token = reset_token
    db.commit()

    send_password_reset_email(str(user.email), reset_token)
    return {"message": "Check your email for password reset instructions"}

@router.post("/reset-password")
async def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    """
    Resets the user's password if the provided token is valid.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=400, detail="Invalid token: No subject found")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    from auth import Hash
    user.hashed_password = Hash.get_password_hash(new_password)
    user.reset_token = None  # Remove used token
    db.commit()

    return {"message": "Password successfully changed"}

@router.put("/set-role/{user_id}", dependencies=[Depends(is_admin)])
async def set_user_role(
        user_id: int,
        new_role: str,
        db: Session = Depends(get_db)
):
    """Admin can change roles for users."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if new_role not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    user.role = new_role
    db.commit()

    return {"message": f"Role of {user.username} changed to {new_role}"}


