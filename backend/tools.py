from db import conn

INVALID_PHONE = {
    "success": False,
    "error": "invalid_phone",
    "message": "Ask the caller to repeat their 10-digit mobile number.",
}

def clean_phone(p):
    digits = "".join(ch for ch in (p or "") if ch.isdigit())
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10 and digits[0] in "6789":
        return "+91" + digits
    return None

def _details(c, appt_id):
    r = c.execute("""SELECT a.id appointment_id, a.patient_name, a.phone, a.status,
                            d.name doctor, d.speciality, s.date, s.time
                     FROM appointments a
                     JOIN slots s ON s.id = a.slot_id
                     JOIN doctors d ON d.id = s.doctor_id
                     WHERE a.id=?""", (appt_id,)).fetchone()
    return dict(r)

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
    c = conn()
    try:
        rows = [dict(r) for r in c.execute(q, args)]
    finally:
        c.close()
    if not rows:
        return {"slots": [], "message": "No free slots match. Offer other dates or doctors."}
    return {"slots": rows}

def book_appointment(slot_id: int, phone: str, patient_name: str = "Caller"):
    phone = clean_phone(phone)
    if phone is None:
        return dict(INVALID_PHONE)
    c = conn()
    try:
        existing = c.execute(
            "SELECT id FROM appointments WHERE phone=? AND status='booked' LIMIT 1",
            (phone,)).fetchone()
        if existing:
            return {"success": False, "error": "already_booked",
                    "message": "This number already has an active appointment. "
                               "Tell the caller, and offer to cancel it first if they want a new one.",
                    **_details(c, existing["id"])}
        cur = c.execute("UPDATE slots SET booked=1 WHERE id=? AND booked=0", (slot_id,))
        if cur.rowcount == 0:
            exists = c.execute("SELECT 1 FROM slots WHERE id=?", (slot_id,)).fetchone()
            if not exists:
                return {"success": False, "error": "slot_not_found",
                        "message": "That slot doesn't exist. Re-check availability."}
            return {"success": False, "error": "slot_taken",
                    "message": "That slot was just taken. Offer another."}
        cur = c.execute("INSERT INTO appointments(slot_id, phone, patient_name) VALUES(?,?,?)",
                        (slot_id, phone, patient_name))
        appt_id = cur.lastrowid
        c.commit()
        return {"success": True, **_details(c, appt_id)}
    finally:
        c.close()

def cancel_appointment(phone: str):
    phone = clean_phone(phone)
    if phone is None:
        return dict(INVALID_PHONE)
    c = conn()
    try:
        appt = c.execute("""SELECT id, slot_id FROM appointments
                            WHERE phone=? AND status='booked'
                            ORDER BY id DESC LIMIT 1""", (phone,)).fetchone()
        if not appt:
            return {"success": False, "error": "no_active_appointment",
                    "message": "No active appointment for this number. Ask them to confirm the number."}
        c.execute("UPDATE appointments SET status='cancelled' WHERE id=?", (appt["id"],))
        c.execute("UPDATE slots SET booked=0 WHERE id=?", (appt["slot_id"],))
        c.commit()
        return {"success": True, **_details(c, appt["id"])}
    finally:
        c.close()