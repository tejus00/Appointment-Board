from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "appointment-board-demo"
DB = "appointments.db"

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
    count = conn.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]
    if count == 0:
        conn.executemany("""
            INSERT INTO appointments
            (title, description, date, start_time, end_time, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            ("Team Stand-up", "Daily project sync", "2026-09-11", "09:30", "10:00", "Scheduled"),
            ("Client Demo", "Demo of the latest build", "2026-09-11", "11:00", "12:00", "Scheduled"),
            ("Design Review", "Review dashboard changes", "2026-09-12", "14:00", "15:00", "Completed"),
            ("Vendor Call", "Discuss integration timeline", "2026-09-12", "16:00", "16:30", "Cancelled"),
        ])
    conn.commit()
    conn.close()

def validate(data, exclude_id=None):
    required = ["title", "date", "start_time", "end_time"]
    if any(not data.get(x, "").strip() for x in required):
        return "Please fill in all required fields."

    try:
        start = datetime.strptime(data["start_time"], "%H:%M")
        end = datetime.strptime(data["end_time"], "%H:%M")
    except ValueError:
        return "Please enter valid start and end times."

    if end <= start:
        return "End time must be after start time."

    conn = get_db()
    query = """
        SELECT id FROM appointments
        WHERE date = ?
          AND status != 'Cancelled'
          AND start_time < ?
          AND end_time > ?
    """
    params = [data["date"], data["end_time"], data["start_time"]]
    if exclude_id is not None:
        query += " AND id != ?"
        params.append(exclude_id)
    conflict = conn.execute(query, params).fetchone()
    conn.close()

    if conflict:
        return "That time slot is already booked. Please choose another time."
    return None

@app.route("/")
def index():
    date_filter = request.args.get("date", "")
    status_filter = request.args.get("status", "")
    conn = get_db()
    query = "SELECT * FROM appointments WHERE 1=1"
    params = []
    if date_filter:
        query += " AND date = ?"
        params.append(date_filter)
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)
    query += " ORDER BY date, start_time"
    appointments = conn.execute(query, params).fetchall()
    conn.close()
    return render_template("index.html", appointments=appointments,
                           date_filter=date_filter, status_filter=status_filter)

@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        data = request.form
        error = validate(data)
        if error:
            flash(error, "error")
            return render_template("form.html", appointment=data, mode="Add")
        conn = get_db()
        conn.execute("""
            INSERT INTO appointments
            (title, description, date, start_time, end_time, status)
            VALUES (?, ?, ?, ?, ?, 'Scheduled')
        """, (data["title"], data.get("description", ""), data["date"],
              data["start_time"], data["end_time"]))
        conn.commit()
        conn.close()
        flash("Appointment added successfully.", "success")
        return redirect(url_for("index"))
    return render_template("form.html", appointment={}, mode="Add")

@app.route("/edit/<int:appointment_id>", methods=["GET", "POST"])
def edit(appointment_id):
    conn = get_db()
    appointment = conn.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,)).fetchone()
    conn.close()
    if not appointment:
        flash("Appointment not found.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        data = request.form
        error = validate(data, appointment_id)
        if error:
            flash(error, "error")
            return render_template("form.html", appointment=data, mode="Edit", appointment_id=appointment_id)
        conn = get_db()
        conn.execute("""
            UPDATE appointments
            SET title=?, description=?, date=?, start_time=?, end_time=?
            WHERE id=?
        """, (data["title"], data.get("description", ""), data["date"],
              data["start_time"], data["end_time"], appointment_id))
        conn.commit()
        conn.close()
        flash("Appointment updated successfully.", "success")
        return redirect(url_for("index"))

    return render_template("form.html", appointment=appointment, mode="Edit", appointment_id=appointment_id)

@app.post("/complete/<int:appointment_id>")
def complete(appointment_id):
    conn = get_db()
    conn.execute("UPDATE appointments SET status='Completed' WHERE id=? AND status='Scheduled'", (appointment_id,))
    changed = conn.total_changes
    conn.commit()
    conn.close()
    flash("Appointment marked as completed." if changed else "Only scheduled appointments can be completed.",
          "success" if changed else "error")
    return redirect(url_for("index"))

@app.post("/cancel/<int:appointment_id>")
def cancel(appointment_id):
    conn = get_db()
    conn.execute("UPDATE appointments SET status='Cancelled' WHERE id=? AND status='Scheduled'", (appointment_id,))
    changed = conn.total_changes
    conn.commit()
    conn.close()
    flash("Appointment cancelled." if changed else "Only scheduled appointments can be cancelled.",
          "success" if changed else "error")
    return redirect(url_for("index"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
