from django.db import models


class Location(models.Model):
    address = models.CharField(max_length=50)
    
    
    def __str__(self):
        return self.address
    
class Pdfdata(models.Model):
    location= models.ForeignKey(Location,on_delete=models.CASCADE)
    pdf = models.FileField(upload_to='pdf_files/')
    
    def __str__(self):
        return str(self.location)
    
class AvailableSlot(models.Model):
    date = models.DateField()
    
    def __str__(self):
        return f"{self.date}"
    
class TimeAvailability(models.Model):
    available_slot = models.ForeignKey(AvailableSlot, on_delete=models.CASCADE)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.available_slot.date} - {self.start_time} to {self.end_time}"
    
    
    
class HomeURL(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    url = models.URLField()
    
    def __str__(self):
        return str(self.location)
    

class Appointment(models.Model):
    Name = models.CharField(max_length=100)
    Email = models.EmailField(max_length=100,)  
    Mobile_no = models.CharField(max_length=15,) 
    Interested = models.TextField()  
    Location = models.CharField(max_length=100)
    Date = models.DateField()
    Time = models.TimeField()
    Home_url = models.URLField()

    # def __str__(self):
    #     return f"{self.name} - {self.mobile_no} - {self.email} - {self.location} - {self.available_slot}- {self.time_availability}"

 