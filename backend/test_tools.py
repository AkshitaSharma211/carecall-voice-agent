from db import init_db
from tools import *
import os
from db import DB, init_db

if os.path.exists(DB):
    os.remove(DB)
init_db()

slots = check_doctor_availability(speciality="derma")["slots"]
print("Slots:", slots[:2])
sid = slots[0]["slot_id"]
print(book_appointment(sid, "98765 43210", "Akshita"))
print(book_appointment(sid, "1111111111"))          # should fail: taken
print(cancel_appointment("9876543210"))
print(check_doctor_availability(speciality="derma")["slots"][0])  # slot is back

from tools import book_appointment, cancel_appointment

def show(label, result):
    print(f"\n{label}\n  -> {result}")

# 1. same number, two formats: second must be already_booked
show("1a book slot 1, '98765 43210'", book_appointment(1, "98765 43210", "Akshita"))
show("1b book slot 2, '+91 98765 43210'", book_appointment(2, "+91 98765 43210", "Akshita"))

# 2. cancel, then book again: both must succeed
show("2a cancel '9876543210'", cancel_appointment("9876543210"))
show("2b book slot 2 again", book_appointment(2, "9876543210", "Akshita"))

# 3. slot that doesn't exist: must be slot_not_found
show("3 book slot 999", book_appointment(999, "9123456780", "Test"))

# 4. number with nothing booked: must be no_active_appointment
show("4 cancel unbooked number", cancel_appointment("9123456780"))