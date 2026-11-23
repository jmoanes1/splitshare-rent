from django.contrib import admin

from apps.properties.models import Property, PropertyImage, Room, RoomImage


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1


class RoomImageInline(admin.TabularInline):
    model = RoomImage
    extra = 1


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'city', 'province', 'status', 'is_published', 'created_at')
    list_filter = ('status', 'is_published', 'property_type', 'province', 'city')
    search_fields = ('title', 'city', 'province', 'barangay', 'owner__email')
    list_editable = ('status', 'is_published')
    inlines = [PropertyImageInline]
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'property_listing', 'room_type', 'monthly_rent', 'availability', 'created_at')
    list_filter = ('availability', 'room_type', 'furnished', 'bathroom_type')
    search_fields = ('name', 'property_listing__title', 'property_listing__city')
    list_editable = ('availability',)
    inlines = [RoomImageInline]
    readonly_fields = ('created_at', 'updated_at')


admin.site.register(PropertyImage)
admin.site.register(RoomImage)

