from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    # Add any extra fields if needed, or leave it as pass
    pass

class Category(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    organizer = models.CharField(max_length=200, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    venue_name = models.CharField(max_length=200, null=True, blank=True)
    full_address = models.TextField(null=True, blank=True)
    
    date = models.DateField()
    time = models.TimeField()
    end_date = models.DateField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    
    price = models.CharField(max_length=100, null=True, blank=True)
    refund_policy = models.CharField(max_length=200, null=True, blank=True)
    
    categories = models.ManyToManyField(Category, blank=True)
    banner = models.ImageField(upload_to='event_banners/', null=True, blank=True)
    likes = models.ManyToManyField(User, related_name='liked_events', blank=True)

    def __str__(self):
        return self.title