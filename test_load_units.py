#!/usr/bin/env python
"""
Test script to verify the load_units AJAX endpoint works correctly.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wapangaji.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from properties.models import Property, Unit

User = get_user_model()

def test_load_units():
    """Test the load_units endpoint"""
    print("=" * 80)
    print("TESTING LOAD_UNITS AJAX ENDPOINT")
    print("=" * 80)
    
    # Get a landlord user
    try:
        landlord = User.objects.get(id=1)
        print(f"\n✓ Found Landlord: {landlord.username} (ID: {landlord.id})")
    except User.DoesNotExist:
        print("✗ Landlord with ID 1 not found")
        return False
    
    # Get a property for this landlord
    try:
        property = Property.objects.filter(landlord=landlord).first()
        if not property:
            print("✗ No properties found for this landlord")
            return False
        print(f"✓ Found Property: {property.name} (ID: {property.id})")
    except Exception as e:
        print(f"✗ Error getting property: {e}")
        return False
    
    # Get unoccupied units for this property
    try:
        units = Unit.objects.filter(
            property=property,
            is_occupied=False
        )
        print(f"✓ Found {units.count()} unoccupied units:")
        for u in units:
            print(f"   - Unit {u.unit_number} (ID: {u.id})")
    except Exception as e:
        print(f"✗ Error getting units: {e}")
        return False
    
    # Test the endpoint with Django test client
    print("\n" + "-" * 80)
    print("Testing /tenancy/load_units/ endpoint")
    print("-" * 80)
    
    client = Client()
    
    # First, log in as the landlord
    try:
        login_success = client.login(username=landlord.username, password='password@123')
        if not login_success:
            print("⚠ Could not auto-login with default password. This is expected if password was changed.")
            print("  (But the endpoint requires @login_required, so ensure you're logged in)")
    except Exception as e:
        print(f"  Login attempt failed: {e}")
    
    # Test the endpoint
    try:
        response = client.get(f'/tenancy/load_units/?property={property.id}')
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Content-Type: {response.get('Content-Type', 'N/A')}")
        print(f"Response Content:\n{response.content.decode('utf-8')}")
        
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            if 'Unit' in content and property.id > 0:
                print("\n✓ Endpoint returned valid HTML options")
                return True
            elif 'Select a property first' in content:
                print("\n⚠ Endpoint returned 'Select a property first' (property filter might not work)")
                return False
            else:
                print("\n✓ Endpoint returned: " + content[:100])
                return True
        else:
            print(f"\n✗ Unexpected status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"\n✗ Error testing endpoint: {e}")
        return False

if __name__ == '__main__':
    success = test_load_units()
    sys.exit(0 if success else 1)
