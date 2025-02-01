from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi_limiter.depends import RateLimiter
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from auth import Hash, create_access_token, get_current_user, send_verification_email, SECRET_KEY, ALGORITHM
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
    email: EmailStr
    password: str

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
    new_user = User(username=body.username, email=body.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    verification_token = await create_access_token(data={"sub": new_user.email}, expires_delta=60*60)

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
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not hash_handler.verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = await create_access_token(data={"sub": user.username})
    """
    Authenticate a user and return an access token.
    """
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
    return {"username": current_user.username, "email": current_user.email}

@router.post("/avatar/")
async def upload_avatar(
        file: UploadFile,
        current_user=Depends(get_current_user),
        db: Session = Depends(get_db)
):
    result = cloudinary.uploader.upload(file.file, folder="avatars")
    current_user.avatar_url = result.get("url")
    db.commit()
    """
    Upload a new avatar for the authenticated user.
    """
    return {"avatar_url": current_user.avatar_url}


