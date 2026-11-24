import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB = str(Path(__file__).parent / "clinic.db")

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = conn()
    try:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS doctors(id INTEGER PRIMARY KEY, name TEXT, speciality TEXT);
        CREATE TABLE IF NOT EXISTS slots(id INTEGER PRIMARY KEY, doctor_id INT, date TEXT, time TEXT, booked INT DEFAULT 0);
        CREATE TABLE IF NOT EXISTS appointments(id INTEGER PRIMARY KEY, slot_id INT, phone TEXT, patient_name TEXT, status TEXT DEFAULT 'booked');
        """)
        if c.execute("SELECT COUNT(*) FROM doctors").fetchone()[0] == 0:
            docs = [("Dr. Meera Rao", "Dermatology"), ("Dr. Arjun Mehta", "Cardiology"), ("Dr. Sana Khan", "General Physician")]
            for name, spec in docs:
                c.execute("INSERT INTO doctors(name, speciality) VALUES(?,?)", (name, spec))
            for doc_id in range(1, len(docs) + 1):
                for d in range(1, 4):
                    day = (date.today() + timedelta(days=d)).isoformat()
                    for t in ["10:00", "11:00", "14:00", "16:00"]:
                        c.execute("INSERT INTO slots(doctor_id, date, time) VALUES(?,?,?)", (doc_id, day, t))
        c.commit()
    finally:
        c.close()