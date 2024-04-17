
from datetime import datetime, timedelta, time
from django.core.mail import send_mail
from .models import Appointment
from django_apscheduler.jobstores import DjangoJobStore
# from django_apscheduler.schedulers import DjangoJobScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings



def send_reminder_email(appointment):
    subject = 'Reminder: Your appointment with  Sila Estates'
    message = f'Your appointment with  Sila Estates is scheduled for {appointment.Date}.'
    recipient_email = appointment.Email

    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [recipient_email],          
    )

def check_appointments():
    print("Checking appointments...")
    today = datetime.now().date()
    print("Today's date is:", today) 
    
    # Get appointments for today and upcoming appointments
    appointments = Appointment.objects.filter(Date__gte=today).order_by('Date')
    
    for appointment in appointments:
        days_remaining = (appointment.Date - today).days
        print(f"Days remaining for appointment on {appointment.Date}: {days_remaining}")
            
        if days_remaining == 2:
            send_reminder_email(appointment)
            print(f'Reminder email sent 2 days before appointment on {appointment.Date}.')

        if days_remaining == 1:
            send_reminder_email(appointment)
            print(f'Reminder email sent 1 days before appointment on {appointment.Date}.')

        elif days_remaining == 0:
            send_reminder_email_on_appointment_day(appointment)
            print(f'Reminder email sent on the day of appointment: {appointment.Date}.')


def send_reminder_email_on_appointment_day(appointment):
    subject = 'Reminder: Your appointment with Sila Estates'
    message = f'Your appointment with Sila Estates is scheduled for today ({appointment.Date}).'
    recipient_email = appointment.Email

    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [recipient_email],
    )
            

# scheduler = DjangoJobScheduler()
scheduler = BackgroundScheduler()


scheduler.add_job(
    check_appointments,
    trigger='cron',
    hour=9,
    id='check_appointments', 
    replace_existing=True,
)

# scheduler.add_job(
#     check_appointments,
#     trigger='interval',  
#     seconds=5,          
#     id='check_appointments', 
#     replace_existing=True,
# )


try:
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(check_appointments, trigger='cron', hour='*', minute='*/1',)
    scheduler.start()
except Exception as e:
    print("Unexpected error:", e)
