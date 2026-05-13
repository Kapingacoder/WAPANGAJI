from django.contrib import admin
from .models import Property, Unit

class UnitInline(admin.TabularInline):
    model = Unit
    extra = 1  # Show one extra blank form for a new unit

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('name', 'landlord', 'address')
    list_filter = ('landlord',)
    search_fields = ('name', 'address')
    inlines = [UnitInline]

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('unit_number', 'property', 'rent_amount', 'is_occupied', 'tenant')
    list_filter = ('property', 'is_occupied')
    search_fields = ('unit_number', 'tenant__username')