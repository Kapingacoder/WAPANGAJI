from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.forms import modelformset_factory
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.db import transaction

from .models import Property, Unit
from .forms import PropertyForm, UnitForm, UnitFormSet

# Properties Overview - Display all properties
def properties_list(request):
    """Display all properties in a responsive grid layout"""
    properties = Property.objects.filter(landlord=request.user)
    context = {
        'properties': properties,
        'page_title': 'Properties Overview'
    }
    return render(request, 'properties/properties_list.html', context)

# View Property Details
def property_detail(request, pk):
    """Display detailed information about a specific property"""
    property_obj = get_object_or_404(Property, pk=pk)
    
    # Handle unit addition
    if request.method == 'POST' and 'add_unit' in request.POST:
        try:
            unit_number = request.POST.get('unit_number', '').strip()
            rent_amount = float(request.POST.get('rent_amount', 0) or 0)
            is_occupied = request.POST.get('is_occupied') == 'on'
            
            if not unit_number:
                messages.error(request, 'Unit number is required')
            else:
                Unit.objects.create(
                    property=property_obj,
                    unit_number=unit_number,
                    rent_amount=rent_amount,
                    is_occupied=is_occupied
                )
                messages.success(request, f'Unit {unit_number} added successfully')
                return redirect('properties:property_detail', pk=pk)
                
        except Exception as e:
            messages.error(request, f'Error adding unit: {str(e)}')
    
    # Get all units for this property
    units = property_obj.units.all().order_by('unit_number')
    
    context = {
        'property': property_obj,
        'units': units,
        'status_choices': Property.STATUS_CHOICES,
        'page_title': f'{property_obj.name} - Details'
    }
    return render(request, 'properties/property_detail.html', context)

@login_required
def add_property(request):
    """
    View for adding a new property with its units.
    Handles both property and unit creation in a single form.
    """
    from .models import Property, Unit
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Debug: Print all POST data
                print("POST data:", request.POST)
                print("FILES:", request.FILES)
                
                # Get form data with proper type conversion
                name = request.POST.get('name', '').strip()
                address = request.POST.get('address', '').strip()
                location = request.POST.get('location', '').strip()
                description = request.POST.get('description', '').strip()
                
                try:
                    rooms = int(request.POST.get('rooms', 1))
                    rent = float(request.POST.get('rent', 0) or 0)
                except (ValueError, TypeError):
                    rooms = 1
                    rent = 0
                
                status = request.POST.get('status', 'vacant')
                utilities = request.POST.get('utilities', '').strip()
                
                # Validate required fields
                if not all([name, address, location]):
                    raise ValueError("Please fill in all required fields")
                
                # Create property
                property_obj = Property(
                    landlord=request.user,
                    name=name,
                    address=address,
                    location=location,
                    description=description,
                    rooms=rooms,
                    rent=rent,
                    status=status,
                    utilities=utilities
                )
                
                # Handle file upload if exists
                if 'image' in request.FILES:
                    property_obj.image = request.FILES['image']
                
                property_obj.save()
                print(f"Property saved with ID: {property_obj.id}")
                
                # Process units
                unit_numbers = request.POST.getlist('unit_number[]')
                unit_rents = request.POST.getlist('unit_rent[]')
                unit_statuses = request.POST.getlist('unit_status[]')
                
                # Create units
                for i in range(len(unit_numbers)):
                    if not unit_numbers[i].strip():
                        continue  # Skip empty unit numbers
                        
                    try:
                        unit_rent = float(unit_rents[i] or 0)
                    except (ValueError, TypeError):
                        unit_rent = 0
                    
                    # Only include fields that exist in the Unit model
                    unit_data = {
                        'property': property_obj,
                        'unit_number': unit_numbers[i].strip(),
                        'rent_amount': unit_rent,
                        'is_occupied': (unit_statuses[i] == 'occupied') if i < len(unit_statuses) else False
                    }
                    
                    unit = Unit.objects.create(**unit_data)
                    print(f"Created unit: {unit.unit_number} (Rent: {unit.rent_amount}, Occupied: {unit.is_occupied})")
                
                messages.success(request, f'Property "{property_obj.name}" and its units were added successfully!')
                return redirect('properties:property_detail', pk=property_obj.pk)
                
        except Exception as e:
            import traceback
            print("Error:", str(e))
            print(traceback.format_exc())
            
            messages.error(request, f'Error saving property: {str(e)}')
            
            # Re-render form with entered data
            context = {
                'form': {
                    'name': request.POST.get('name', ''),
                    'address': request.POST.get('address', ''),
                    'location': request.POST.get('location', ''),
                    'description': request.POST.get('description', ''),
                    'rooms': request.POST.get('rooms', 1),
                    'rent': request.POST.get('rent', ''),
                    'status': request.POST.get('status', 'vacant'),
                    'utilities': request.POST.get('utilities', '')
                },
                'units': zip(
                    request.POST.getlist('unit_number[]'),
                    request.POST.getlist('unit_rent[]'),
                    request.POST.getlist('unit_status[]'),
                    request.POST.getlist('unit_type[]'),
                    request.POST.getlist('unit_size[]'),
                    request.POST.getlist('unit_features[]')
                ),
                'status_choices': Property.STATUS_CHOICES
            }
            return render(request, 'properties/add_property.html', context)
    
    # GET request - show empty form
    context = {
        'form': {
            'name': '',
            'address': '',
            'location': '',
            'description': '',
            'rooms': 1,
            'rent': '',
            'status': 'vacant',
            'utilities': ''
        },
        'units': [],
        'status_choices': Property.STATUS_CHOICES
    }
    return render(request, 'properties/add_property.html', context)

