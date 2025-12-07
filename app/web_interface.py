from flask import Flask, render_template, request, redirect, url_for, session
from app.db import SessionLocal
from app.models import Employee, Schedule, ScheduleEntry

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_dev_only'


def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


# 1. LANDING PAGE (Your existing index.html)
@app.route('/')
def home():
    return render_template('index.html')


# 2. SET ROLE & REDIRECT
@app.route('/set_role/<role>')
def set_role(role):
    session['role'] = role
    # Redirect to the NEW schedule view instead of availability form
    return redirect(url_for('view_schedule'))


# 3. SCHEDULE VIEW (The new page)
@app.route('/schedule')
def view_schedule():
    db = get_db()
    role = session.get('role', 'Guest')

    # Get the latest schedule (Spring 2025)
    latest_schedule = db.query(Schedule).order_by(Schedule.id.desc()).first()

    if not latest_schedule:
        return "<h3>No schedule found!</h3><p>Please run <code>python import_scheduler.py</code> first.</p>"

    # Get all entries
    entries = db.query(ScheduleEntry).join(Employee).filter(ScheduleEntry.schedule_id == latest_schedule.id).all()

    # Prepare data for the grid
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    # Range from 7 AM to 10 PM (22) based on your CSV
    hours_range = range(7, 23)

    # Structure: schedule_data[hour][day] = [List of Names]
    schedule_data = {h: {d: [] for d in days} for h in hours_range}

    for entry in entries:
        # Only add if the hour/day is within our display range
        if entry.hour in schedule_data and entry.day_of_week in schedule_data[entry.hour]:
            schedule_data[entry.hour][entry.day_of_week].append(entry.employee.name)

    return render_template('schedule.html',
                           schedule=schedule_data,
                           hours=hours_range,
                           days=days,
                           version=latest_schedule.version_name,
                           role=role)


if __name__ == '__main__':
    app.run(debug=True)