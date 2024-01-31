from flask import Flask, render_template, request, redirect, session
from datetime import datetime
from flask_mail import Mail, Message
from utilities import send_mail, toDateTime, defaultDateTimeFormat, event_dict, over_booking, \
    string_to_datetime, get_min_date, format_currency
import pyrebase

app = Flask(__name__)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = '*insert email here*'
app.config['MAIL_PASSWORD'] = '*insert password here*'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
mail = Mail(app)
app.secret_key = "Something even more ominous"
config = {
    "apiKey": "AIzaSyDrY5Bjm-xTvqX5x-Qisx77zyTnqBcb7JU",
    "authDomain": "my-flask-app-392616.firebaseapp.com",
    "projectId": "my-flask-app-392616",
    "storageBucket": "my-flask-app-392616.appspot.com",
    "messagingSenderId": "718690831357",
    "appId": "1:718690831357:web:2327ec5d9838c4fc0be794",
    "measurementId": "G-N53S6X0HBV",
    "databaseURL": "https://my-flask-app-392616-default-rtdb.firebaseio.com/"
}
firebase = pyrebase.initialize_app(config)
db = firebase.database()
DEPOSIT = 100000
PRICE = 400000
app.jinja_env.globals.update(string_to_datetime=string_to_datetime, datetime=datetime,
                             defaultDateTimeFormat=defaultDateTimeFormat, get_min_date=get_min_date, deposit=DEPOSIT,
                             price=PRICE, format_currency=format_currency)

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/services")
def services():
    return render_template("services.html")


@app.route("/gallery")
def gallery():
    return render_template("gallery.html")


# Make event reservations
@app.route("/bookEvent", methods=["GET", "POST"])
def bookEvent():
    if request.method == "POST":
        first_name = request.form.get("firstName")
        last_name = request.form.get("lastName")
        email = request.form.get("email")
        number = request.form.get("number")
        event = request.form.get("event")
        people = request.form.get("many")
        event_time = request.form.get("task-datetime")
        date_in = event_time
        # Converting from an HTML datetime object to a python datetime object
        date_viewing = date_in.replace('T', '').replace(':', '').split('-')
        date_viewing = "".join(v for v in date_viewing)
        date_out = toDateTime(date_in)
        # Accounting for clashing reservations
        if over_booking(date_out, db):
            return render_template("bookEvent.html", errMessage="Day has already been booked", event=event[0])
        try:
            get_id = list(db.child("events").get().val().keys())
            last_entry_key = get_id[-1]
            last_entry_id = db.child("events").child(last_entry_key).child("id").get().val()
            id = last_entry_id + 1
        except AttributeError:
            id = 1
        booking_code = event[2].lower() + event[0].lower() + \
                       event[1].lower() + date_viewing + str(id)
        date_out_final = str(date_out).replace(" ", "-").replace(":", "-")
        new_event = event_dict(first_name=first_name, booking_code=booking_code, last_name=last_name, email=email,
                               number=number, event=event, people=people, event_time=date_out_final, event_id=id)
        new_event["dep_ref_code"] = 0
        new_event["ref_code"] = 0
        db.child("events").child(booking_code).set(new_event)
        send_mail(mail, new_event, "booked", date_out)  # Automated email client. See 'utilities.py'

        return render_template("bookEvent.html", success="Event booked. You will receive an email shortly")
    else:
        return render_template("bookEvent.html")


@app.route("/schedule")
def schedule():
    events = db.child("events").get().each()
    dates = ""
    for event in events:
        formatted_date = event.val()["event_time"][:10]
        dates += f"|{formatted_date}"
    # dates = dates.split("|")
    return render_template("schedule.html", dates=dates)


# Portal to manage reservation
@app.route("/viewBooking", methods=["POST", "GET"])
def viewBooking():
    if request.method == "POST":
        booking_code = request.form.get("bookCode")
        event = db.child("events").child(booking_code).get().val()
        if event is None:
            return render_template("viewBooking.html", errMessage="Event does not exist")
        event_time = string_to_datetime(db.child("events").child(booking_code).child("event_time").get().val())
        if event_time < datetime.utcnow():
            return render_template("viewBooking.html", errMessage="Event does not exist")
        else:
            session["booking_code"] = booking_code
            return redirect("/editBooking")
    else:
        return render_template("viewBooking.html", edit=False)


