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
    
    price = models.CharField(max_length=100, null=True, blank=True) # Legacy or display price
    refund_policy = models.CharField(max_length=200, null=True, blank=True)
    
    categories = models.ManyToManyField(Category, blank=True)
    banner = models.ImageField(upload_to='event_banners/', null=True, blank=True)
    likes = models.ManyToManyField(User, related_name='liked_events', blank=True)

    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    # Capacity is tracked per TicketType via TicketType.remaining_capacity

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
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"pass_id {self.pass_id} - {self.user.username} for {self.event.title}"

    @property
    def grouped_tickets(self):
        groups = {}
        for ticket in self.tickets.all():
            name = ticket.ticket_type.name if ticket.ticket_type else 'General'
            attendee = ticket.get_attendee_type_display()
            key = f"{name} ({attendee})"
            if key not in groups:
                groups[key] = {'count': 0, 'total': 0}
            groups[key]['count'] += 1
            groups[key]['total'] += ticket.price_paid
        
        return [
            {'label': k, 'count': v['count'], 'total': v['total']}
            for k, v in groups.items()
        ]

class TicketType(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='ticket_types')
    name = models.CharField(max_length=100)
    price_adult = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    price_child = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    available_quantity = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.event.title}"

    @property
    def remaining_capacity(self):
        if self.available_quantity is None:
            return None
        sold = self.attendeeticket_set.filter(
            event_pass__status__in=['valid', 'used']
        ).count()
        return max(self.available_quantity - sold, 0)
        
    @property
    def sold_count(self):
        return self.attendeeticket_set.filter(
            event_pass__status__in=['valid', 'used']
        ).count()

class AttendeeTicket(models.Model):
    ATTENDEE_CHOICES = [
        ('adult', 'Adult'),
        ('child', 'Child'),
    ]

    event_pass = models.ForeignKey(EventPass, on_delete=models.CASCADE, related_name='tickets')
    ticket_type = models.ForeignKey(TicketType, on_delete=models.SET_NULL, null=True)
    attendee_type = models.CharField(max_length=10, choices=ATTENDEE_CHOICES, default='adult')
    price_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        ticket_name = self.ticket_type.name if self.ticket_type else 'N/A'
        return f"{self.get_attendee_type_display()} - {ticket_name}"