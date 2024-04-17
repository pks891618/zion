from django.contrib import admin
from app.models import *

# Register your models here.

admin.site.register(Location)
# admin.site.register(Pdfdata)
admin.site.register(AvailableSlot)
admin.site.register(TimeAvailability)
admin.site.register(HomeURL)

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['serial_number','Name', 'Email', 'Mobile_no', 'Location', 'Date', 'Time', 'Interested',  'Home_url']
    ordering = ('-id',)
    
    def serial_number(self, obj):
        return obj.id
    serial_number.short_description = 'Serial Number'