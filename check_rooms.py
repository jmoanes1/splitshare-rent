import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from apps.properties.models import Room, Property
rooms = Room.objects.filter(
    availability=Room.Availability.AVAILABLE,
    property_listing__status=Property.Status.APPROVED,
    property_listing__is_published=True
)
print('Available approved published rooms:', rooms.count())
for r in rooms[:3]:
    print(f'  - {r.name}: {r.property_listing.title if r.property_listing else "No property"}')
    