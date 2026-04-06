import json
from django.shortcuts import render, get_object_or_404, redirect
from .models import Event, Category
from django.db.models import Q
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .forms import CustomUserCreationForm

def landing_page(request):
    return render(request, 'events/landing.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('event_list')
    else:
        form = CustomUserCreationForm()
    return render(request, 'events/register.html', {'form': form})

# LIST
def event_list(request):
    events = Event.objects.all()

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

    # LOCATION (City)
    location = request.GET.get('location')  # Actually searching by city now
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

    # SORT (ALWAYS LAST)
    sort = request.GET.get('sort')
    if sort == 'latest':
        events = events.order_by('-date', '-time')
    elif sort == 'oldest':
        events = events.order_by('date', 'time')

    return render(request, 'events/event_list.html', {'events': events})

# DETAIL
def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    return render(request, 'events/event_detail.html', {'event': event})

# Helper function to handle saving categories
def save_categories(event, categories_string):
    event.categories.clear()
    if categories_string:
        names = [n.strip() for n in categories_string.split(',')]
        for name in names:
            if name:
                cat_obj, created = Category.objects.get_or_create(name=name)
                event.categories.add(cat_obj)

# CREATE
def event_create(request):
    if request.method == 'POST':
        event = Event.objects.create(
            title=request.POST['title'],
            description=request.POST.get('description', ''),
            organizer=request.POST.get('organizer', ''),
            city=request.POST.get('city', ''),
            venue_name=request.POST.get('venue_name', ''),
            full_address=request.POST.get('full_address', ''),
            date=request.POST['date'],
            time=request.POST['time'],
            end_date=request.POST.get('end_date') or None,
            end_time=request.POST.get('end_time') or None,
            price=request.POST.get('price', ''),
            refund_policy=request.POST.get('refund_policy', ''),
            banner=request.FILES.get('banner')
        )
        
        # Handle categories (Expect a comma-separated string like "Music, Party")
        save_categories(event, request.POST.get('categories', ''))

        return redirect('event_detail', pk=event.pk)
        
    prefill_date = request.GET.get('date', '')
    return render(request, 'events/event_form.html', {'prefill_date': prefill_date})

# UPDATE
def event_update(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if request.method == 'POST':
        event.title = request.POST['title']
        event.description = request.POST.get('description', '')
        event.organizer = request.POST.get('organizer', '')
        event.city = request.POST.get('city', '')
        event.venue_name = request.POST.get('venue_name', '')
        event.full_address = request.POST.get('full_address', '')
        event.date = request.POST['date']
        event.time = request.POST['time']
        event.end_date = request.POST.get('end_date') or None
        event.end_time = request.POST.get('end_time') or None
        event.price = request.POST.get('price', '')
        event.refund_policy = request.POST.get('refund_policy', '')

        if request.FILES.get('banner'):
            event.banner = request.FILES.get('banner')
        
        event.save()
        
        save_categories(event, request.POST.get('categories', ''))

        return redirect('event_detail', pk=event.pk)

    # For pre-filling the categories field in the frontend as "Music, Party"
    current_categories = ", ".join([c.name for c in event.categories.all()])
    return render(request, 'events/event_form.html', {'event': event, 'current_categories': current_categories})

# DELETE
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)
    event.delete()
    return redirect('event_list')

# CALENDAR
def calendar_view(request):
    events = Event.objects.all()

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

    return render(request, 'events/calendar.html', {
        'events': json.dumps(event_data)
    })

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