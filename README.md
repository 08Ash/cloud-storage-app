# Cloud Storage Service (FastAPI + React)

# Cloud Storage Service

A full-stack cloud storage application built using FastAPI (backend) and React (frontend).  
It supports file upload, folders, trash, starred files, sharing, rename, move, and preview.

## Features

- User Authentication (JWT)
- File Upload & Download
- Folder Management
- Rename / Delete Files
- Starred Files
- Trash System
- File Preview
- File Sharing with other users
- Storage usage tracking

## Tech Stack

Frontend: React, CSS  
Backend: FastAPI, SQLite  
Authentication: JWT  
Database: SQLite

## Project Structure

cloud-storage-app/
- backend/
- frontend/
- README.md

## How to Run Locally

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload

### Frontend

cd frontend
npm install
npm start

