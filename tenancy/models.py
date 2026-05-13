from django.db import models
from django.conf import settings
from properties.models import Unit

class Tenancy(models.Model):
    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'tenant'},
        related_name='tenancies'
    )
    unit = models.OneToOneField(
        Unit,
        on_delete=models.CASCADE,
        related_name='tenancy_details'
    )
    start_date = models.DateField()
    months_paid = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    last_payment_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Tenancy for {self.unit} by {self.tenant.username}"

    class Meta:
        verbose_name_plural = "Tenancies"

class MaintenanceRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    ]
    tenant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='maintenance_requests')
    title = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    photo = models.ImageField(upload_to='maintenance_photos/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.status})"

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = "Maintenance Request"
        verbose_name_plural = "Maintenance Requests"


class Payment(models.Model):
    STATUS_CHOICES = [
        ('Paid', 'Paid'),
        ('Pending', 'Pending'),
        ('Late', 'Late'),
        ('Failed', 'Failed'),
        ('Refunded', 'Refunded'),
    ]
    
    PAYMENT_METHODS = [
        ('Cash', 'Cash'),
        ('Cheque', 'Cheque'),
        ('Other', 'Other'),
    ]
    
    tenancy = models.ForeignKey(Tenancy, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    method = models.CharField(max_length=50, choices=PAYMENT_METHODS, default='M-Pesa')
    reference_number = models.CharField('Reference/Receipt Number', max_length=100, blank=True, 
                                      help_text='Payment reference or receipt number')
    description = models.TextField(blank=True, help_text='Additional payment details or notes')
    transaction_id = models.CharField('Transaction ID', max_length=100, blank=True, 
                                    help_text='Payment gateway transaction ID')
    payment_proof = models.FileField(upload_to='payment_proofs/', blank=True, null=True,
                                   help_text='Upload payment receipt or proof')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                 null=True, related_name='payments_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                 null=True, related_name='payments_updated')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment of TZS {self.amount} for {self.tenancy} ({self.status})"
        
    def save(self, *args, **kwargs):
        # Auto-generate reference number if not provided
        if not self.reference_number:
            from django.utils import timezone
            from django.utils.crypto import get_random_string
            date_str = timezone.now().strftime('%Y%m%d')
            random_str = get_random_string(6, '0123456789')
            self.reference_number = f'PAY-{date_str}-{random_str}'
            
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = "Payment"
        verbose_name_plural = "Payments"


class Document(models.Model):
    """Document model for storing tenant agreements, house rules, etc."""
    DOCUMENT_TYPES = [
        ('Lease Agreement', 'Lease Agreement'),
        ('House Rules', 'House Rules'),
        ('Tenant Handbook', 'Tenant Handbook'),
        ('Maintenance Policy', 'Maintenance Policy'),
        ('Payment Terms', 'Payment Terms'),
        ('Other', 'Other'),
    ]
    
    property = models.ForeignKey('properties.Property', on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES, default='Other')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='documents/')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                   null=True, related_name='documents_uploaded')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.title} - {self.property.name}"
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "Document"
        verbose_name_plural = "Documents"
        verbose_name_plural = "Payments"