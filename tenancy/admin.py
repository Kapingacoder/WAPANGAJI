from django.contrib import admin
from .models import Tenancy, Payment, MaintenanceRequest

@admin.register(Tenancy)
class TenancyAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'unit', 'start_date', 'months_paid', 'last_payment_date', 'is_active')
    list_filter = ('is_active', 'unit__property')
    search_fields = ('tenant__username', 'unit__unit_number', 'unit__property__name')
    autocomplete_fields = ('tenant', 'unit')
    readonly_fields = ('last_payment_date',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenancy', 'amount', 'date', 'status', 'method')
    list_filter = ('status', 'date', 'method')
    search_fields = ('tenancy__tenant__username', 'tenancy__unit__unit_number', 'tenancy__unit__property__name')
    list_select_related = ('tenancy__tenant', 'tenancy__unit', 'tenancy__unit__property')
    date_hierarchy = 'date'
    ordering = ('-date', '-created_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'tenancy__tenant', 'tenancy__unit', 'tenancy__unit__property'
        )

@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'tenant', 'status', 'submitted_at')
    list_filter = ('status', 'submitted_at')
    search_fields = ('title', 'notes', 'tenant__username')
    readonly_fields = ('submitted_at', 'updated_at')
    autocomplete_fields = ('tenant',)