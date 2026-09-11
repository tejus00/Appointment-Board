from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import sqlite3
from datetime import datetime
from urllib.parse import urlencode


app = FastAPI(title="Appointment Board")

DB = "appointments.db"

templates = Jinja2Templates(directory="templates")

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


# -----------------------------
# Database
# -----------------------------

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Scheduled'
        )
    """)

    count = conn.execute(
        "SELECT COUNT(*) FROM appointments"
    ).fetchone()[0]

    if count == 0:
        conn.executemany("""
            INSERT INTO appointments
            (title, description, date, start_time, end_time, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            (
                "Team Stand-up",
                "Daily project sync",
                "2026-09-11",
                "09:30",
                "10:00",
                "Scheduled"
            ),
            (
                "Client Demo",
                "Demo of the latest build",
                "2026-09-11",
                "11:00",
                "12:00",
                "Scheduled"
            ),
            (
                "Design Review",
                "Review dashboard changes",
                "2026-09-12",
                "14:00",
                "15:00",
                "Completed"
            ),
            (
                "Vendor Call",
                "Discuss integration timeline",
                "2026-09-12",
                "16:00",
                "16:30",
                "Cancelled"
            )
        ])

    conn.commit()
    conn.close()


# -----------------------------
# Validation
# -----------------------------

def validate(
    title,
    date,
    start_time,
    end_time,
    exclude_id=None
):

    if not title.strip():
        return "Please fill in all required fields."

    if not date.strip():
        return "Please fill in all required fields."

    if not start_time.strip():
        return "Please fill in all required fields."

    if not end_time.strip():
        return "Please fill in all required fields."

    try:
        start = datetime.strptime(
            start_time,
            "%H:%M"
        )

        end = datetime.strptime(
            end_time,
            "%H:%M"
        )

    except ValueError:
        return "Please enter valid start and end times."

    if end <= start:
        return "End time must be after start time."

    # Check overlapping appointments
    conn = get_db()

    query = """
        SELECT id
        FROM appointments
        WHERE date = ?
          AND status != 'Cancelled'
          AND start_time < ?
          AND end_time > ?
    """

    params = [
        date,
        end_time,
        start_time
    ]

    if exclude_id is not None:
        query += " AND id != ?"
        params.append(exclude_id)

    conflict = conn.execute(
        query,
        params
    ).fetchone()

    conn.close()

    if conflict:
        return (
            "That time slot is already booked. "
            "Please choose another time."
        )

    return None


# -----------------------------
# Home / Appointment Board
# -----------------------------

@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    date: str = "",
    status: str = ""
):

    conn = get_db()

    query = """
        SELECT *
        FROM appointments
        WHERE 1=1
    """

    params = []

    if date:
        query += " AND date = ?"
        params.append(date)

    if status:
        query += " AND status = ?"
        params.append(status)

    query += """
        ORDER BY date, start_time
    """

    appointments = conn.execute(
        query,
        params
    ).fetchall()

    conn.close()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "appointments": appointments,
            "date_filter": date,
            "status_filter": status
        }
    )


# -----------------------------
# Add Appointment
# -----------------------------

@app.get("/add", response_class=HTMLResponse)
def add_page(request: Request):

    return templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "appointment": {},
            "mode": "Add",
            "error": None
        }
    )


@app.post("/add")
def add(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    date: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...)
):

    error = validate(
        title,
        date,
        start_time,
        end_time
    )

    if error:

        appointment = {
            "title": title,
            "description": description,
            "date": date,
            "start_time": start_time,
            "end_time": end_time
        }

        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "appointment": appointment,
                "mode": "Add",
                "error": error
            },
            status_code=400
        )

    conn = get_db()

    conn.execute("""
        INSERT INTO appointments
        (
            title,
            description,
            date,
            start_time,
            end_time,
            status
        )
        VALUES (?, ?, ?, ?, ?, 'Scheduled')
    """, (
        title,
        description,
        date,
        start_time,
        end_time
    ))

    conn.commit()
    conn.close()

    return RedirectResponse(
        url="/?message=Appointment+added+successfully.",
        status_code=303
    )


# -----------------------------
# Edit Appointment
# -----------------------------

@app.get(
    "/edit/{appointment_id}",
    response_class=HTMLResponse
)
def edit_page(
    request: Request,
    appointment_id: int
):

    conn = get_db()

    appointment = conn.execute(
        """
        SELECT *
        FROM appointments
        WHERE id = ?
        """,
        (appointment_id,)
    ).fetchone()

    conn.close()

    if not appointment:

        return RedirectResponse(
            url="/?error=Appointment+not+found.",
            status_code=303
        )

    return templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "appointment": appointment,
            "mode": "Edit",
            "error": None
        }
    )


@app.post("/edit/{appointment_id}")
def edit(
    request: Request,
    appointment_id: int,
    title: str = Form(...),
    description: str = Form(""),
    date: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...)
):

    conn = get_db()

    appointment = conn.execute(
        """
        SELECT *
        FROM appointments
        WHERE id = ?
        """,
        (appointment_id,)
    ).fetchone()

    conn.close()

    if not appointment:

        return RedirectResponse(
            url="/?error=Appointment+not+found.",
            status_code=303
        )

    error = validate(
        title,
        date,
        start_time,
        end_time,
        exclude_id=appointment_id
    )

    if error:

        updated_appointment = {
            "title": title,
            "description": description,
            "date": date,
            "start_time": start_time,
            "end_time": end_time
        }

        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "appointment": updated_appointment,
                "mode": "Edit",
                "error": error,
                "appointment_id": appointment_id
            },
            status_code=400
        )

    conn = get_db()

    conn.execute("""
        UPDATE appointments
        SET
            title = ?,
            description = ?,
            date = ?,
            start_time = ?,
            end_time = ?
        WHERE id = ?
    """, (
        title,
        description,
        date,
        start_time,
        end_time,
        appointment_id
    ))

    conn.commit()
    conn.close()

    return RedirectResponse(
        url="/?message=Appointment+updated+successfully.",
        status_code=303
    )


# -----------------------------
# Complete Appointment
# -----------------------------

@app.post("/complete/{appointment_id}")
def complete(
    appointment_id: int
):

    conn = get_db()

    cursor = conn.execute(
        """
        UPDATE appointments
        SET status = 'Completed'
        WHERE id = ?
          AND status = 'Scheduled'
        """,
        (appointment_id,)
    )

    changed = cursor.rowcount

    conn.commit()
    conn.close()

    if changed:
        message = "Appointment marked as completed."
        url = "/?message=" + urlencode(
            {"message": message}
        ).split("=", 1)[1]
    else:
        url = "/?error=Only+scheduled+appointments+can+be+completed."

    return RedirectResponse(
        url=url,
        status_code=303
    )


# -----------------------------
# Cancel Appointment
# -----------------------------

@app.post("/cancel/{appointment_id}")
def cancel(
    appointment_id: int
):

    conn = get_db()

    cursor = conn.execute(
        """
        UPDATE appointments
        SET status = 'Cancelled'
        WHERE id = ?
          AND status = 'Scheduled'
        """,
        (appointment_id,)
    )

    changed = cursor.rowcount

    conn.commit()
    conn.close()

    if changed:
        url = "/?message=Appointment+cancelled."
    else:
        url = (
            "/?error="
            "Only+scheduled+appointments+can+be+cancelled."
        )

    return RedirectResponse(
        url=url,
        status_code=303
    )


# -----------------------------
# Application startup
# -----------------------------

@app.on_event("startup")
def startup():

    init_db()