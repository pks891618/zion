from django.urls import path
from. import views 
from .views import *

# urlpatterns = [
#     path('locations/', views.handle_locations, name='location-list'),
# ]



urlpatterns = [
    path('locations/', LocationListCreateView.as_view(), name='location-list-create'),
    path('pdf/', views.get_pdfdata, name='pdf-list'),
    path('get_pdf/', GetPdfByLocation.as_view(), name='get-pdf-by-location'),
    path('get_url/', GetUrlByLocation.as_view(), name='get-url-by-location'),
    path('available-slots/', AvailableSlotListAPIView.as_view(), name='available_slots_api'),
    path('validate_phone/', validate_phone, name='validate_phone'),
    path('available-time/', AvailableTimeView.as_view(), name='available-time'),
    path('time/', TimeValidationAPIView.as_view(), name='check_time'),
    path('check-time-availability/', CheckTimeAvailabilityAPI.as_view(), name='check-time-availability'),
    path('create_event/', create_google_calendar_event, name='create_event'),
    path('validate/', validate_email, name='validate_email'),
    path('appointment/', AppointmentCreateAPIView.as_view(), name='appointment_create'),
]


