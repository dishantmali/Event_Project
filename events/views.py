import json
import base64
from io import BytesIO
from django.shortcuts import render, get_object_or_404, redirect
from .models import Event, Category, OrganizerRequest, User, ActivityLog, EventPass, TicketType, AttendeeTicket
from django.db.models import Q
from decimal import Decimal
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

# --- ADMIN EVENT LIST ---
@login_required
def admin_event_list(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Only Admins can view this page.")
    
    events = Event.objects.all()

    # SEARCH
    query = request.GET.get('q')
    if query:
        events = events.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(city__icontains=query) |
            Q(venue_name__icontains=query) |
            Q(organizer__username__icontains=query)
        )

    # STATUS FILTER
    status = request.GET.get('status')
    if status == 'approved':
        events = events.filter(is_approved=True)
    elif status == 'pending':
        events = events.filter(is_approved=False)

    # LOCATION
    location = request.GET.get('location')
    if location:
        events = events.filter(city__icontains=location)

    # SORT
    sort = request.GET.get('sort')
    if sort == 'latest':
        events = events.order_by('-date', '-time')
    elif sort == 'oldest':
        events = events.order_by('date', 'time')
    elif sort == 'title':
        events = events.order_by('title')
    else:
        events = events.order_by('-created_at')

    context = {
        'events': events,
        'total_events': Event.objects.count(),
        'approved_events': Event.objects.filter(is_approved=True).count(),
        'pending_events': Event.objects.filter(is_approved=False).count(),
        'active_organizers': User.objects.filter(is_organizer=True).count(),
    }
    return render(request, 'events/admin_event_list.html', context)

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
            capacity=None,
            refund_policy=request.POST.get('refund_policy', ''),
            banner=request.FILES.get('banner'),
            is_approved=request.user.is_superuser
        )
        save_categories(event, request.POST.get('categories', ''))

        tt_names = request.POST.getlist('tt_name[]')
        tt_adults = request.POST.getlist('tt_adult[]')
        tt_childs = request.POST.getlist('tt_child[]')
        tt_caps = request.POST.getlist('tt_capacity[]')
        for i in range(len(tt_names)):
            if tt_names[i].strip():
                try:
                    cap = int(tt_caps[i]) if i < len(tt_caps) and tt_caps[i] else None
                except ValueError:
                    cap = None
                TicketType.objects.create(
                    event=event,
                    name=tt_names[i].strip(),
                    price_adult=tt_adults[i] or 0.00,
                    price_child=tt_childs[i] or 0.00,
                    available_quantity=cap
                )
        
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
        
        event.refund_policy = request.POST.get('refund_policy', '')

        if request.FILES.get('banner'):
            event.banner = request.FILES.get('banner')
        
        event.save()
        save_categories(event, request.POST.get('categories', ''))

        tt_names = request.POST.getlist('tt_name[]')
        tt_adults = request.POST.getlist('tt_adult[]')
        tt_childs = request.POST.getlist('tt_child[]')
        tt_caps = request.POST.getlist('tt_capacity[]')
        
        current_names = []
        for i in range(len(tt_names)):
            name = tt_names[i].strip()
            if name:
                current_names.append(name)
                try:
                    cap = int(tt_caps[i]) if i < len(tt_caps) and tt_caps[i] else None
                except ValueError:
                    cap = None
                tt, created = TicketType.objects.get_or_create(event=event, name=name)
                tt.price_adult = tt_adults[i] or 0.00
                tt.price_child = tt_childs[i] or 0.00
                tt.available_quantity = cap
                tt.save()
        
        TicketType.objects.filter(event=event).exclude(name__in=current_names).delete()

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

    if request.method == 'POST':
        ticket_types = event.ticket_types.all()
        if ticket_types.exists():
            ticket_selections = []
            valid_qty = 0
            total_amount = Decimal('0.00')

            for tt in ticket_types:
                adult_qty = int(request.POST.get(f'tt_qty_adult_{tt.id}', 0))
                child_qty = int(request.POST.get(f'tt_qty_child_{tt.id}', 0))
                valid_qty += adult_qty + child_qty

                if tt.available_quantity is not None:
                    sold_for_tt = AttendeeTicket.objects.filter(
                        ticket_type=tt, event_pass__status__in=['valid', 'used']
                    ).count()
                    if (sold_for_tt + adult_qty + child_qty) > tt.available_quantity:
                        messages.error(request, f'Not enough capacity left for {tt.name}.')
                        return redirect('reserve_pass', event_id=event.id)

                if adult_qty > 0 or child_qty > 0:
                    ticket_selections.append({
                        'tt_id': tt.id,
                        'tt_name': tt.name,
                        'adult_qty': adult_qty,
                        'child_qty': child_qty,
                        'price_adult': str(tt.price_adult),
                        'price_child': str(tt.price_child),
                    })
                    total_amount += tt.price_adult * adult_qty
                    total_amount += tt.price_child * child_qty

            if valid_qty == 0:
                messages.error(request, 'Please select at least one ticket.')
                return redirect('reserve_pass', event_id=event.id)

            # Store in session → go to attendee details
            request.session['ticket_selections'] = ticket_selections
            request.session['reserve_event_id'] = event.id
            request.session['total_amount'] = str(total_amount)
            return redirect('attendee_details')
        else:
            # Free event with no ticket types
            EventPass.objects.create(event=event, user=request.user)
            ActivityLog.objects.create(
                action="Pass reserved",
                description=f"{request.user.username} reserved a pass for {event.title}"
            )
            messages.success(request, 'Pass reserved successfully!')
            return redirect('my_passes')

    return render(request, 'events/reserve_pass.html', {'event': event})


