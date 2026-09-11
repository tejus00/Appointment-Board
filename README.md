# Appointment Board

A simple **FastAPI + SQLite appointment management board** for a small team.

The application provides an easy way to view, add, edit, complete, cancel, and filter appointments while preventing overlapping time slots.

## Features

* 📅 View existing appointments with sample data
* ➕ Add new appointments
* ✏️ Edit appointments
* ✅ Mark appointments as completed
* ❌ Cancel appointments
* 🔎 Filter appointments by date and status
* ⚠️ Validate required fields
* ⏰ Validate that end time is after start time
* 🚫 Prevent overlapping appointments
* 📌 Keep cancelled appointments visible and clearly marked
* 🔄 Cancelled appointments do not block the same time slot
* 📖 Automatic API documentation with FastAPI Swagger UI

## Tech Stack

* **Backend:** Python, FastAPI
* **ASGI Server:** Uvicorn
* **Database:** SQLite
* **Frontend:** HTML, CSS, Jinja2
* **API Documentation:** Swagger UI / OpenAPI
* **Version Control:** Git & GitHub

## Project Structure

```text
Appointment-Board/
│
├── main.py
├── appointments.db
├── requirements.txt
├── README.md
│
├── templates/
│   ├── index.html
│   └── form.html
│
└── static/
    └── style.css
```

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/tejus00/Appointment-Board.git
cd Appointment-Board
```

### 2. Create a virtual environment

#### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

#### macOS/Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the FastAPI application

```bash
uvicorn main:app --reload
```

### 5. Open the application

Open your browser and visit:

```text
http://127.0.0.1:8000
```

The SQLite database is created automatically when the application starts for the first time.

## API Documentation

FastAPI automatically generates interactive API documentation.

### Swagger UI

```text
http://127.0.0.1:8000/docs
```

### ReDoc

```text
http://127.0.0.1:8000/redoc
```

These pages can be used to view and test the available API routes.

## How It Works

1. The user opens the appointment board and sees existing appointments.
2. Appointments can be filtered by **date** or **status**.
3. The user selects **Add Appointment**.
4. The user enters:

   * Title
   * Description
   * Date
   * Start time
   * End time
5. FastAPI validates the appointment details.
6. The application checks whether the selected time overlaps with an existing scheduled appointment.
7. If the information is valid, the appointment is stored in SQLite.
8. Existing appointments can be edited.
9. Scheduled appointments can be marked as completed.
10. Scheduled appointments can be cancelled.
11. Cancelled appointments remain visible and are clearly marked.
12. Cancelled appointments do not block another appoi
