from django.urls import path

from apps.properties import views

urlpatterns = [
    path('browse/', views.browse_rooms, name='browse_rooms'),
    path('room/<int:room_id>/', views.room_detail, name='room_detail'),
    path('become-a-host/', views.become_a_host, name='become_a_host'),
]

