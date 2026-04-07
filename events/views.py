import json
from django.shortcuts import render, get_object_or_404, redirect
from .models import Event, Category, OrganizerRequest, User, ActivityLog, EventPass
from django.db.models import Q
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib import messages
from .forms import CustomUserCreationForm

def landing_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    featured_events = Event.objects.filter(is_approved=True).order_by('-date')[:3]
    return render(request, 'events/landing.html', {'featured_events': featured_events})

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_user = True
            user.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'events/register.html', {'form': form})

@login_required
def dashboard(request):
    if request.user.is_superuser:
        return redirect('admin_dashboard')
    elif request.user.is_organizer:
        return redirect('organizer_dashboard')
    else:
        return redirect('event_list') # User dashboard

# --- ADMIN DASHBOARD ---
@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Only Admins can view this page.")
    
    # Context data for Overview
    total_events = Event.objects.count()
    pending_requests = OrganizerRequest.objects.filter(is_approved=False).count() + Event.objects.filter(is_approved=False).count()
    active_organizers = User.objects.filter(is_organizer=True).count()
    approved_events = Event.objects.filter(is_approved=True).count()
    recent_activity = ActivityLog.objects.all().order_by('-created_at')[:5]

    # Context data for Tabs
    org_requests = OrganizerRequest.objects.filter(is_approved=False).order_by('-created_at')
    pending_events = Event.objects.filter(is_approved=False).order_by('-created_at')

    return render(request, 'events/admin_dashboard.html', {
        'total_events': total_events,
        'pending_requests': pending_requests,
        'active_organizers': active_organizers,
        'approved_events': approved_events,
        'recent_activity': recent_activity,
        'org_requests': org_requests,
        'pending_events': pending_events,
    })

@login_required
def approve_event(request, event_id):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Only Admins can approve events.")
    event = get_object_or_404(Event, id=event_id)
    if request.method == "POST":
        action = request.POST.get('action')
        if action == 'approve':
            event.is_approved = True
            event.save()
            ActivityLog.objects.create(action="Event approved", description=event.title)
        elif action == 'reject':
            event.delete()
    return redirect('/admin-dashboard/?tab=requests')

@login_required
def approve_organizer(request, req_id):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Only Admins can approve requests.")
    org_req = get_object_or_404(OrganizerRequest, id=req_id)
    if request.method == "POST":
        action = request.POST.get('action')
        if action == 'approve':
            org_req.user.is_organizer = True
            org_req.user.is_user = False
            org_req.user.save()
            org_req.is_approved = True
            org_req.save()
            ActivityLog.objects.create(action="Organizer request approved", description=org_req.user.username)
        elif action == 'reject':
            org_req.delete()
    return redirect('admin_dashboard')

# --- ORGANIZER DASHBOARD ---
@login_required
def organizer_dashboard(request):
    if not (request.user.is_organizer or request.user.is_superuser):
        return HttpResponseForbidden("Only Organizers can view this page.")
    my_events = Event.objects.filter(organizer=request.user).order_by('-date')
    
    context = {
        'events': my_events,
        'total_events': my_events.count(),
        'approved_events': my_events.filter(is_approved=True).count(),
        'pending_events': my_events.filter(is_approved=False).count(),
        'rejected_events': 0
    }
    return render(request, 'events/organizer_dashboard.html', context)

# --- USER FEATURES ---
@login_required
def request_organizer(request):
    if request.method == "POST":
        if not request.user.is_organizer and not request.user.is_superuser:
            obj, created = OrganizerRequest.objects.get_or_create(user=request.user)
            if created:
                ActivityLog.objects.create(action="New organizer request", description=request.user.username)
    return redirect('dashboard')

# LIST (User Dashboard)
def event_list(request):
    events = Event.objects.filter(is_approved=True)

    # SEARCH
    query = request.GET.get('q')
    if query:
        events = events.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(city__icontains=query) |
            Q(venue_name__icontains=query)
        )

    # CATEGORY
    category = request.GET.get('category')
    if category:
        events = events.filter(categories__name__icontains=category).distinct()

    # LOCATION
    location = request.GET.get('location')
    if location:
        events = events.filter(city__icontains=location)

    # DATE RANGE
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date and end_date:
        events = events.filter(date__range=[start_date, end_date])
    elif start_date:
        events = events.filter(date__gte=start_date)
    elif end_date:
        events = events.filter(date__lte=end_date)

    # SORT
    sort = request.GET.get('sort')
    if sort == 'latest':
        events = events.order_by('-date', '-time')
    elif sort == 'oldest':
        events = events.order_by('date', 'time')
        
    has_pending_request = False
    if request.user.is_authenticated and not request.user.is_organizer and not request.user.is_superuser:
        has_pending_request = OrganizerRequest.objects.filter(user=request.user, is_approved=False).exists()

    return render(request, 'events/event_list.html', {
        'events': events, 
        'has_pending_request': has_pending_request
    })

# DETAIL
def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    has_pass = False
    user_pass = None
    if request.user.is_authenticated:
        user_pass = EventPass.objects.filter(event=event, user=request.user, status='valid').first()
        has_pass = user_pass is not None
    return render(request, 'events/event_detail.html', {
        'event': event,
        'has_pass': has_pass,
        'user_pass': user_pass,
    })

def save_categories(event, categories_string):
    event.categories.clear()
    if categories_string:
        names = [n.strip() for n in categories_string.split(',')]
        for name in names:
            if name:
                cat_obj, created = Category.objects.get_or_create(name=name)
                event.categories.add(cat_obj)

