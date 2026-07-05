from fastapi import APIRouter, Request, Form, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import hashlib
import secrets
import psycopg2
from app.database import get_db_connection

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# временное хранилище сессий в памяти
sessions = {}

def create_session(username: str) -> str:
    token = secrets.token_hex(32)
    sessions[token] = username
    return token

def get_current_user(request: Request) -> str:
    token = request.cookies.get("session")
    return sessions.get(token)

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = get_current_user(request)
    if user:
        return templates.TemplateResponse("welcome.html", {"request": request, "username": user})
    return RedirectResponse(url="/login")

@router.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
async def register(username: str = Form(...), password: str = Form(...)):
    conn = get_db_connection()
    cursor = conn.cursor()
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    try:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", 
                       (username, password_hash))
        conn.commit()
    except psycopg2.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")
    finally:
        conn.close()
        
    return RedirectResponse(url="/login", status_code=303)

@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # тут уязвимый запрос для SQL-инъекции
    query = f"SELECT id, username, password_hash FROM users WHERE username='{username}' AND password_hash='{hashlib.sha256(password.encode()).hexdigest()}'"
    
    try:
        cursor.execute(query)
        user = cursor.fetchone()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()

    if user:
        token = create_session(user[1]) # user[1] это username
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(key="session", value=token, httponly=True)
        return response
    else:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

@router.get("/welcome", response_class=HTMLResponse)
async def welcome(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("welcome.html", {"request": request, "username": user})