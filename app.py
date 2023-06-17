from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_mail import Mail, Message
from utilities import MailError, send_mail, toDateTime, defaultDateTimeFormat

app = Flask(__name__)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'insert email here'
app.config['MAIL_PASSWORD'] = 'kdwfvudwwuhhemcy'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///events.db"
mail = Mail(app)
db = SQLAlchemy(app)
app.secret_key = "Something even more ominus"

# Event table
class Events(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_code = db.Column(db.Text, unique=True)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.Text, nullable=False)
    number = db.Column(db.Integer, nullable=False)
    event = db.Column(db.String(120), nullable=False)
    people = db.Column(db.Text, nullable=False)
    event_time = db.Column(db.DateTime, nullable=False)
    dep_ref_code = db.Column(db.Integer, unique=True, nullable=True)
    ref_code = db.Column(db.Integer, unique=True, nullable=True)
    payment = db.Column(db.Integer, default=0)

    def __repr__(self):
        return "Events" + str(self.id)

# Creates db within app context
def create_db():
    with app.app_context():
        db.create_all()

create_db()
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/services")
def services():
    return render_template("services.html")


@app.route("/gallery")
def gallary():
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
        # Converting from a HTML datetime object to a python datetime objct
        date_viewing = date_in.replace('T', '').replace(':', '').split('-')
        date_viewing = "".join(v for v in date_viewing)
        date_out = toDateTime(date_in)
        # Prevents making a reservation for a date that has passed
        if date_out < datetime.utcnow():
            return render_template("bookEvent.html", errMessage="Day has Passed")
        # Accounting for clashing reservations
        double_standard = Events.query.all()
        for i in double_standard:
            if i.event_time.year == date_out.year and i.event_time.month == date_out.month and i.event_time.day == date_out.day:
                return render_template("bookEvent.html", errMessage="Day has already been booked", event=event[0])
        get_id = Events.query.all()
        if len(get_id) == 0:
            id = 1
        else:
            # Created a reservation code based on information from the reservation
            id = get_id[-1].id + 1
        booking_code = event[2].lower() + event[0].lower() + \
            event[1].lower() + date_viewing + str(id)
        new_event = Events(first_name=first_name, booking_code=booking_code, last_name=last_name, email=email,
                           number=number, event=event, people=people, event_time=date_out)
        db.session.add(new_event)
        db.session.commit()
        send_mail(mail, new_event, "booked", date_out) # Automated email client. See 'utilities.py'
        
        return render_template("bookEvent.html", success="Event booked. You will receive an email shortly")
    else:
        return render_template("bookEvent.html")


# Portal to manage reservation
@app.route("/viewBooking", methods=["POST", "GET"])
def viewBooking():
    if request.method == "POST":
        booking_code = request.form.get("bookCode")
        event = Events.query.filter_by(booking_code=booking_code).all()
        if len(event) == 0 or event[0].event_time < datetime.utcnow():
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
        event = Events.query.filter_by(booking_code=booking_code).all()
        event_time = event[0].event_time
        month = defaultDateTimeFormat(event_time.month)
        day = defaultDateTimeFormat(event_time.day)
        hour = defaultDateTimeFormat(event_time.hour)
        minute = defaultDateTimeFormat(event_time.minute)
        payment = event[0].payment
        # Payment can be made either in half or fully. 
        if payment == 0:
            amount = 20000000
        elif payment <= 100000:
            amount = 10000000
        else:
            amount = 0
        # Verifying the transaction from paystack, a bit of added finantial security.
        if request.method == "POST":
            if  request.form.get("ref") != None:
                ref =  request.form.get("ref")
                from pypaystack.transactions import Transaction
                transactions = Transaction(authorization_key="sk_test_7e4d1f1b634b8817e2eb350f9bc4465b4c6c6295")
                response = transactions.verify(ref)
                if response[3]["status"] == "success" and response[3]["paid_at"] != None and response[2] == "Verification successful":
                    if int(response[3]["amount"] / 100) == 100000 and payment == 0:
                        event[0].dep_ref_code  = ref
                    else:
                        event[0].ref_code = ref
                    if payment == 0:
                        event[0].payment = int(response[3]["amount"] / 100)
                    else:
                        event[0].payment += int(response[3]["amount"] / 100)
                    db.session.commit()
                    return render_template("editBooking.html", event=event[0], month=month,
                                           day=day, amount=amount, hour=hour, 
                                           minute=minute, success="Payment Successful")
            else:
                event[0].first_name = request.form.get("firstName")
                event[0].last_name = request.form.get("lastName")
                event[0].email = request.form.get("email")
                event[0].number = request.form.get("number")
                event[0].event = request.form.get("event")
                event[0].people = request.form.get("people")
                time = toDateTime(request.form.get("event_time"))
                double_standard = Events.query.all()
                if toDateTime(request.form.get("event_time")) < datetime.utcnow():
                    return render_template("editBooking.html", errMessage="Day has passed", event=event[0])
                for i in double_standard:
                    if i.event_time.year == time.year and i.event_time.month == time.month and i.event_time.day == time.day and i.booking_code != booking_code:
                        return render_template("editBooking.html", errMessage="Day has already been booked", amount=amount, 
                                               event=event[0])
                event[0].event_time = toDateTime(request.form.get("event_time"))
                db.session.commit()
                send_mail(mail, event[0], "updated", time)
                return render_template("editBooking.html", event=event[0], month=month, 
                                       day=day, hour=hour, minute=minute, amount=amount, success="Update Successful")
        else:
            return render_template("editBooking.html", event=event[0], month=month, day=day, hour=hour, amount=amount, minute=minute)
    else:
        return redirect("/viewBooking")

# Cancelling the reservation
@app.route("/cancel/<int:id>")
def cancel(id):
    event = Events.query.get_or_404(id)
    db.session.delete(event)
    db.session.commit()
    send_mail(mail, event, "cancelled", event.event_time)
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
            f'A Message from {name}', sender='devtempmail1+cxuerseqxz@gmail.com', recipients=['devtempmail1+cxuerseqxz@gmail.com'])
        msg_us.body = f"""Name: {name}\nEmail: {email}\nMessage:\n{message}"""
        mail.send(msg_us)
        return render_template("contact.html", success="Message sent!")
    else:
        return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=True, port=4995)
