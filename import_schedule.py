import pandas as pd
import sys
import os
from datetime import datetime

# --- 1. Setup Path ---
sys.path.append(os.getcwd())

# --- 2. Import App Modules ---
from app.db import SessionLocal, engine
from app.models import Employee, Schedule, ScheduleEntry, Base

# Create tables
Base.metadata.create_all(bind=engine)


def parse_time_string(time_str):
    """
    Parses strings like '7:55am', '12: 00pm', '1pm'.
    Handles typos like extra spaces.
    """
    # 1. Clean the string: remove ALL spaces
    if not isinstance(time_str, str):
        return None

    clean_str = time_str.replace(" ", "").strip().lower()  # "12: 00pm" -> "12:00pm"

    # 2. Try parsing with minutes
    try:
        dt = datetime.strptime(clean_str, "%I:%M%p")
        return dt
    except ValueError:
        pass

    # 3. Try parsing without minutes (e.g. "1pm")
    try:
        dt = datetime.strptime(clean_str, "%I%p")
        return dt
    except ValueError:
        pass

    return None


def get_hour_range(start_str, end_str):
    start_dt = parse_time_string(start_str)
    end_dt = parse_time_string(end_str)

    if not start_dt or not end_dt:
        return None  # Return None to signal failure

    start_h = start_dt.hour
    if start_dt.minute >= 30:
        start_h += 1

    end_h = end_dt.hour
    if end_dt.minute >= 30:
        end_h += 1

    # Handle overnight shifts or PM/AM mixups if needed,
    # but for now assume standard day order.
    if end_h <= start_h:
        # If end time is smaller (e.g. 1pm to 2pm -> 13 to 14), datetime handles 24h.
        # But if the calc messed up, return empty.
        pass

    return list(range(start_h, end_h))


def parse_csv_and_import(csv_path, schedule_version_name="Spring 2025 - Clean Import"):
    print(f"📂 Reading file: {csv_path}...")
    db = SessionLocal()

    new_schedule = Schedule(version_name=schedule_version_name, status="draft")
    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)
    print(f"✅ Created Schedule: '{new_schedule.version_name}'")

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return

    success_count = 0
    error_count = 0

    for index, row in df.iterrows():
        # Get basic info
        raw_name = str(row.get("Member", "")).strip()

        # Skip empty rows
        if not raw_name or raw_name.lower() == "nan":
            continue

        start_time_str = str(row.get("Start Time", ""))
        end_time_str = str(row.get("End Time", ""))
        start_date_str = str(row.get("Start Date", ""))

        # --- VALIDATION ---
        # 1. Check Date
        try:
            date_obj = datetime.strptime(start_date_str, "%m/%d/%Y")
            day_name = date_obj.strftime("%A")
        except ValueError:
            print(f"⚠️ SKIPPING Row {index + 2} ({raw_name}): Invalid Date '{start_date_str}'")
            error_count += 1
            continue

        # 2. Check Time
        hours_covered = get_hour_range(start_time_str, end_time_str)

        if hours_covered is None:
            # THIS IS THE NEW PART: It prints exactly why it failed
            print(
                f"⚠️ SKIPPING Row {index + 2} ({raw_name}): Could not parse time '{start_time_str}' - '{end_time_str}'")
            error_count += 1
            continue

        # --- DATABASE ENTRY ---
        employee = db.query(Employee).filter(Employee.name == raw_name).first()
        if not employee:
            email = str(row.get("Work Email", "")).strip()
            if not email or email == "nan":
                email = f"{raw_name.replace(' ', '.').lower()}@example.com"

            employee = Employee(name=raw_name, email=email)
            db.add(employee)
            db.commit()
            db.refresh(employee)

        for h in hours_covered:
            exists = db.query(ScheduleEntry).filter_by(
                schedule_id=new_schedule.id,
                employee_id=employee.employee_id,
                day_of_week=day_name,
                hour=h
            ).first()

            if not exists:
                entry = ScheduleEntry(
                    schedule_id=new_schedule.id,
                    employee_id=employee.employee_id,
                    day_of_week=day_name,
                    hour=h
                )
                db.add(entry)
                success_count += 1

    db.commit()
    db.close()

    print("-" * 40)
    print(f"🏁 Import Finished.")
    print(f"✅ Successful Entries: {success_count}")
    if error_count > 0:
        print(f"❌ Skipped Rows: {error_count} (See warnings above)")
    else:
        print("🎉 No errors found!")


if __name__ == "__main__":
    csv_filename = "improvedschedule.csv"
    if os.path.exists(csv_filename):
        parse_csv_and_import(csv_filename)
    else:
        print(f"❌ Error: Could not find '{csv_filename}'")