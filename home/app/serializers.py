from rest_framework import serializers
from .models import *

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'

class PdfdataSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pdfdata
        fields = '__all__'


class AvailableSlotSerializer(serializers.ModelSerializer):
    date = serializers.DateField(format="%d %B")  

    class Meta:
        model = AvailableSlot
        fields = ['date']


# class TimeAvailabilitySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = TimeAvailability
#         fields = ['start_time', 'end_time']

class TimeAvailabilitySerializer(serializers.ModelSerializer):
    formatted_time_range = serializers.SerializerMethodField()

    class Meta:
        model = TimeAvailability
        fields = ['formatted_time_range']

    def get_formatted_time_range(self, obj):
        start_time = obj.start_time.strftime("%-I%p").lower()  # Use %-I for hour without leading zero
        end_time = obj.end_time.strftime("%-I%p").lower()  # Use %-I for hour without leading zero
        return f"{start_time} to {end_time}"

    
    
class HomeURLSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeURL
        fields = '__all__'



# class AppointmentSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Appointment
#         fields = '__all__'


class AppointmentSerializer(serializers.ModelSerializer):
    formatted_date = serializers.SerializerMethodField()
    formatted_time = serializers.SerializerMethodField()

    def get_formatted_date(self, obj):
        return obj.Date.strftime("%d %B %Y")

    # def get_formatted_time(self, obj):
    #     formatted_time = obj.Time.strftime("%I %p") 
    #     return formatted_time.replace(" ", "") 

    def get_formatted_time(self, obj):
        formatted_time = obj.Time.strftime("%I %p").lstrip("0").replace(" 0", " ")
        return formatted_time

    class Meta:
        model = Appointment
        fields = ['Name', 'Email', 'Mobile_no', 'Interested', 'Location', 'Date', 'Time', 'formatted_date', 'formatted_time','Home_url']