@login_required
def attendee_details(request):
    ticket_selections = request.session.get('ticket_selections')
    event_id = request.session.get('reserve_event_id')
    total_amount = request.session.get('total_amount', '0.00')

    if not ticket_selections or not event_id:
        messages.error(request, 'Your session expired. Please select tickets again.')
        return redirect('event_list')

    event = get_object_or_404(Event, id=event_id, is_approved=True)

    # Build a flat list of individual attendee slots
    attendee_slots = []
    for sel in ticket_selections:
        for _ in range(sel['adult_qty']):
            attendee_slots.append({
                'tt_id': sel['tt_id'],
                'tt_name': sel['tt_name'],
                'attendee_type': 'adult',
                'attendee_type_display': 'Adult',
                'price': sel['price_adult'],
            })
        for _ in range(sel['child_qty']):
            attendee_slots.append({
                'tt_id': sel['tt_id'],
                'tt_name': sel['tt_name'],
                'attendee_type': 'child',
                'attendee_type_display': 'Child',
                'price': sel['price_child'],
            })

    if request.method == 'POST':
        total = Decimal('0.00')
        tickets_data = []
        previous_email = ''

        for i, slot in enumerate(attendee_slots):
            name = request.POST.get(f'attendee_name_{i}', '').strip()
            age_raw = request.POST.get(f'attendee_age_{i}', '').strip()
            typed_email = request.POST.get(f'attendee_email_{i}', '').strip()

            # For attendee 2+, user can choose to reuse previous attendee's email.
            if i > 0 and request.POST.get(f'use_previous_email_{i}'):
                email = previous_email
            else:
                email = typed_email

            if i == 0 and not email:
                email = request.user.email

            if not name:
                messages.error(request, f'Please enter a name for attendee {i + 1}.')
                return redirect('attendee_details')
            if not age_raw.isdigit() or int(age_raw) < 1:
                messages.error(request, f'Please enter a valid age for attendee {i + 1}.')
                return redirect('attendee_details')
            if not email:
                messages.error(request, f'Please enter an email for attendee {i + 1}.')
                return redirect('attendee_details')

            price = Decimal(slot['price'])
            total += price
            tickets_data.append({
                'tt_id': slot['tt_id'],
                'attendee_type': slot['attendee_type'],
                'price_paid': price,
                'attendee_name': name,
                'attendee_age': int(age_raw),
                'attendee_email': email,
            })
            previous_email = email

        event_pass = EventPass.objects.create(
            event=event,
            user=request.user,
            total_amount=total
        )

        for t in tickets_data:
            tt = TicketType.objects.get(id=t['tt_id'])
            AttendeeTicket.objects.create(
                event_pass=event_pass,
                ticket_type=tt,
                attendee_type=t['attendee_type'],
                price_paid=t['price_paid'],
                attendee_name=t['attendee_name'],
                attendee_age=t['attendee_age'],
                attendee_email=t['attendee_email'],
            )

        ActivityLog.objects.create(
            action="Pass reserved",
            description=f"{request.user.username} reserved {len(tickets_data)} tickets for {event.title} (pass_id {event_pass.pass_id})"
        )

        # Clear session
        request.session.pop('ticket_selections', None)
        request.session.pop('reserve_event_id', None)
        request.session.pop('total_amount', None)

        messages.success(request, f'Successfully reserved {len(tickets_data)} tickets!')
        return redirect('pass_detail', pass_id=event_pass.pass_id)

    return render(request, 'events/attendee_details.html', {
        'event': event,
        'attendee_slots': attendee_slots,
        'total_amount': total_amount,
        'user_email': request.user.email,
    })

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
    if event.ticket_types.exists():
        total_attendees = AttendeeTicket.objects.filter(event_pass__in=passes).count()
    else:
        total_attendees = passes.count()
    return render(request, 'events/manage_attendees.html', {'event': event, 'passes': passes, 'total_attendees': total_attendees})

@login_required
def pass_detail(request, pass_id):
    event_pass = get_object_or_404(EventPass, pass_id=pass_id, user=request.user)
    qr_payload = str(event_pass.pass_id)
    qr_data_uri = None
    try:
        import qrcode
        qr_img = qrcode.make(qr_payload)
        buffer = BytesIO()
        qr_img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        qr_data_uri = f"data:image/png;base64,{qr_base64}"
    except Exception:
        qr_data_uri = None

    return render(request, 'events/pass_detail.html', {
        'event_pass': event_pass,
        'qr_data_uri': qr_data_uri,
        'qr_payload': qr_payload,
    })