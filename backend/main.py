from fastapi import Depends, FastAPI, UploadFile, File, HTTPException, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from jose import jwt
import os
import shutil
import sqlite3
from datetime import datetime

# ================== AUTH SETUP ==================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except:
        raise HTTPException(status_code=401, detail="Invalid token")


# ================== APP ==================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

import os
print("USING DATABASE FILE:", os.path.abspath(DB_PATH))

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")


if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)


# ================== DATABASE ==================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            user_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            size INTEGER,
            upload_time TEXT,
            user_id INTEGER,
            folder_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(folder_id) REFERENCES folders(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shared_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER,
            owner_id INTEGER,
            shared_with INTEGER,
            FOREIGN KEY(file_id) REFERENCES files(id),
            FOREIGN KEY(owner_id) REFERENCES users(id),
            FOREIGN KEY(shared_with) REFERENCES users(id)
)
""")


    conn.commit()
    conn.close()


init_db()

# ================== ROUTES ==================

@app.get("/")
def home():
    return {"message": "Cloud Storage Backend Running"}


# ---------- SIGNUP ----------
@app.post("/signup/")
def signup(email: str = Form(...), password: str = Form(...)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    hashed = hash_password(password)

    try:
        cursor.execute(
            "INSERT INTO users (email, password) VALUES (?, ?)",
            (email, hashed)
        )
        conn.commit()
    except:
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")

    conn.close()
    return {"message": "User registered successfully"}


# ---------- LOGIN ----------
@app.post("/login/")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    email = form_data.username
    password = form_data.password

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, password FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    user_id, hashed_password = user

    if not verify_password(password, hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = jwt.encode({"user_id": user_id}, SECRET_KEY, algorithm=ALGORITHM)

    return {"access_token": token, "token_type": "bearer"}


# ---------- CREATE FOLDER ----------
@app.post("/folders/")
def create_folder(
    name: str = Form(...),
    user_id: int = Depends(get_current_user)
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO folders (name, user_id) VALUES (?, ?)",
        (name, user_id)
    )
    folder_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"message": "Folder created", "id": folder_id, "name": name}


# ---------- LIST FOLDERS ----------
@app.get("/folders/")
def list_folders(user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name FROM folders WHERE user_id = ?",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1]} for r in rows]


# ---------- UPLOAD FILE ----------
@app.post("/upload/")
async def upload_file(
    file: UploadFile = File(...),
    folder_id: int = Form(None),
    user_id: int = Depends(get_current_user)
):
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    size = os.path.getsize(file_path)
    upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO files (filename, filepath, size, upload_time, user_id, folder_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (file.filename, file_path, size, upload_time, user_id, folder_id))
    conn.commit()
    conn.close()

    return {"message": "File uploaded successfully"}


# ---------- LIST FILES ----------
@app.get("/files/")
def list_files(folder_id: int = None, user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if folder_id is None:
        cursor.execute("""
            SELECT id, filename, size, upload_time
            FROM files
            WHERE user_id = ? 
            AND folder_id IS NULL 
            AND is_deleted = 0
        """, (user_id,))
    else:
        cursor.execute("""
            SELECT id, filename, size, upload_time
            FROM files
            WHERE user_id = ? 
            AND folder_id = ? 
            AND is_deleted = 0
        """, (user_id, folder_id))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "filename": r[1],
            "size": r[2],
            "upload_time": r[3]
        }
        for r in rows
    ]

# ---------- DELETE FILE ----------
@app.delete("/file/{file_id}")
def delete_file(file_id: int, user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE files SET is_deleted = 1 
        WHERE id = ? AND user_id = ?
    """, (file_id, user_id))

    conn.commit()
    conn.close()
    return {"message": "File moved to trash"}


# ---------- DOWNLOAD FILE ----------
@app.get("/download/{file_id}")
def download_file(file_id: int, user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT filepath, filename FROM files WHERE id = ? AND user_id = ?",
        (file_id, user_id)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="File not found")

    file_path, filename = row
    return FileResponse(path=file_path, filename=filename)

