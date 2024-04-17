from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import *
from .serializers import *
from rest_framework.views import APIView
import re
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics,serializers
from django.http import JsonResponse, HttpRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
from datetime import datetime,timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import requests
from django.conf import settings
from django.db.models import Q
from django.core.mail import send_mail,EmailMessage
from pytz import timezone



SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_credentials():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json')
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'zion.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def create_event(service, start_datetime_str, end_datetime_str, full_name, email, mobile_number):
    try:
        start_datetime = datetime.strptime(start_datetime_str, "%Y-%m-%d %H:%M:%S")
        end_datetime = datetime.strptime(end_datetime_str, "%Y-%m-%d %H:%M:%S")

        event = {
            'summary': 'Appointments',
            'start': {
                'dateTime': start_datetime.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': 'UTC',
            },
            'description': f'Booked by: {full_name}\nEmail: {email}\nMobile: {mobile_number}',
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        print(f'Event created: {event.get("htmlLink")}')
    except Exception as e:
        print(f"Error creating event: {e}")
        raise


@csrf_exempt
def create_google_calendar_event(request: HttpRequest):
    if request.method == 'POST':
        try:
            
            date = request.POST.get('date')
            time = request.POST.get('time')
            full_name = request.POST.get('full_name')
            email = request.POST.get('email')
            mobile_number = request.POST.get('mobile_number')
            start_datetime_str = f"{date} {time}"
            end_datetime_str = (datetime.strptime(start_datetime_str, "%Y-%m-%d %H:%M:%S") + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")

            creds = get_credentials()
            service = build('calendar', 'v3', credentials=creds)
            create_event(service, start_datetime_str, end_datetime_str, full_name, email, mobile_number)

            return JsonResponse({"message": "Event created successfully"}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)



class AvailableSlotListAPIView(generics.ListAPIView):
    serializer_class = AvailableSlotSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serialized_dates = [slot.date.strftime("%d %B") for slot in queryset]
        return Response(serialized_dates)

    def get_queryset(self):
    
        return AvailableSlot.objects.all()



class AvailableTimeView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = AvailableSlotSerializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        date = serializer.validated_data['date']
        available_slot = self.get_available_slot(date)
        if not available_slot:
            return Response({'error': 'No available slot for the given date'}, status=status.HTTP_404_NOT_FOUND)
        first_time_availability = TimeAvailability.objects.filter(available_slot=available_slot).first()

        if not first_time_availability:
            return Response({'error': 'No time availabilities found for the given date'}, status=status.HTTP_404_NOT_FOUND)

        serialized_data = TimeAvailabilitySerializer(first_time_availability).data
        return Response(serialized_data, status=status.HTTP_200_OK)

    def get_available_slot(self, date):
        try:
            return AvailableSlot.objects.get(date=date)
        except AvailableSlot.DoesNotExist:
            return None



def validate_time_format(time_str):
    # Define regular expression pattern for allowed time formats
    pattern = re.compile(r'^(1[0-2]|0?[1-9])(?::([0-5][0-9]))?\s?(AM|PM|am|pm)$')
    # Check if the time string matches the pattern
    match = pattern.match(time_str)
    if match:
        # Extract hour, minute, and period (AM/PM) from the time string
        hour, minute, period = match.groups()
        # Convert hour to 24-hour format if it's in AM/PM format
        if period.lower() == 'pm':
            hour = str(int(hour) + 12) if hour != '12' else '12'
        else:
            hour = '00' if hour == '12' else hour
        # Return the formatted time
        return f"{hour.zfill(2)}:{minute.zfill(2) if minute else '00'}:00"
    else:
        return None

class TimeValidationAPIView(APIView):
    def post(self, request):
        time_input = request.data.get('time')  # Assuming time is sent via POST request data
        if time_input:
            formatted_time = validate_time_format(time_input)
            if formatted_time:
                return Response({'message': 'Valid time format!', 'formatted_time': formatted_time}, status=status.HTTP_200_OK)
            else:
                return Response({'error': f'Time "{time_input}" is not in a valid format.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'error': 'Time parameter is missing.'}, status=status.HTTP_400_BAD_REQUEST)



class CheckTimeAvailabilityAPI(APIView):
    def post(self, request):
        date_str = request.data.get('date')
        time_str = request.data.get('time')
        if not date_str or not time_str:
            return Response({'error': 'Please provide a date and time'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            time = datetime.strptime(time_str, '%H:%M:%S').time()
        except ValueError:
            return Response({'error': 'Invalid date or time format. Please provide date in YYYY-MM-DD format and time in HH:MM:SS format'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            available_slot = AvailableSlot.objects.get(date=date)
        except AvailableSlot.DoesNotExist:
            return Response({'error': 'No available slot for the given date'}, status=status.HTTP_404_NOT_FOUND)
        
        time_availability = TimeAvailability.objects.filter(available_slot=available_slot, start_time__lte=time, end_time__gte=time).first()
        if time_availability:
            return Response({'message': 'Time is available'}, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'Time is not available'}, status=status.HTTP_400_BAD_REQUEST)





class LocationListCreateView(APIView):
    def get(self, request):
        
        locations = Location.objects.all()
        serializer = LocationSerializer(locations, many=True)
        addresses = [location["address"] for location in serializer.data]
        return Response(addresses)

    def post(self, request):
        serializer = LocationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['GET'])
def get_pdfdata(request):
    data = Pdfdata.objects.all()
    serializer = PdfdataSerializer(data, many=True)
    return Response(serializer.data)






class GetUrlByLocation(APIView):
    def post(self, request):
        serializer = LocationSerializer(data=request.data)
        if serializer.is_valid():
            address = serializer.validated_data.get('address')
            # Extract the first word from the address
            first_word = address.split()[0].strip()
            # Filter HomeURL objects by partial first word match
            try:
                home_url = HomeURL.objects.filter(
                    Q(location__address__istartswith=first_word)
                ).first()
                if home_url:
                    home_url_serializer = HomeURLSerializer(home_url)
                    return Response(home_url_serializer.data, status=status.HTTP_200_OK)
                else:
                    return Response({"detail": "URL not found for the given location."},
                                    status=status.HTTP_404_NOT_FOUND)
            except HomeURL.DoesNotExist:
                return Response({"detail": "URL not found for the given location."},
                                status=status.HTTP_404_NOT_FOUND)
        return Response({"detail": "Invalid data provided."},
                        status=status.HTTP_400_BAD_REQUEST)



class GetPdfByLocation(APIView):
    def post(self, request):
        # Deserialize the incoming data to get the location
        serializer = LocationSerializer(data=request.data)
        if serializer.is_valid():
            location = serializer.validated_data['address']

            # Retrieve the Pdfdata instance associated with the provided location
            try:
                pdf_data = Pdfdata.objects.get(location__address=location)
                pdf_serializer = PdfdataSerializer(pdf_data)
                return Response(pdf_serializer.data, status=status.HTTP_200_OK)
            except Pdfdata.DoesNotExist:
                return Response({"detail": "PDF not found for the given location."},
                                status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




# Function to validate the International Phone Numbers
def is_valid_phone_number(phone_number):
    pattern = r"^[+]{1}(?:[0-9\\-\\(\\)\\/""\\.]\\s?){11,13}[0-9]{1}$"
    if not phone_number:
        return False
    return bool(re.match(pattern, phone_number))

@csrf_exempt
def validate_phone(request):
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        is_valid = is_valid_phone_number(phone_number)

        if not is_valid:
            return JsonResponse({'error': 'Not a valid phone number'}, status=400)

        response = {
            'phone_number': phone_number,
            'is_valid': is_valid,
            'message': 'Valid phone number'
        }

        return JsonResponse(response)




@api_view(['POST'])
def validate_email(request):
    email = request.data.get('email')
    if not email:
        return Response({'error': 'Email address is required'}, status=400)

    pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    match = pattern.search(email)
    if match:
        return Response({'message': 'Valid email address'}, status=200)
    else:
        return Response({'error': 'Invalid email address'}, status=400)







class AppointmentCreateAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = AppointmentSerializer(data=request.data)
        if serializer.is_valid():

            formatted_date = serializer.validated_data['Date'].strftime("%d %B %Y")
            # formatted_time = serializer.validated_data['Time'].strftime("%I %p").replace(" ", "")
            formatted_time = serializer.validated_data['Time'].strftime("%I %p").lstrip("0").replace(" 0", " ") 


            subject_user = f'Your Viewing Appointment Confirmed for {serializer.validated_data["Location"]} on {formatted_date} at {formatted_time}'
            message_user = f'''Dear {serializer.validated_data["Name"]},

            
This email confirms your appointment to view your room at Location: {serializer.validated_data["Location"]} on Date: {formatted_date} at Time: {formatted_time}.\n\n A representative from Sila Estates will be there to greet you and show you the property. The viewing is expected to last approximately 15 minutes.\n\nPlease note: If you are no longer interested in viewing the apartment or need to reschedule for another time, kindly let us know as soon as possible by replying to this email. This will allow us to inform potential tenants on our waitlist.\n
We appreciate your cooperation in keeping the appointment or notifying us of any changes. We look forward to meeting you!

Sincerely,
Jamie Flynn
Property Viewings Associate
Sila Estates'''
            sender_email_user = settings.EMAIL_HOST_USER
            recipient_email_user = [serializer.validated_data["Email"]]
            send_mail(subject_user, message_user, sender_email_user, recipient_email_user, fail_silently=False)
            # serializer.save()
            subject_company = f'New Appointment Registered for {serializer.validated_data["Location"]} on {formatted_date} at {formatted_time}'
            message_company = f'''Dear Zion,

A new appointment has been registered with the following details:

Name: {serializer.validated_data["Name"]}
Email: {serializer.validated_data["Email"]}
Mobile No: {serializer.validated_data["Mobile_no"]}
Interested: {serializer.validated_data["Interested"]}
Location: {serializer.validated_data["Location"]}
Date: {formatted_date}
Time: {formatted_time}

Best regards,
Jamie Flynn
Property Viewings Associate
Sila Estates
'''

            sender_email_company = settings.EMAIL_HOST_USER
            recipient_email_company = [settings.COMPANY_EMAIL_ADDRESS]
            send_mail(subject_company, message_company, sender_email_company, recipient_email_company, fail_silently=False)
            serializer.save()

            print("Appointment registered successfully.")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            print("Errors occurred during appointment registration:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# cron job scheduler daily call at 8 am and send the reminder of that day booking on email address


def send_reminder_email_on_appointment_day(appointment):
    serializer = AppointmentSerializer(appointment)
    subject = f'Reminder: Viewing Appointment for {appointment.Location}'
    message = f'''Dear {appointment.Name},

This is a friendly reminder of your viewing appointment for the property at {serializer.data['Location']} on {serializer.data['formatted_date']} at {serializer.data['formatted_time']}.\n
If you need to reschedule or have any questions, please contact us at [Agent's Phone Number].\n
We look forward to showing you the property.

Best regards,
Jamie Flynn
Property Viewings Associate
Sila Estates
'''
    recipient_email = appointment.Email

    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [recipient_email],
    )

def check_email_appointments():
    print("Checking email appointments...")
    uk_time = datetime.now(timezone('Europe/London')) 
    print("UK time is:", uk_time.strftime("%Y-%m-%d %H:%M:%S")) 
    
    # Get appointments for today
    appointments = Appointment.objects.filter(Date=uk_time)
    
    for appointment in appointments:
        send_reminder_email_on_appointment_day(appointment)
        print(f'Reminder email sent on the day of appointment: {appointment.Date}.')

try:
    # scheduler = BackgroundScheduler(daemon=True)
    scheduler = BackgroundScheduler(timezone='Europe/London')
    scheduler.add_job(
        # check_email_appointments, trigger='cron', hour='*', minute='*/1',
        check_email_appointments, trigger='cron', year="*", month="*", day="*", hour="8", minute="0",
    )
    scheduler.start()

except Exception as e:
    print("Unexpected error:", e)




# cron job scheduler daily call at 8 am and send the reminder of that day booking on whatshapp


def send_appointment_reminder(appointment, message):
    recipient_number = appointment.Mobile_no
    print("=============recipient number=============")
    print(recipient_number)
    send_whatsapp_message(recipient_number, message)

def check_appointments():
    print("Checking appointments...")
    uk_time = datetime.now(timezone('Europe/London')) 
    print("UK time is:", uk_time.strftime("%Y-%m-%d %H:%M:%S"))
    
    # Query appointments scheduled for today
    appointments_same_day = Appointment.objects.filter(Date=uk_time)
    
    # Send reminders for appointments on the same day
    for appointment in appointments_same_day:
        serializer = AppointmentSerializer(appointment)
        message = f'''Dear {appointment.Name},

This is a friendly reminder of your viewing appointment for the property at {serializer.data['Location']} on {serializer.data['formatted_date']} at {serializer.data['formatted_time']}.\n
If you need to reschedule or have any questions, please contact us.\n
We look forward to showing you the property.

Best regards,
Jamie Flynn
Property Viewings Associate
Sila Estates
''' 
        send_appointment_reminder(appointment, message)

# Function to send WhatsApp message using the Facebook Graph API
def send_whatsapp_message(recipient_number, message):
    url ="https://graph.facebook.com/v18.0/282354704954659/messages"
    headers = {
        "Authorization": f"Bearer {settings.FACEBOOK_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_number,
        "type": "text",
        "text": {
            "preview_url": "false",
            "body": message
        }
    }
   
    print(payload)
    print("=========whatsapp message ==========")  
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        print("WhatsApp message sent successfully")
    else:
        print("Failed to send WhatsApp message")
        print(response.text)

try:
    # scheduler = BackgroundScheduler(daemon=True)
    scheduler = BackgroundScheduler(timezone='Europe/London')
    # scheduler.add_job(check_appointments,trigger='cron', hour='*', minute='*/1',)
    scheduler.add_job(check_appointments, trigger='cron', year="*", month="*", day="*", hour="8", minute="0")
    scheduler.start()
except Exception as e:
    print("Unexpected error:", e)






class AppointmentCreateAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = AppointmentSerializer(data=request.data)
        if serializer.is_valid():
            location_name = serializer.validated_data["Location"]
            location = Location.objects.filter(address__icontains=location_name).first()

            if location:
                location_address = location.address
            else:
                location_address = "Unknown"

            formatted_date = serializer.validated_data['Date'].strftime("%d %B %Y")
            formatted_time = serializer.validated_data['Time'].strftime("%I %p").lstrip("0").replace(" 0", " ") 

            subject_user = f'Your Viewing Appointment Confirmed for {location_address} on {formatted_date} at {formatted_time}'
            message_user = f'''Dear {serializer.validated_data["Name"]},
            
This email confirms your appointment to view your room at Location: {location_address} on Date: {formatted_date} at Time: {formatted_time}.\n\nA representative from Sila Estates will be there to greet and show you around the property. The viewing is expected to last approximately 15 minutes.\n\nPlease note: If you are no longer interested in viewing the property or need to reschedule for another time, kindly let us know as soon as possible by replying to this email. This will allow us to inform potential tenants on our waitlist.\n
We appreciate your cooperation in keeping the appointment or notifying us of any changes. We look forward to meeting you!

Sincerely,
Jamie Flynn
Property Viewings Associate
Sila Estates'''

            sender_email_user = settings.EMAIL_HOST_USER
            recipient_email_user = [serializer.validated_data["Email"]]
            send_mail(subject_user, message_user, sender_email_user, recipient_email_user, fail_silently=False)

            subject_company = f'New Appointment Registered for {location_name} on {formatted_date} at {formatted_time}'
            message_company = f'''Dear Zion,

A new appointment has been registered with the following details:

Name: {serializer.validated_data["Name"]}
Email: {serializer.validated_data["Email"]}
Mobile No: {serializer.validated_data["Mobile_no"]}
Interested: {serializer.validated_data["Interested"]}
Location: {location_address}
Date: {formatted_date}
Time: {formatted_time}

Best regards,
Jamie Flynn
Property Viewings Associate
Sila Estates
'''

            sender_email_company = settings.EMAIL_HOST_USER
            recipient_email_company = [settings.COMPANY_EMAIL_ADDRESS]
            send_mail(subject_company, message_company, sender_email_company, recipient_email_company, fail_silently=False)
            serializer.save()

            print("Appointment registered successfully.")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            print("Errors occurred during appointment registration:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

