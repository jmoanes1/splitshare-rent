"""Property and room views for public browsing (Phase 2)."""

from decimal import Decimal, InvalidOperation

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from apps.properties.models import Room, Property


def browse_rooms(request):
    """Public room listing with search, filters, sorting, and pagination.

    Only shows rooms in approved, published properties that are available.
    """
    rooms = (
        Room.objects.select_related('property_listing', 'property_listing__owner')
        .filter(
            availability=Room.Availability.AVAILABLE,
            property_listing__status=Property.Status.APPROVED,
            property_listing__is_published=True,
        )
        .order_by('-created_at')
    )

    # Search by location (city, province, region)
    query = request.GET.get('q', '').strip()
    if query:
        rooms = rooms.filter(
            Q(property_listing__city__icontains=query)
            | Q(property_listing__province__icontains=query)
            | Q(property_listing__region__icontains=query)
        )

    # Filter by city
    city = request.GET.get('city', '').strip()
    if city:
        rooms = rooms.filter(property_listing__city__iexact=city)

    # Filter by province
    province = request.GET.get('province', '').strip()
    if province:
        rooms = rooms.filter(property_listing__province__iexact=province)

    # Filter by max price
    max_price = request.GET.get('max_price', '').strip()
    price_error = False
    if max_price:
        try:
            amount = Decimal(max_price)
            if not amount.is_finite() or amount < 0:
                raise InvalidOperation
            amount = min(amount, Decimal('99999999.99'))
            rooms = rooms.filter(monthly_rent__lte=amount)
            max_price = format(amount, 'f')
        except InvalidOperation:
            max_price = ''
            price_error = True

    # Filter by room type
    room_type = request.GET.get('room_type', '').strip()
    if room_type in dict(Room.RoomType.choices):
        rooms = rooms.filter(room_type=room_type)

    # Filter by furnished
    furnished = request.GET.get('furnished', '').strip()
    if furnished in ('true', 'false'):
        rooms = rooms.filter(furnished=(furnished == 'true'))

    # Sorting
    sort = request.GET.get('sort', 'newest')
    if sort == 'price_asc':
        rooms = rooms.order_by('monthly_rent')
    elif sort == 'price_desc':
        rooms = rooms.order_by('-monthly_rent')
    else:  # newest
        rooms = rooms.order_by('-created_at')

    # Distinct filter values for the UI
    cities = (
        Property.objects.filter(status=Property.Status.APPROVED, is_published=True)
        .values_list('city', flat=True)
        .distinct()
        .order_by('city')
    )
    provinces = (
        Property.objects.filter(status=Property.Status.APPROVED, is_published=True)
        .values_list('province', flat=True)
        .distinct()
        .order_by('province')
    )

    paginator = Paginator(rooms, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    saved_room_ids = set()
    if request.user.is_authenticated:
        from apps.properties.models import SavedListing
        saved_room_ids = set(
            SavedListing.objects.filter(renter=request.user).values_list('room_id', flat=True)
        )

    context = {
        'page_obj': page_obj,
        'rooms': page_obj.object_list,
        'query': query,
        'city': city,
        'province': province,
        'max_price': max_price,
        'price_error': price_error,
        'room_type': room_type,
        'furnished': furnished,
        'sort': sort,
        'cities': cities,
        'provinces': provinces,
        'room_type_choices': Room.RoomType.choices,
        'saved_room_ids': saved_room_ids,
        'total_count': paginator.count,
    }
    return render(request, 'properties/browse_rooms.html', context)


def room_detail(request, room_id):
    """Room details page with image gallery and booking button."""
    room = get_object_or_404(
        Room.objects.select_related('property_listing', 'property_listing__owner'),
        id=room_id,
        property_listing__status=Property.Status.APPROVED,
        property_listing__is_published=True,
    )
    images = room.images.all()
    property_images = room.property_listing.images.all()
    similar_rooms = (
        Room.objects.select_related('property_listing')
        .filter(
            availability=Room.Availability.AVAILABLE,
            property_listing__status=Property.Status.APPROVED,
            property_listing__is_published=True,
            property_listing__city=room.property_listing.city,
        )
        .exclude(id=room.id)
        .order_by('-created_at')[:3]
    )
    saved_room_ids = set()
    user_booking = None
    if request.user.is_authenticated:
        from apps.properties.models import SavedListing, Booking
        saved_room_ids = set(
            SavedListing.objects.filter(renter=request.user).values_list('room_id', flat=True)
        )
        user_booking = Booking.objects.filter(
            room=room, renter=request.user,
            status__in=[Booking.Status.PENDING, Booking.Status.ACCEPTED],
        ).first()
    context = {
        'room': room,
        'property': room.property_listing,
        'images': images,
        'property_images': property_images,
        'owner': room.property_listing.owner,
        'similar_rooms': similar_rooms,
        'saved_room_ids': saved_room_ids,
        'user_booking': user_booking,
    }
    return render(request, 'properties/room_detail.html', context)


def become_a_host(request):
    """Become a Host landing page."""
    return render(request, 'properties/become_a_host.html')

