"""Public pages, role-based dashboards, bookings, and saved listings."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.accounts.decorators import admin_required, owner_required, renter_required
from apps.accounts.forms import BookingRequestForm
from apps.accounts.models import User, VerificationDocument
from apps.properties.models import Booking, Room, Property, SavedListing


def _saved_room_ids(user):
    if user.is_authenticated:
        return set(
            SavedListing.objects.filter(renter=user).values_list('room_id', flat=True)
        )
    return set()


def _available_rooms():
    return (
        Room.objects.select_related('property_listing', 'property_listing__owner')
        .filter(
            availability=Room.Availability.AVAILABLE,
            property_listing__status=Property.Status.APPROVED,
            property_listing__is_published=True,
        )
    )


def home(request):
    featured_rooms = _available_rooms().order_by('-created_at')[:6]
    available = _available_rooms()
    stats = {
        'rooms': available.count(),
        'cities': available.values('property_listing__city').distinct().count(),
        'hosts': available.values('property_listing__owner').distinct().count(),
    }
    return render(request, 'core/home.html', {
        'featured_rooms': featured_rooms,
        'saved_room_ids': _saved_room_ids(request.user),
        'stats': stats,
        'room_type_choices': Room.RoomType.choices,
    })


def about(request):
    return render(request, 'core/about.html')


@login_required
def dashboard(request):
    """Route every authenticated user to their role dashboard."""
    if request.user.role == User.Role.OWNER:
        return owner_dashboard(request)
    if request.user.role == User.Role.ADMIN or request.user.is_staff or request.user.is_superuser:
        return admin_dashboard(request)
    return renter_dashboard(request)


@renter_required
def renter_dashboard(request):
    profile = getattr(request.user, 'renter_profile', None)
    bookings = (
        Booking.objects.filter(renter=request.user)
        .select_related('room', 'room__property_listing', 'room__property_listing__owner')
    )
    active_rentals = bookings.filter(status=Booking.Status.ACCEPTED)
    saved_rooms = (
        Room.objects.filter(saved_by__renter=request.user)
        .select_related('property_listing')
    )
    return render(request, 'dashboard/renter.html', {
        'profile': profile,
        'verification_status': profile.verification_status if profile else 'PENDING',
        'bookings': bookings,
        'active_rentals': active_rentals,
        'saved_rooms': saved_rooms,
        'saved_room_ids': _saved_room_ids(request.user),
        'pending_count': bookings.filter(status=Booking.Status.PENDING).count(),
    })


@owner_required
def owner_dashboard(request):
    profile = getattr(request.user, 'owner_profile', None)
    properties = (
        Property.objects.filter(owner=request.user)
        .prefetch_related('rooms', 'images')
    )
    bookings = (
        Booking.objects.filter(room__property_listing__owner=request.user)
        .select_related('renter', 'room', 'room__property_listing')
    )
    pending_bookings = bookings.filter(status=Booking.Status.PENDING)
    rooms = Room.objects.filter(property_listing__owner=request.user)
    stats = {
        'properties': properties.count(),
        'rooms': rooms.count(),
        'available_rooms': rooms.filter(availability=Room.Availability.AVAILABLE).count(),
        'pending_requests': pending_bookings.count(),
        'active_rentals': bookings.filter(status=Booking.Status.ACCEPTED).count(),
    }
    return render(request, 'dashboard/owner.html', {
        'profile': profile,
        'verification_status': profile.verification_status if profile else 'PENDING',
        'properties': properties,
        'bookings': bookings,
        'pending_bookings': pending_bookings,
        'stats': stats,
    })


@admin_required
def admin_dashboard(request):
    stats = {
        'total_users': User.objects.count(),
        'total_renters': User.objects.filter(role=User.Role.RENTER).count(),
        'total_owners': User.objects.filter(role=User.Role.OWNER).count(),
        'total_admins': User.objects.filter(role=User.Role.ADMIN).count(),
        'total_properties': Property.objects.count(),
        'published_properties': Property.objects.filter(
            status=Property.Status.APPROVED, is_published=True,
        ).count(),
        'pending_properties': Property.objects.filter(status=Property.Status.PENDING_REVIEW).count(),
        'total_rooms': Room.objects.count(),
        'total_bookings': Booking.objects.count(),
        'pending_verifications': VerificationDocument.objects.filter(status='PENDING').count(),
        'database_ok': _database_ok(),
    }
    recent_users = User.objects.order_by('-date_joined')[:8]
    pending_documents = (
        VerificationDocument.objects.filter(status='PENDING').select_related('user')[:5]
    )
    return render(request, 'dashboard/admin.html', {
        'stats': stats,
        'recent_users': recent_users,
        'pending_documents': pending_documents,
    })


# --- Bookings ---------------------------------------------------------------

@renter_required
def booking_create(request, room_id):
    """Create a booking request for a room."""
    room = get_object_or_404(
        Room.objects.select_related('property_listing', 'property_listing__owner'),
        id=room_id,
        property_listing__status=Property.Status.APPROVED,
        property_listing__is_published=True,
    )

    if room.property_listing.owner == request.user:
        messages.error(request, 'You cannot book your own room.')
        return redirect('room_detail', room_id=room.id)

    if Booking.objects.filter(
        room=room, renter=request.user,
        status__in=[Booking.Status.PENDING, Booking.Status.ACCEPTED],
    ).exists():
        messages.info(request, 'You already have an active booking request for this room.')
        return redirect('room_detail', room_id=room.id)

    if not room.is_bookable:
        messages.error(request, 'This room is no longer available for booking.')
        return redirect('room_detail', room_id=room.id)

    form = BookingRequestForm(room, request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            room = Room.objects.select_for_update().get(pk=room.pk)
            if not room.is_bookable:
                messages.error(request, 'This room is no longer available for booking.')
                return redirect('room_detail', room_id=room.id)
            Booking.objects.get_or_create(
                room=room, renter=request.user,
                status__in=[Booking.Status.PENDING, Booking.Status.ACCEPTED],
                defaults={
                    'message': form.cleaned_data['message'],
                    'move_in_date': form.cleaned_data['move_in_date'],
                },
            )
        messages.success(request, 'Your booking request has been sent to the host.')
        return redirect('renter_dashboard')

    return render(request, 'accounts/booking_form.html', {'room': room, 'form': form})


@owner_required
def booking_requests(request):
    """List booking requests for the owner's rooms."""
    bookings = (
        Booking.objects.filter(room__property_listing__owner=request.user)
        .select_related('renter', 'room', 'room__property_listing')
    )
    return render(request, 'accounts/booking_requests.html', {
        'bookings': bookings,
        'pending_bookings': bookings.filter(status=Booking.Status.PENDING),
    })


