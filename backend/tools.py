from db import conn

def clean_phone(p: str) -> str:
    return "".join(ch for ch in p if ch.isdigit())  # "98765 43210" -> "9876543210"

def check_doctor_availability(speciality: str = None, doctor_name: str = None, date: str = None):
    q = """SELECT s.id slot_id, d.name doctor, d.speciality, s.date, s.time
           FROM slots s JOIN doctors d ON d.id = s.doctor_id WHERE s.booked = 0"""
    args = []
    if speciality:
        q += " AND LOWER(d.speciality) LIKE ?"; args.append(f"%{speciality.lower()}%")
    if doctor_name:
        q += " AND LOWER(d.name) LIKE ?"; args.append(f"%{doctor_name.lower()}%")
    if date:
        q += " AND s.date = ?"; args.append(date)
    q += " ORDER BY s.date, s.time LIMIT 8"
    c = conn(); rows = [dict(r) for r in c.execute(q, args)]; c.close()
    return {"slots": rows}

def book_appointment(slot_id: int, phone: str, patient_name: str = "Caller"):
    phone = clean_phone(phone)
    c = conn()
    slot = c.execute("SELECT booked FROM slots WHERE id=?", (slot_id,)).fetchone()
    if not slot:
        c.close(); return {"success": False, "error": "Slot not found"}
    if slot["booked"]:
        c.close(); return {"success": False, "error": "Slot already taken"}
    c.execute("UPDATE slots SET booked=1 WHERE id=?", (slot_id,))
    c.execute("INSERT INTO appointments(slot_id, phone, patient_name) VALUES(?,?,?)", (slot_id, phone, patient_name))
    c.commit(); c.close()
    return {"success": True, "slot_id": slot_id, "phone": phone}

def cancel_appointment(phone: str):
    phone = clean_phone(phone)
    c = conn()
    appt = c.execute("SELECT id, slot_id FROM appointments WHERE phone=? AND status='booked' ORDER BY id DESC LIMIT 1", (phone,)).fetchone()
    if not appt:
        c.close(); return {"success": False, "error": "No active appointment for this number"}
    c.execute("UPDATE appointments SET status='cancelled' WHERE id=?", (appt["id"],))
    c.execute("UPDATE slots SET booked=0 WHERE id=?", (appt["slot_id"],))
    c.commit(); c.close()
    return {"success": True}