@app.get("/trash/")
def get_trash(user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, filename, size, upload_time 
        FROM files 
        WHERE user_id = ? AND is_deleted = 1
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    return [
        {"id": r[0], "filename": r[1], "size": r[2], "upload_time": r[3]}
        for r in rows
    ]

@app.post("/restore/{file_id}")
def restore_file(file_id: int, user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE files SET is_deleted = 0 
        WHERE id = ? AND user_id = ?
    """, (file_id, user_id))

    conn.commit()
    conn.close()
    return {"message": "File restored"}

# ---------- RENAME FOLDER ----------
@app.put("/folders/{folder_id}")
def rename_folder(
    folder_id: int,
    name: str = Form(...),
    user_id: int = Depends(get_current_user)
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE folders 
        SET name = ?
        WHERE id = ? AND user_id = ?
    """, (name, folder_id, user_id))

    conn.commit()
    conn.close()

    return {"message": "Folder renamed successfully"}

# ---------- RENAME FILE ----------
@app.put("/files/{file_id}")
def rename_file(
    file_id: int,
    name: str = Form(...),
    user_id: int = Depends(get_current_user)
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE files SET filename = ?
        WHERE id = ? AND user_id = ?
    """, (name, file_id, user_id))

    conn.commit()
    conn.close()
    return {"message": "File renamed successfully"}


@app.get("/storage/")
def get_storage_usage(user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COALESCE(SUM(size), 0)
        FROM files
        WHERE user_id = ? AND is_deleted = 0
    """, (user_id,))

    used = cursor.fetchone()[0]
    conn.close()

    TOTAL_STORAGE = 1024 * 1024 * 1024  # 1 GB in bytes

    return {
        "used": used,
        "total": TOTAL_STORAGE
    }

@app.put("/file/move/{file_id}")
def move_file(file_id: int, folder_id: int = Form(None), user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if folder_id == "" or folder_id is None:
        cursor.execute("""
            UPDATE files SET folder_id = NULL
            WHERE id = ? AND user_id = ?
        """, (file_id, user_id))
    else:
        cursor.execute("""
            UPDATE files SET folder_id = ?
            WHERE id = ? AND user_id = ?
        """, (folder_id, file_id, user_id))

    conn.commit()
    conn.close()
    return {"message": "File moved successfully"}

@app.post("/star/{file_id}")
def toggle_star(file_id: int, user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE files SET is_starred = CASE WHEN is_starred=1 THEN 0 ELSE 1 END
        WHERE id=? AND user_id=?
    """, (file_id, user_id))
    conn.commit()
    conn.close()
    return {"message": "Star toggled"}

@app.get("/starred/")
def get_starred_files(user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, filename, size, upload_time
        FROM files
        WHERE user_id = ? AND is_starred = 1 AND is_deleted = 0
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "filename": r[1], "size": r[2], "upload_time": r[3]}
        for r in rows
    ]

# ---------- DELETE FOLDER ----------
@app.delete("/folders/{folder_id}")
def delete_folder(folder_id: int, user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # First move all files in this folder to trash
    cursor.execute("""
        UPDATE files SET is_deleted = 1 
        WHERE folder_id = ? AND user_id = ?
    """, (folder_id, user_id))

    # Then delete the folder
    cursor.execute("""
        DELETE FROM folders 
        WHERE id = ? AND user_id = ?
    """, (folder_id, user_id))

    conn.commit()
    conn.close()
    return {"message": "Folder deleted and files moved to trash"}

@app.get("/shared/")
def get_shared_files(user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.id, f.filename, f.size, f.upload_time
        FROM files f
        JOIN shared_files s ON f.id = s.file_id
        WHERE s.shared_with = ?
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    return [
        {"id": r[0], "filename": r[1], "size": r[2], "upload_time": r[3]}
        for r in rows
    ]

@app.post("/share/{file_id}")
def share_file(
    file_id: int,
    email: str = Form(...),
    user_id: int = Depends(get_current_user)
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # find target user
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    target = cursor.fetchone()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target_id = target[0]

    cursor.execute("""
        INSERT INTO shared_files (file_id, owner_id, shared_with)
        VALUES (?, ?, ?)
    """, (file_id, user_id, target_id))

    conn.commit()
    conn.close()
    return {"message": "File shared successfully"}
