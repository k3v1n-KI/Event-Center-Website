"""
    This file contains helper functions and classes
"""

from flask_mail import Message
from datetime import datetime

# Custom error message for invalid mail criteria: ['booked', 'updated', 'cancelled'] 
class MailError(Exception):
    pass


def send_mail(mail_client, receiver, mail_criteria, date_out):
    mail_options = ["booked", "updated", "cancelled"]
    msg_client = Message(
            'Palm Center', sender='insert email here', recipients=[receiver.email])
    if mail_criteria.lower() not in mail_options:
        raise MailError("Invalid Mail Criteria. Expecting either 'booked', 'updated', or 'cancelled'") 
    msg_client.body = f"""Hi {receiver.first_name},\nYour event has been {mail_criteria}. 
    See details of your event below;\n
    Full Name: {receiver.first_name} {receiver.last_name}\nPhone Number: {receiver.number}\n
    Booking Code: {receiver.booking_code}\nEvent: {receiver.event}\n
    Number of People: {receiver.people}\nEvent Date: {date_out.strftime("%a, %B %d, %Y")}\n
    Event Time: {date_out.strftime("%I:%M %p")}"""
    mail_client.send(msg_client)
    
# Takes in HTML Datetime object and converts to Python Datetime Object
def toDateTime(html_dtObject):
    date_processing = html_dtObject.replace(
        'T', '-').replace(':', '-').split('-')
    date_processing = [int(v) for v in date_processing]
    date_out = datetime(*date_processing)
    return date_out

# Formats Datetime objects
def defaultDateTimeFormat(dt_object):
    if len(str(dt_object)) == 1:
        format_date = "0" + str(dt_object)
        return format_date
    return dt_object
