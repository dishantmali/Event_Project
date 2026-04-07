import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    is_user = models.BooleanField(default=True)
    is_organizer = models.BooleanField(default=False)

class OrganizerRequest(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Request by {self.user.username}"

class Category(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_events', null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    venue_name = models.CharField(max_length=200, null=True, blank=True)
    full_address = models.TextField(null=True, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    
    date = models.DateField()
    time = models.TimeField()
    end_date = models.DateField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    
    price = models.CharField(max_length=100, null=True, blank=True)
    refund_policy = models.CharField(max_length=200, null=True, blank=True)
    
    categories = models.ManyToManyField(Category, blank=True)
    banner = models.ImageField(upload_to='event_banners/', null=True, blank=True)
    likes = models.ManyToManyField(User, related_name='liked_events', blank=True)

    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    @property
    def available_capacity(self):
        if self.capacity is None:
            return None
        sold = self.passes.filter(status__in=['valid', 'used']).count()
        return max(self.capacity - sold, 0)

class ActivityLog(models.Model):
    action = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} - {self.description}"

class EventPass(models.Model):
    STATUS_CHOICES = [
        ('valid', 'Valid'),
        ('cancelled', 'Cancelled'),
        ('used', 'Used'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='passes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_passes')
    pass_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    purchase_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='valid')
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('event', 'user')

    def __str__(self):
        return f"Pass {self.pass_id} - {self.user.username} for {self.event.title}"