# CREATE
@login_required
def event_create(request):
    if not (request.user.is_organizer or request.user.is_superuser):
        return HttpResponseForbidden("Only Organizers can create events.")
        
    if request.method == 'POST':
        event = Event.objects.create(
            title=request.POST['title'],
            description=request.POST.get('description', ''),
            organizer=request.user, # Assign correct user
            city=request.POST.get('city', ''),
            venue_name=request.POST.get('venue_name', ''),
            full_address=request.POST.get('full_address', ''),
            date=request.POST['date'],
            time=request.POST['time'],
            end_date=request.POST.get('end_date') or None,
            end_time=request.POST.get('end_time') or None,
            price=request.POST.get('price', ''),
            capacity=request.POST.get('capacity') or None,
            refund_policy=request.POST.get('refund_policy', ''),
            banner=request.FILES.get('banner'),
            is_approved=request.user.is_superuser
        )
        save_categories(event, request.POST.get('categories', ''))
        
        if not request.user.is_superuser:
            ActivityLog.objects.create(action="New event submitted", description=event.title)
            
        return redirect('event_detail', pk=event.pk)
        
    prefill_date = request.GET.get('date', '')
    return render(request, 'events/event_form.html', {'prefill_date': prefill_date})

# UPDATE
@login_required
def event_update(request, pk):
    event = get_object_or_404(Event, pk=pk)
    
    if event.organizer != request.user and not request.user.is_superuser:
        return HttpResponseForbidden("You can only edit your own events.")

    if request.method == 'POST':
        event.title = request.POST['title']
        event.description = request.POST.get('description', '')
        event.city = request.POST.get('city', '')
        event.venue_name = request.POST.get('venue_name', '')
        event.full_address = request.POST.get('full_address', '')
        event.date = request.POST['date']
        event.time = request.POST['time']
        event.end_date = request.POST.get('end_date') or None
        event.end_time = request.POST.get('end_time') or None
        event.price = request.POST.get('price', '')
        event.capacity = request.POST.get('capacity') or None
        event.refund_policy = request.POST.get('refund_policy', '')

        if request.FILES.get('banner'):
            event.banner = request.FILES.get('banner')
        
        event.save()
        save_categories(event, request.POST.get('categories', ''))
        return redirect('event_detail', pk=event.pk)

    current_categories = ", ".join([c.name for c in event.categories.all()])
    return render(request, 'events/event_form.html', {'event': event, 'current_categories': current_categories})

# DELETE
@login_required
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if event.organizer != request.user and not request.user.is_superuser:
        return HttpResponseForbidden("You can only delete your own events.")
        
    event.delete()
    return redirect('dashboard')

# CALENDAR
def calendar_view(request):
    events = Event.objects.filter(is_approved=True)
    event_data = []
    for event in events:
        cats = ", ".join([c.name for c in event.categories.all()])
        event_data.append({
            "title": event.title,
            "start": str(event.date),
            "description": event.description[:100] + "..." if len(event.description) > 100 else event.description,
            "category": cats,
            "time": str(event.time),
            "image": event.banner.url if event.banner else "",
            "id": event.id,
            "url": f"/event/{event.id}/"
        })
    return render(request, 'events/calendar.html', {'events': json.dumps(event_data)})

@login_required
def toggle_like(request, pk):
    if request.method == "POST":
        event = get_object_or_404(Event, pk=pk)
        if request.user in event.likes.all():
            event.likes.remove(request.user)
            liked = False
        else:
            event.likes.add(request.user)
            liked = True
        return JsonResponse({'liked': liked, 'count': event.likes.count()})
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def liked_events(request):
    events = request.user.liked_events.all()
    return render(request, 'events/event_list.html', {'events': events, 'is_liked_events_page': True})

# --- PASS SYSTEM ---
@login_required
def reserve_pass(request, event_id):
    event = get_object_or_404(Event, id=event_id, is_approved=True)
    
    # Check if user already has a valid pass
    existing = EventPass.objects.filter(event=event, user=request.user).first()
    if existing and existing.status == 'valid':
        messages.info(request, 'You already have a pass for this event.')
        return redirect('my_passes')
    
    # Check capacity
    if event.capacity and event.available_capacity <= 0:
        messages.error(request, 'Sorry, this event is sold out!')
        return redirect('event_detail', pk=event.id)
    
    if request.method == 'POST':
        if existing and existing.status == 'cancelled':
            # Reactivate cancelled pass
            existing.status = 'valid'
            existing.save()
        else:
            EventPass.objects.create(event=event, user=request.user)
        ActivityLog.objects.create(
            action="Pass reserved",
            description=f"{request.user.username} reserved a pass for {event.title}"
        )
        messages.success(request, 'Pass reserved successfully!')
        return redirect('my_passes')
    
    return render(request, 'events/reserve_pass.html', {'event': event})

@login_required
def my_passes(request):
    passes = EventPass.objects.filter(user=request.user).select_related('event').order_by('-purchase_date')
    return render(request, 'events/my_passes.html', {'passes': passes})

@login_required
def cancel_pass(request, pass_id):
    event_pass = get_object_or_404(EventPass, pass_id=pass_id, user=request.user)
    if request.method == 'POST':
        event_pass.status = 'cancelled'
        event_pass.save()
        ActivityLog.objects.create(
            action="Pass cancelled",
            description=f"{request.user.username} cancelled pass for {event_pass.event.title}"
        )
        messages.success(request, 'Your pass has been cancelled.')
    return redirect('my_passes')

@login_required
def manage_attendees(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if event.organizer != request.user and not request.user.is_superuser:
        return HttpResponseForbidden("You can only manage attendees for your own events.")
    passes = EventPass.objects.filter(event=event, status__in=['valid', 'used']).select_related('user').order_by('-purchase_date')
    return render(request, 'events/manage_attendees.html', {'event': event, 'passes': passes})