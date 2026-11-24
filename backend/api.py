from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db import conn, init_db

init_db()
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def rows(sql):
    c = conn()
    try:
        return [dict(r) for r in c.execute(sql)]
    finally:
        c.close()

@app.get("/data/doctors")
def doctors():
    return rows("SELECT id, name, speciality FROM doctors")

@app.get("/data/slots")
def slots():
    return rows("""SELECT s.id slot_id, d.name doctor, d.speciality, s.date, s.time
                   FROM slots s JOIN doctors d ON d.id = s.doctor_id
                   WHERE s.booked = 0 ORDER BY s.date, s.time""")

@app.get("/data/appointments")
def appointments():
    return rows("""SELECT a.id, a.patient_name, a.phone, a.status, d.name doctor,
                          d.speciality, s.date, s.time
                   FROM appointments a JOIN slots s ON s.id = a.slot_id
                   JOIN doctors d ON d.id = s.doctor_id ORDER BY a.id DESC""")