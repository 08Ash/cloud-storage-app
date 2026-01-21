# Cloud Storage Service (FastAPI + React)

A cloud-based file storage system built using FastAPI for backend and React for frontend.

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