@login_required
def edit_property(request, pk):
    """
    View for editing an existing property and its units.
    Uses a formset to handle multiple units.
    """
    property_obj = get_object_or_404(Property, pk=pk, landlord=request.user)
    
    if request.method == 'POST':
        property_form = PropertyForm(request.POST, request.FILES, instance=property_obj, prefix='property')
        unit_formset = UnitFormSet(request.POST, instance=property_obj, prefix='units')
        
        if property_form.is_valid() and unit_formset.is_valid():
            try:
                # Save the property
                property_obj = property_form.save()
                
                # Save the units
                units = unit_formset.save(commit=False)
                for unit in units:
                    unit.property = property_obj
                    unit.save()
                
                # Delete any units marked for deletion
                for obj in unit_formset.deleted_objects:
                    obj.delete()
                
                messages.success(request, f'Property "{property_obj.name}" updated successfully!')
                return redirect('landlord_property_detail', pk=property_obj.pk)
                
            except Exception as e:
                messages.error(request, f'Error updating property: {str(e)}')
        else:
            # Form validation failed
            messages.error(request, 'Please correct the errors below.')
    else:
        property_form = PropertyForm(instance=property_obj, prefix='property')
        unit_formset = UnitFormSet(instance=property_obj, prefix='units')
    
    context = {
        'property': property_obj,
        'property_form': property_form,
        'unit_formset': unit_formset,
        'page_title': f'Edit {property_obj.name}',
        'form_title': 'Edit Property',
        'submit_btn_text': 'Update Property',
        'form_id': 'edit-property-form',
    }
    return render(request, 'properties/property_form.html', context)

# Edit Unit
def edit_unit(request, pk):
    """Edit unit information"""
    unit = get_object_or_404(Unit, pk=pk)
    
    if request.method == 'POST':
        try:
            unit.unit_number = request.POST.get('unit_number', unit.unit_number)
            unit.rent_amount = request.POST.get('rent_amount', unit.rent_amount)
            unit.is_occupied = request.POST.get('is_occupied') == 'on'
            unit.save()
            messages.success(request, f'Unit {unit.unit_number} updated successfully.')
            return redirect('properties:property_detail', pk=unit.property.id)
        except Exception as e:
            messages.error(request, f'Error updating unit: {str(e)}')
    
    context = {
        'unit': unit,
        'page_title': f'Edit Unit {unit.unit_number}'
    }
    return render(request, 'properties/unit_edit.html', context)

# Delete Unit
def delete_unit(request, pk):
    """Remove a unit from a property"""
    unit = get_object_or_404(Unit, pk=pk)
    property_id = unit.property.id
    unit_number = unit.unit_number
    unit.delete()
    messages.success(request, f'Unit {unit_number} has been deleted successfully.')
    return redirect('properties:property_detail', pk=property_id)

# Delete Property
def delete_property(request, pk):
    """Remove a property from the system"""
    property_obj = get_object_or_404(Property, pk=pk)
    property_name = property_obj.name
    
    if request.method == 'POST':
        try:
            property_obj.delete()
            messages.success(request, f'Property "{property_name}" deleted successfully!')
            return redirect('properties:properties_list')
        except Exception as e:
            messages.error(request, f'Error deleting property: {str(e)}')
            return redirect('properties:property_detail', pk=property_obj.pk)
    
    context = {
        'property': property_obj,
        'page_title': f'Delete {property_obj.name}'
    }
    return render(request, 'properties/delete_property.html', context)

