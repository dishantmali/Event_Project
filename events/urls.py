from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('organizer-dashboard/', views.organizer_dashboard, name='organizer_dashboard'),
    path('approve-organizer/<int:req_id>/', views.approve_organizer, name='approve_organizer'),
    path('approve-event/<int:event_id>/', views.approve_event, name='approve_event'),
    path('request-organizer/', views.request_organizer, name='request_organizer'),
    
    path('admin-events/', views.admin_event_list, name='admin_event_list'),
    path('events/', views.event_list, name='event_list'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='events/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('event/<int:pk>/', views.event_detail, name='event_detail'),
    path('create/', views.event_create, name='event_create'),
    path('update/<int:pk>/', views.event_update, name='event_update'),
    path('delete/<int:pk>/', views.event_delete, name='event_delete'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('event/<int:pk>/like/', views.toggle_like, name='toggle_like'),
    path('profile/liked-events/', views.liked_events, name='liked_events'),

    # Pass System
    path('event/<int:event_id>/reserve/', views.reserve_pass, name='reserve_pass'),
    path('my-passes/', views.my_passes, name='my_passes'),
    path('pass/<uuid:pass_id>/cancel/', views.cancel_pass, name='cancel_pass'),
    path('event/<int:event_id>/attendees/', views.manage_attendees, name='manage_attendees'),
]