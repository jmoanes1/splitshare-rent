"""Property and room models for SharedSpace Philippines."""

from django.conf import settings
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Property(models.Model):
    """Property (house/condo/etc) owned by a user."""
    
    class PropertyType(models.TextChoices):
        HOUSE = 'HOUSE', 'House'
        APARTMENT = 'APARTMENT', 'Apartment'
        CONDO = 'CONDO', 'Condominium'
        TOWNHOUSE = 'TOWNHOUSE', 'Townhouse'
    
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PENDING_REVIEW = 'PENDING_REVIEW', 'Pending Review'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        SUSPENDED = 'SUSPENDED', 'Suspended'
    
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='properties', limit_choices_to={'role': 'OWNER'},
    )
    title = models.CharField('property title', max_length=200)
    description = models.TextField('property description')
    property_type = models.CharField(
        'property type', max_length=20, choices=PropertyType.choices,
        default=PropertyType.HOUSE,
    )
    region = models.CharField('region', max_length=100)
    province = models.CharField('province', max_length=100)
    city = models.CharField('city or municipality', max_length=100)
    barangay = models.CharField('barangay', max_length=100, blank=True)
    street_address = models.CharField('street address', max_length=200, blank=True)
    postal_code = models.CharField('postal code', max_length=20, blank=True)
    number_of_floors = models.PositiveIntegerField('number of floors', default=1)
    parking_available = models.BooleanField('parking available', default=False)
    house_rules = models.TextField('house rules', blank=True)
    property_amenities = models.TextField(
        'property amenities', blank=True,
        help_text='Comma-separated list (e.g. Wi-Fi, laundry, kitchen).',
    )
    shared_facilities = models.TextField(
        'shared facilities', blank=True,
        help_text='Comma-separated list (e.g. swimming pool, gym, parking).',
    )
    status = models.CharField(
        'status', max_length=20, choices=Status.choices,
        default=Status.DRAFT, db_index=True,
    )
    is_published = models.BooleanField('published', default=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['city', 'status', 'is_published']),
            models.Index(fields=['owner', 'status']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def location(self):
        parts = [p for p in [self.barangay, self.city, self.province, self.region] if p]
        return ', '.join(parts)
    
    @property
    def main_image(self):
        return self.images.filter(is_main=True).first() or self.images.first()


class PropertyImage(models.Model):
    """Images belonging to a Property."""
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name='images',
    )
    image = models.ImageField(
        upload_to='properties/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
    )
    is_main = models.BooleanField('main image', default=False)
    caption = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    
    class Meta:
        ordering = ['-is_main', 'created_at']


class Room(models.Model):
    """Room for rent within a Property."""
    
    class RoomType(models.TextChoices):
        PRIVATE = 'PRIVATE', 'Private Room'
        SHARED = 'SHARED', 'Shared Room'
        MASTERS = 'MASTERS', "Master's Room"
    
    class Availability(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        RESERVED = 'RESERVED', 'Reserved'
        OCCUPIED = 'OCCUPIED', 'Occupied'
        MAINTENANCE = 'MAINTENANCE', 'Maintenance'
        UNAVAILABLE = 'UNAVAILABLE', 'Unavailable'
    
    property_listing = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name='rooms',
    )
    name = models.CharField('room name', max_length=100)
    description = models.TextField('room description', blank=True)
    room_type = models.CharField(
        'room type', max_length=20, choices=RoomType.choices,
        default=RoomType.PRIVATE,
    )
    monthly_rent = models.DecimalField(
        'monthly rent', max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    weekly_rent = models.DecimalField(
        'weekly rent', max_digits=10, decimal_places=2,
        null=True, blank=True, validators=[MinValueValidator(0)],
    )
    room_size = models.PositiveIntegerField('room size (sqm)', null=True, blank=True)
    furnished = models.BooleanField('furnished', default=True)
    max_occupants = models.PositiveIntegerField('max occupants', default=1)
    bathroom_type = models.CharField(
        'bathroom type', max_length=20, default='SHARED',
        choices=[('PRIVATE', 'Private'), ('SHARED', 'Shared')],
    )
    room_amenities = models.TextField(
        'room amenities', blank=True,
        help_text='Comma-separated list (e.g. bed, desk, aircon).',
    )
    availability = models.CharField(
        'availability', max_length=20, choices=Availability.choices,
        default=Availability.AVAILABLE, db_index=True,
    )
    available_from = models.DateField('available from', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['property_listing', 'availability']),
            models.Index(fields=['monthly_rent', 'availability']),
        ]
    
    def __str__(self):
        return f'{self.name} -- {self.property_listing.title}'
    
    @property
    def main_image(self):
        return self.images.filter(is_main=True).first() or self.images.first()
    
    @property
    def is_bookable(self):
        return (
            self.availability == self.Availability.AVAILABLE
            and self.property_listing.status == Property.Status.APPROVED
            and self.property_listing.is_published
        )


class RoomImage(models.Model):
    """Images belonging to a Room."""
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name='images',
    )
    image = models.ImageField(
        upload_to='rooms/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
    )
    is_main = models.BooleanField('main image', default=False)
    caption = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    
    class Meta:
        ordering = ['-is_main', 'created_at']


class Booking(models.Model):
    """A renter's booking request for a room."""

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='bookings')
    renter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings',
    )
    message = models.TextField('message to owner', blank=True)
    status = models.CharField(
        'status', max_length=10, choices=Status.choices,
        default=Status.PENDING, db_index=True,
    )
    move_in_date = models.DateField('preferred move-in date', null=True, blank=True)
    requested_at = models.DateTimeField(default=timezone.now, editable=False)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']
        constraints = [
            models.UniqueConstraint(
                fields=['room', 'renter'],
                condition=models.Q(status__in=['PENDING', 'ACCEPTED']),
                name='unique_active_booking_per_room_renter',
            ),
        ]

    def __str__(self):
        return f'Booking #{self.pk} - {self.room} ({self.status})'


class SavedListing(models.Model):
    """A room a renter has saved to their shortlist."""

    renter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_listings',
    )
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['renter', 'room'], name='unique_saved_listing'),
        ]

    def __str__(self):
        return f'{self.renter.email} saved {self.room}'
