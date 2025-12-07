import pandas as pd
import re
import sys
import os

# --- 1. Setup Path ---
# This ensures we can find the 'app' folder
sys.path.append(os.getcwd())

# --- 2. Import App Modules ---
# If this fails, it will show the real error (like "No module named sqlalchemy")
from app.db import SessionLocal, engine
from app.models import Employee, Schedule, ScheduleEntry, Base

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)


def parse_time_to_hour(time_str):
    """
    Converts '7:55', '9:20', '2:55' into a 24-hour integer (0-23).
    """
    if not isinstance(time_str, str): return None
    time_str = time_str.lower().strip()

    # Extract numbers (e.g., 7:55 -> [7, 55])
    nums = re.findall(r'\d+', time_str)
    if not nums: return None

    hour = int(nums[0])
    minute = int(nums[1]) if len(nums) > 1 else 0

    # Rounding logic: If > 45 mins, round up to next hour (7:55 -> 8)
    if minute > 45:
        hour += 1

    # PM Logic for College Schedule:
    # 1, 2, 3, 4, 5, 6 -> Assume PM (13-18)
    # 7, 8, 9, 10, 11 -> Assume AM
    # 12 -> Noon
    if 1 <= hour <= 6:
        hour += 12
    elif hour == 12:
        pass  # Noon is 12

    return hour


def parse_csv_and_import(csv_path, schedule_version_name="Spring 2025 Initial Import"):
    print(f"📂 Reading file: {csv_path}...")
    db = SessionLocal()

    # --- A. Create the Schedule Container ---
    new_schedule = Schedule(version_name=schedule_version_name, status="draft")
    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)
    print(f"✅ Created Schedule: '{new_schedule.version_name}' (ID: {new_schedule.id})")

    # --- B. Load CSV ---
    try:
        # Read header=None so we can find the real header dynamically
        df = pd.read_csv(csv_path, header=None)
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return

    # --- C. Find the Header Row (Days of Week) ---
    header_row_index = -1
    col_map = {}  # Stores {column_index: "Monday", ...}

    # Scan the first 10 rows to find "Monday"
    for idx, row in df.head(10).iterrows():
        row_str = str(row.values).lower()
        if "monday" in row_str:
            header_row_index = idx
            # Map the columns
            for col_idx, val in row.items():
                val_str = str(val).strip()
                for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
                    if day in val_str:
                        col_map[col_idx] = day
            break

    if header_row_index == -1:
        print("❌ Error: Could not find a row containing 'Monday'. Check the CSV format.")
        return

    print(f"📅 Found Days: {list(col_map.values())}")

    # --- D. Track Time State ---
    # col_active_time tracks the current time block for each column index.
    # We initialize everyone to "7:55" just in case.
    col_active_time = {c: "7:55" for c in col_map}

    # --- E. Iterate Data Rows ---
    # Start loop AFTER the header row
    for index, row in df.iloc[header_row_index + 1:].iterrows():

        # 1. Check Global Time (Column 0) - usually for MWF
        # Looks for "8:55-9:55a" pattern
        first_col = str(row.values[0]).strip()
        if pd.notna(row.values[0]) and any(char.isdigit() for char in first_col) and ('-' in first_col):
            current_row_time_str = first_col.split('-')[0]  # Take start time

            # Update MWF columns to this new time
            for c, day in col_map.items():
                if day in ["Monday", "Wednesday", "Friday", "Saturday", "Sunday"]:
                    col_active_time[c] = current_row_time_str

        # 2. Process Each Column
        for col_idx, cell_val in row.items():
            if col_idx not in col_map: continue

            raw_text = str(cell_val).strip()
            if not raw_text or raw_text.lower() == "nan": continue

            # CHECK FOR SPECIAL TUES/THURS MARKERS (e.g., ____9:20____)
            marker_match = re.search(r'_+(\d{1,2}:\d{2})_+', raw_text)

            if marker_match:
                # Found a marker! Update this specific column's time
                new_time = marker_match.group(1)
                col_active_time[col_idx] = new_time

                # Remove marker text to see if names are left
                clean_text = re.sub(r'_+(\d{1,2}:\d{2})_+', '', raw_text).strip()
                if not clean_text:
                    continue  # It was just a marker, move on
                raw_text = clean_text  # Names remain

            # 3. Add Schedule Entries
            names = re.split(r'[,\n]', raw_text)

            # Convert current string time (e.g. "9:20") to integer (e.g. 9)
            hour_int = parse_time_to_hour(col_active_time[col_idx])

            if hour_int is None: continue

            for name in names:
                name = name.strip()
                if not name: continue

                # Find/Create Employee
                employee = db.query(Employee).filter(Employee.name == name).first()
                if not employee:
                    email = f"{name.replace(' ', '.').lower()}@example.com"
                    employee = Employee(name=name, email=email)
                    db.add(employee)
                    db.commit()
                    db.refresh(employee)
                    print(f"  👤 New Employee: {name}")

                # Prevent duplicates
                exists = db.query(ScheduleEntry).filter_by(
                    schedule_id=new_schedule.id,
                    employee_id=employee.employee_id,
                    day_of_week=col_map[col_idx],
                    hour=hour_int
                ).first()

                if not exists:
                    entry = ScheduleEntry(
                        schedule_id=new_schedule.id,
                        employee_id=employee.employee_id,
                        day_of_week=col_map[col_idx],
                        hour=hour_int
                    )
                    db.add(entry)

    db.commit()
    print("✨ Import complete! Database populated.")
    db.close()


if __name__ == "__main__":
    # Ensure this matches your specific filename
    csv_filename = "Spring 2025 Semester Scedule copy(BLK 3 Printout).csv"

    if os.path.exists(csv_filename):
        parse_csv_and_import(csv_filename)
    else:
        print(f"❌ Error: Could not find '{csv_filename}'")
        print("Make sure the file is in the same folder as this script.")