@app.route("/editBooking", methods=["GET", "POST"])
def editBooking():
    if "booking_code" in session:
        booking_code = session["booking_code"]
        event_queried = db.child("events").child(booking_code).get().val()
        event_time = string_to_datetime(event_queried["event_time"])
        month = defaultDateTimeFormat(event_time.month)
        day = defaultDateTimeFormat(event_time.day)
        hour = defaultDateTimeFormat(event_time.hour)
        minute = defaultDateTimeFormat(event_time.minute)
        payment = event_queried["payment"]
        # Payment can be made either in half or fully.
        amount = PRICE - payment
        # if payment == 0:
        #     amount = 20000000
        # elif payment <= 100000:
        #     amount = 10000000
        # else:
        #     amount = 0
        # Verifying the transaction from PayStack, a bit of added financial security.
        if request.method == "POST":
            if request.form.get("ref") is not None:
                ref = request.form.get("ref")
                from pypaystack.transactions import Transaction
                transactions = Transaction(authorization_key="sk_test_7e4d1f1b634b8817e2eb350f9bc4465b4c6c6295")
                response = transactions.verify(ref)
                if response[3]["status"] == "success" and response[3]["paid_at"] is not None and response[
                    2] == "Verification successful":
                    if int(response[3]["amount"] / 100) == DEPOSIT and payment == 0:
                        db.child("events").child(booking_code).update({"dep_ref_code": ref,
                                                                       "payment_status":
                                                                           f"Deposit Paid: {format_currency(int(response[3]['amount'] / 100))}"})
                    else:
                        db.child("events").child(booking_code).update({"ref_code": ref,
                                                                       "payment_status": f"Payment Completed: "
                                                                                         f"{format_currency(PRICE)}"})
                    if payment == 0:
                        db.child("events").child(booking_code).update({"payment": int(response[3]["amount"] / 100)})
                    else:
                        final_amount = payment + int(response[3]["amount"] / 100)
                        db.child("events").child(booking_code).update({"payment": final_amount})
                    return render_template("editBooking.html", event=event_queried, month=month,
                                           day=day, amount=amount, hour=hour,
                                           minute=minute, success="Payment Successful! Please Refresh This Page")
            else:
                first_name = request.form.get("firstName")
                last_name = request.form.get("lastName")
                email = request.form.get("email")
                number = request.form.get("number")
                event = request.form.get("event")
                people = request.form.get("people")
                date_out = toDateTime(request.form.get("event_time"))
                if over_booking(date_out, db):
                    if event_time.year == date_out.year and event_time.month == date_out.month \
                            and event_time.day == date_out.day:
                        pass
                    else:
                        return render_template("editBooking.html", errMessage="Day has already been booked",
                                               amount=amount, event=event_queried)
                event_time_new = str(date_out).replace(" ", "-").replace(":", "-")
                updated_event = event_dict(first_name=first_name, booking_code=booking_code,
                                           event_id=event_queried["id"], last_name=last_name,
                                           email=email, number=number, event=event, people=people,
                                           event_time=event_time_new)
                db.child("events").child(booking_code).update(updated_event)
                send_mail(mail, updated_event, "updated", date_out)
                return render_template("editBooking.html", event=event_queried, month=month,
                                       day=day, hour=hour, minute=minute, amount=amount,
                                       success="Update Successful! Please Refresh This Page")
        else:
            return render_template("editBooking.html", event=event_queried, month=month, day=day, hour=hour,
                                   amount=amount, minute=minute)
    else:
        return redirect("/viewBooking")


# Cancelling the reservation
@app.route("/cancel")
def cancel():
    if "booking_code" in session:
        booking_code = session["booking_code"]
        event = db.child("events").child(booking_code).get().val()
        db.child("events").child(booking_code).remove()
        send_mail(mail, event, "cancelled", string_to_datetime(event["event_time"]))
    return redirect("/viewBooking")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")
        msg_us = Message(
            f'A Message from {name}', sender='knightp550@gmail.com',
            recipients=['knightp550@gmail.com'])
        msg_us.body = f"""Name: {name}\nEmail: {email}\nMessage:\n{message}"""
        mail.send(msg_us)
        return render_template("contact.html", success="Message sent!")
    else:
        return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=True, port=4995)
