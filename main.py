from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import sqlite3
from datetime import datetime
from urllib.parse import quote_plus


app = FastAPI(title="Appointment Board")

DB = "appointments.db"

templates = Jinja2Templates(directory="templates")

# Serve CSS files
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


# =========================
# DATABASE
# =========================

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

    # Add sample appointments only if database is empty
    if count == 0:

        conn.executemany("""
            INSERT INTO appointments
            (
                title,
                description,
                date,
                start_time,
                end_time,
                status
            )
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


# =========================
# VALIDATION
# =========================

def validate(
    title,
    date,
    start_time,
    end_time,
    exclude_id=None
):

    # Required fields
    if not title.strip():
        return "Please fill in all required fields."

    if not date.strip():
        return "Please fill in all required fields."

    if not start_time.strip():
        return "Please fill in all required fields."

    if not end_time.strip():
        return "Please fill in all required fields."

    # Validate time format
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

    # End time must be after start
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

    # When editing, don't compare with itself
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


# =========================
# HOME PAGE
# =========================

@app.get(
    "/",
    response_class=HTMLResponse,
    name="index"
)
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
        request=request,
        name="index.html",
        context={
            "appointments": appointments,
            "date_filter": date,
            "status_filter": status
        }
    )


# =========================
# ADD APPOINTMENT
# =========================

@app.get(
    "/add",
    response_class=HTMLResponse,
    name="add_page"
)
def add_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="form.html",
        context={
            "appointment": {},
            "mode": "Add",
            "error": None
        }
    )


@app.post(
    "/add",
    name="add"
)
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
            request=request,
            name="form.html",
            context={
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

    message = quote_plus(
        "Appointment added successfully."
    )

    return RedirectResponse(
        url=f"/?message={message}",
        status_code=303
    )


# =========================
# EDIT APPOINTMENT
# =========================

@app.get(
    "/edit/{appointment_id}",
    response_class=HTMLResponse,
    name="edit_page"
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

        error = quote_plus(
            "Appointment not found."
        )

        return RedirectResponse(
            url=f"/?error={error}",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="form.html",
        context={
            "appointment": appointment,
            "mode": "Edit",
            "error": None,
            "appointment_id": appointment_id
        }
    )


@app.post(
    "/edit/{appointment_id}",
    name="edit"
)
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

    existing = conn.execute(
        """
        SELECT *
        FROM appointments
        WHERE id = ?
        """,
        (appointment_id,)
    ).fetchone()

    conn.close()

    if not existing:

        error = quote_plus(
            "Appointment not found."
        )

        return RedirectResponse(
            url=f"/?error={error}",
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

        appointment = {
            "title": title,
            "description": description,
            "date": date,
            "start_time": start_time,
            "end_time": end_time
        }

        return templates.TemplateResponse(
            request=request,
            name="form.html",
            context={
                "appointment": appointment,
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

    message = quote_plus(
        "Appointment updated successfully."
    )

    return RedirectResponse(
        url=f"/?message={message}",
        status_code=303
    )


# =========================
# COMPLETE APPOINTMENT
# =========================

@app.post(
    "/complete/{appointment_id}",
    name="complete"
)
def complete(appointment_id: int):

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

        message = quote_plus(
            "Appointment marked as completed."
        )

        return RedirectResponse(
            url=f"/?message={message}",
            status_code=303
        )

    error = quote_plus(
        "Only scheduled appointments can be completed."
    )

    return RedirectResponse(
        url=f"/?error={error}",
        status_code=303
    )


# =========================
# CANCEL APPOINTMENT
# =========================

@app.post(
    "/cancel/{appointment_id}",
    name="cancel"
)
def cancel(appointment_id: int):

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

        message = quote_plus(
            "Appointment cancelled."
        )

        return RedirectResponse(
            url=f"/?message={message}",
            status_code=303
        )

    error = quote_plus(
        "Only scheduled appointments can be cancelled."
    )

    return RedirectResponse(
        url=f"/?error={error}",
        status_code=303
    )


# =========================
# STARTUP
# =========================

@app.on_event("startup")
def startup():

    init_db()