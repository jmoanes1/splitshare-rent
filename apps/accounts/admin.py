from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import OwnerProfile, RenterProfile, User, VerificationDocument


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name', 'phone_number')
    ordering = ('-date_joined',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone_number', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )
    add_fieldsets = (
        (None, {'fields': ('email', 'password1', 'password2')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone_number', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )


@admin.register(RenterProfile)
class RenterProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'verification_status', 'created_at')
    list_filter = ('verification_status', 'employment_status')
    search_fields = ('user__email', 'first_name', 'last_name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(OwnerProfile)
class OwnerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'business_name', 'verification_status', 'created_at')
    list_filter = ('verification_status',)
    search_fields = ('user__email', 'first_name', 'last_name', 'business_name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(VerificationDocument)
class VerificationDocumentAdmin(admin.ModelAdmin):
    list_display = ('user', 'document_type', 'status', 'submitted_at', 'reviewed_by')
    list_filter = ('status', 'document_type', 'submitted_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('submitted_at', 'reviewed_at')
    list_editable = ('status',)
