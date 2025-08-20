from fastapi import FastAPI, UploadFile, File, Form, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from typing import List, Optional
import os
from app.db import create_db_and_tables, get_session
from passlib.context import CryptContext
from app.models import Note, Transaction, User
from jose import jwt 
from datetime import datetime, timedelta

app = FastAPI(title="NoteTrade API")

# Signup/Login
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password) 

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=1)):
    SECRET_KEY = "764b967bd547q2vc64y970nv85chycgbxa8rt3yvn9q87nq12waf0535trmkpqazcvvrdi"  # Change this to a random, secret string!
    ALGORITHM = "HS256"
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# Call this once at startup to create tables (if they don't exist)
create_db_and_tables()


# CORS middleware if needed
origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static & templates setup
templates = Jinja2Templates(directory="app/templates")
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Startup event
@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    os.makedirs(UPLOAD_DIR, exist_ok=True)

# Web pages
@app.get("/", response_class=HTMLResponse)
def homepage(request: Request):
    return templates.TemplateResponse("homepage.html", {"request": request})

@app.get("/upload", response_class=HTMLResponse)
def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.get("/notes", response_class=HTMLResponse)
def browse_notes(request: Request, session: Session = Depends(get_session)):
    notes: List[Note] = session.exec(select(Note).order_by(Note.id.desc())).all()
    return templates.TemplateResponse("index.html", {"request": request, "notes": notes})

@app.get("/transactions", response_class=HTMLResponse)
def transactions_page(request: Request, session: Session = Depends(get_session)):
    txs: List[Transaction] = session.exec(select(Transaction).order_by(Transaction.timestamp.desc())).all()
    return templates.TemplateResponse("transactions.html", {"request": request, "transactions": txs})

@app.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/contact", response_class=HTMLResponse)
def contact(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})
@app.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})
@app.get("/terms", response_class=HTMLResponse)
def terms(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})
@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# API routes
@app.get("/api/notes", response_model=List[Note])
def read_notes(
    skip: int = 0,
    limit: int = 12,
    subject: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    session: Session = Depends(get_session),
):
    query = select(Note)
    if subject:
        query = query.where(Note.subject == subject)
    if category:
        query = query.where(Note.category == category)
    if search:
        query = query.where(Note.title.ilike(f"%{search}%"))

    notes = session.exec(query.offset(skip).limit(limit)).all()
    return notes

@app.post("/api/upload", status_code=201)
async def upload_note(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    subject: str = Form(...),
    category: str = Form(...),
    price: float = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed.")

    file_location = os.path.join(UPLOAD_DIR, file.filename)
    base, ext = os.path.splitext(file.filename)
    counter = 1
    while os.path.exists(file_location):
        file_location = os.path.join(UPLOAD_DIR, f"{base}_{counter}{ext}")
        counter += 1

    with open(file_location, "wb") as buffer:
        buffer.write(await file.read())

    new_note = Note(
        title=title,
        description=description,
        subject=subject,
        category=category,
        price=price,
        file_path=file_location,
    )
    session.add(new_note)
    session.commit()
    session.refresh(new_note)
    return {"message": "Note uploaded successfully", "note_id": new_note.id}

@app.get("/uploads/{filename}")
def get_uploaded_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, media_type="application/pdf", filename=filename)
    
@app.post("/api/signup")
def signup(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session)
):
    user = session.exec(select(User).where(User.username == username)).first()
    if user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(password)
    new_user = User(username=username, email=email, hashed_password=hashed_password)
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return {"message": "User created successfully"}

@app.post("/api/login")
def login(
    username_or_email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session)
):
    user = session.exec(
        select(User).where(
            (User.username == username_or_email) | (User.email == username_or_email)
        )
    ).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}