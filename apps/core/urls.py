from django.urls import path

from apps.core import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/renter/', views.renter_dashboard, name='renter_dashboard'),
    path('dashboard/owner/', views.owner_dashboard, name='owner_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    # Booking URLs
    path('room/<int:room_id>/book/', views.booking_create, name='booking_create'),
    path('booking/requests/', views.booking_requests, name='booking_requests'),
    path('booking/<int:booking_id>/action/', views.booking_action, name='booking_action'),
    path('booking/<int:booking_id>/cancel/', views.booking_cancel, name='booking_cancel'),
    path('room/<int:room_id>/save/', views.toggle_saved, name='toggle_saved'),
]
