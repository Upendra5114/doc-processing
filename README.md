# 📄 Document Processing System

A full-stack **Document Processing Application** that extracts, analyzes, and processes information from uploaded documents using **OCR** and **Natural Language Processing (NLP)**.

This project consists of:

* ⚙️ **FastAPI Backend**
* 💻 **Svelte Frontend**
* 🔍 **OCR Text Extraction**
* 🧠 **NLP Processing Pipeline**

---

## 🚀 Project Overview

The system allows users to:

* Upload document images/files
* Extract text using OCR
* Process extracted content
* Analyze document data through backend APIs
* View results through a modern frontend interface

---

## 🏗️ Project Structure

```
doc-processing/
│
├── backend/        → FastAPI server & document processing
│
├── frontend/       → Svelte UI application
│
├── steps.txt       → Setup & execution notes
└── .gitignore
```

---

## ⚙️ Tech Stack

### Backend

* Python
* FastAPI
* Uvicorn
* OCR Processing (Tesseract)
* NLP/Text Processing

### Frontend

* Svelte
* JavaScript
* HTML/CSS

---

## 🔧 Backend Setup

### 1️⃣ Navigate to Backend

```bash
cd backend
```

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
```

Activate environment:

**Windows**

```bash
venv\Scripts\activate
```

**Linux / Mac**

```bash
source venv/bin/activate
```

---

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4️⃣ Install Tesseract OCR

Download and install:

👉 [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)

After installation, add Tesseract to system PATH.

---

### 5️⃣ Run Backend Server

```bash
uvicorn main:app --reload
```

Server runs at:

```
http://127.0.0.1:8000
```

Swagger API Docs:

```
http://127.0.0.1:8000/docs
```

---

## 💻 Frontend Setup

### 1️⃣ Navigate to Frontend

```bash
cd frontend
```

### 2️⃣ Install Node Modules

```bash
npm install
```

### 3️⃣ Start Frontend

```bash
npm run dev
```

Frontend runs at:

```
http://localhost:5173
```

---

## 🔄 Application Workflow

1. User uploads a document
2. Backend receives file
3. OCR extracts text
4. NLP processes extracted content
5. Processed data returned via API
6. Frontend displays results

---

## 📡 API Features

* Document upload endpoint
* Text extraction
* Document analysis
* Processed output response

(API details available in Swagger docs)

---

## 📌 Requirements

* Python 3.9+
* Node.js 18+
* Tesseract OCR
* npm

---

## ▶️ Running Full Project

Open **two terminals**:

### Terminal 1 — Backend

```bash
cd backend
uvicorn main:app --reload
```

### Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

---

## 📷 Future Improvements

* Multiple document formats
* AI summarization
* Entity extraction
* Cloud deployment
* Authentication system

---

## 👨‍💻 Author

**Upendra**

GitHub:
[https://github.com/Upendra5114](https://github.com/Upendra5114)

---
