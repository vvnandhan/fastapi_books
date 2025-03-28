import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import jwt  # PyJWT library

# -------------------------------------------------------------------
# Configuration for JWT tokens
SECRET_KEY = "YOUR_SECRET_KEY"  # In production, use a secure key and store it safely
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# -------------------------------------------------------------------
# Pydantic models for our data
class Book(BaseModel):
    id: int
    title: str
    author: str
    category: str
    price: float
    stock: int

class User(BaseModel):
    username: str
    full_name: Optional[str] = None

class UserInDB(User):
    password: str

# -------------------------------------------------------------------
# In-memory "database"
users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "password": "secret"
    }
}
books: List[Book] = []

# -------------------------------------------------------------------
# Utility functions for authentication
def verify_password(plain_password: str, stored_password: str) -> bool:
    return plain_password == stored_password

def get_user(db, username: str) -> Optional[UserInDB]:
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    return None

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# -------------------------------------------------------------------
# Setting up OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# -------------------------------------------------------------------
# Initialize FastAPI app
app = FastAPI()

# -------------------------------------------------------------------
# Root endpoint (for quick testing)
@app.get("/")
def read_root():
    return {"message": "Welcome to the Bookstore API!"}

# -------------------------------------------------------------------
# Authentication endpoint: Get JWT token
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user(users_db, form_data.username)
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# -------------------------------------------------------------------
# Dependency to get the current user from the JWT token
def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: username missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = get_user(users_db, username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# -------------------------------------------------------------------
# Bookstore API endpoints
@app.post("/books/", response_model=Book)
def create_book(book: Book, current_user: User = Depends(get_current_user)):
    books.append(book)
    return book

@app.get("/books/", response_model=List[Book])
def list_books(current_user: User = Depends(get_current_user)):
    return books
