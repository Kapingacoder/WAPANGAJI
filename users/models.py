from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('landlord', 'Landlord'),
        ('tenant', 'Tenant'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='Emergency Contact Name')
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Emergency Contact Phone')
    emergency_contact_relationship = models.CharField(max_length=50, blank=True, null=True, 
                                                   verbose_name='Relationship to Tenant')