@owner_required
@require_POST
def booking_action(request, booking_id):
    """Accept or reject a booking request."""
    action = request.POST.get('action')
    if action not in ('accept', 'reject'):
        messages.error(request, 'Invalid action.')
        return redirect('booking_requests')

    with transaction.atomic():
        booking = get_object_or_404(
            Booking.objects.select_for_update().select_related('room__property_listing'),
            id=booking_id, room__property_listing__owner=request.user,
        )
        if booking.status != Booking.Status.PENDING:
            messages.error(request, 'Only pending requests can be accepted or rejected.')
            return redirect('booking_requests')
        if action == 'accept':
            reserved = Room.objects.filter(
                pk=booking.room_id,
                availability=Room.Availability.AVAILABLE,
                property_listing__status=Property.Status.APPROVED,
                property_listing__is_published=True,
            ).update(availability=Room.Availability.RESERVED, updated_at=timezone.now())
            if not reserved:
                messages.error(request, 'This room is no longer available. Reject this request instead.')
                return redirect('booking_requests')
            booking.status = Booking.Status.ACCEPTED
            messages.success(request, f'Booking #{booking.id} has been accepted.')
        else:
            booking.status = Booking.Status.REJECTED
            rejection_reason = request.POST.get('rejection_reason', '').strip()
            if rejection_reason:
                booking.message += f'\n\nRejection reason: {rejection_reason}'
            messages.success(request, f'Booking #{booking.id} has been rejected.')
        booking.responded_at = timezone.now()
        booking.save(update_fields=['status', 'responded_at', 'message'])
    return redirect('booking_requests')


@renter_required
@require_POST
def booking_cancel(request, booking_id):
    """Renter withdraws a pending booking request."""
    booking = get_object_or_404(Booking, id=booking_id, renter=request.user)
    cancelled = Booking.objects.filter(pk=booking.pk, status=Booking.Status.PENDING).update(
        status=Booking.Status.CANCELLED, responded_at=timezone.now(),
    )
    if cancelled:
        messages.success(request, 'Your booking request has been cancelled.')
    else:
        messages.error(request, 'Only pending requests can be cancelled.')
    return redirect('renter_dashboard')


# --- Saved listings ---------------------------------------------------------

@renter_required
@require_POST
def toggle_saved(request, room_id):
    room = get_object_or_404(
        Room, id=room_id,
        property_listing__status=Property.Status.APPROVED,
        property_listing__is_published=True,
    )
    saved, created = SavedListing.objects.get_or_create(renter=request.user, room=room)
    if not created:
        saved.delete()
        messages.info(request, 'Removed from your saved listings.')
    else:
        messages.success(request, 'Saved to your shortlist.')
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect('room_detail', room_id=room.id)


def _database_ok():
    """Verify the database connection actually works."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            return cursor.fetchone() is not None
    except Exception:
        return False


# --- Error handlers ---------------------------------------------------------

def forbidden(request, exception=None):
    return render(request, 'errors/403.html', status=403)


def not_found(request, exception=None):
    return render(request, 'errors/404.html', status=404)


def server_error(request):
    return render(request, 'errors/500.html', status=500)