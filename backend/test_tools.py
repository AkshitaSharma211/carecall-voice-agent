from db import init_db
from tools import *

init_db()
slots = check_doctor_availability(speciality="derma")["slots"]
print("Slots:", slots[:2])
sid = slots[0]["slot_id"]
print(book_appointment(sid, "98765 43210", "Akshita"))
print(book_appointment(sid, "1111111111"))          # should fail: taken
print(cancel_appointment("9876543210"))
print(check_doctor_availability(speciality="derma")["slots"][0])  # slot is back