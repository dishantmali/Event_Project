from django.shortcuts import render, get_object_or_404, redirect
from .models import Event
from django.db.models import Q

# LIST
def event_list(request):
    events = Event.objects.all()

    # SEARCH
    query = request.GET.get('q')
    if query:
        events = events.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(location__icontains=query)
        )

    # CATEGORY
    category = request.GET.get('category')
    if category:
        events = events.filter(category__icontains=category)

    # LOCATION
    location = request.GET.get('location')
    if location:
        events = events.filter(location__icontains=location)

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

# CREATE
def event_create(request):
    if request.method == 'POST':
        Event.objects.create(
            title=request.POST['title'],
            description=request.POST['description'],
            location=request.POST['location'],
            date=request.POST['date'],
            time=request.POST['time'],
            category=request.POST['category'],
            banner=request.FILES.get('banner')
        )
        return redirect('event_list')
    return render(request, 'events/event_form.html')

# UPDATE
def event_update(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if request.method == 'POST':
        event.title = request.POST['title']
        event.description = request.POST['description']
        event.location = request.POST['location']
        event.date = request.POST['date']
        event.time = request.POST['time']
        event.category = request.POST['category']
        if request.FILES.get('banner'):
            event.banner = request.FILES.get('banner')
        event.save()
        return redirect('event_list')

    return render(request, 'events/event_form.html', {'event': event})


# DELETE
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)
    event.delete()
    return redirect('event_list')