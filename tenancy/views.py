import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Sum
from django.http import FileResponse, HttpResponse, JsonResponse
import json
import re

# Set up logging
logger = logging.getLogger(__name__)
from .models import Tenancy, MaintenanceRequest, Payment, Document
from communication.models import Message
from properties.models import Property, Unit
from .forms import TenantUserForm, TenancyForm, AddTenancyForm, PaymentForm
from django.contrib.auth import get_user_model

User = get_user_model()

# Tenant Dashboard - Main overview
@login_required(login_url='home:index')
def tenant_dashboard(request):
    """Display the main tenant dashboard with summary information"""
    try:
        # Get tenant's current tenancy
        tenancy = Tenancy.objects.filter(tenant=request.user, is_active=True).first()
        
        # Get unread message count
        unread_count = Message.objects.filter(
            recipient=request.user, 
            read_at__isnull=True
        ).count()
        
        # Get pending maintenance requests
        maintenance_count = MaintenanceRequest.objects.filter(
            tenant=request.user,
            status__in=['pending', 'in_progress']
        ).count()
        
        if not tenancy:
            context = {
                'page_title': 'Tenant Dashboard',
                'user': request.user,
                'tenancy': None,
                'rent_status': 'No Active Tenancy',
                'unread_count': unread_count,
                'maintenance_count': maintenance_count
            }
            return render(request, 'tenancy/tenant_dashboard.html', context)
        
        # Get property details
        property_obj = tenancy.unit.property
        
        # Calculate rent status (for demo purposes, assume monthly payments)
        from datetime import date, timedelta
        today = date.today()
        next_payment_day = property_obj.rent if hasattr(property_obj, 'rent') else 5
        
        # Determine next payment date (5th of next month)
        if today.day < 5:
            next_payment = today.replace(day=5)
        else:
            if today.month == 12:
                next_payment = today.replace(year=today.year + 1, month=1, day=5)
            else:
                next_payment = today.replace(month=today.month + 1, day=5)
        
        # Get messages for this tenant
        messages_list = Message.objects.filter(recipient=request.user).order_by('-sent_at')[:5]
        
        # Get maintenance requests count (real data)
        maintenance_requests_count = MaintenanceRequest.objects.filter(tenant=request.user).exclude(status='Completed').count()
        
        # Get payment information
        payments = Payment.objects.filter(tenancy=tenancy).order_by('-date', '-created_at')
        payment_stats = payments.aggregate(
            total_paid=Sum('amount', filter=Q(status='Paid')),
            total_pending=Sum('amount', filter=Q(status='Pending')),
            total_late=Sum('amount', filter=Q(status='Late')),
            total_all=Sum('amount')
        )
        
        total_paid = payment_stats['total_paid'] or 0
        total_pending = payment_stats['total_pending'] or 0
        total_late = payment_stats['total_late'] or 0
        total_all = payment_stats['total_all'] or 0
        rent_amount = property_obj.rent or 0
        balance = rent_amount - total_paid
        
        context = {
            'page_title': 'Tenant Dashboard',
            'tenancy': tenancy,
            'property': property_obj,
            'unit': tenancy.unit,
            'next_payment_date': next_payment,
            'unread_count': unread_count,
            'maintenance_count': maintenance_count,
            'messages': messages_list,
            'maintenance_requests_count': maintenance_requests_count,
            'rent_amount': rent_amount,
            'total_paid': total_paid,
            'total_pending': total_pending,
            'total_late': total_late,
            'total_all': total_all,
            'balance': balance,
            'balance_abs': abs(balance),
            'payments': payments[:5],  # Show only the 5 most recent payments
        }
        
        return render(request, 'tenancy/tenant_dashboard.html', context)
    
    except Exception as e:
        messages.error(request, f'Error loading dashboard: {str(e)}')
        context = {
            'page_title': 'Tenant Dashboard',
            'error': str(e)
        }
        return render(request, 'tenancy/tenant_dashboard.html', context)


# View Payment History
@login_required(login_url='home:index')
def payment_history(request):
    """Display tenant's payment history"""
    # Redirect non-tenant users to their appropriate dashboard
    if not hasattr(request.user, 'user_type') or request.user.user_type != 'tenant':
        if hasattr(request.user, 'user_type') and request.user.user_type == 'landlord':
            return redirect('landlord:dashboard')
        return redirect('home:index')
        
    try:
        tenancy = Tenancy.objects.filter(tenant=request.user, is_active=True).first()
        
        if not tenancy:
            messages.error(request, 'No active tenancy found')
            return redirect('tenancy:tenant_dashboard')

        # Get all payments for this tenancy
        payments = Payment.objects.filter(tenancy=tenancy).order_by('-date', '-created_at')
        
        # Calculate payment statistics
        total_paid = payments.filter(status='Paid').aggregate(total=Sum('amount'))['total'] or 0
        total_pending = payments.filter(status='Pending').aggregate(total=Sum('amount'))['total'] or 0
        total_late = payments.filter(status='Late').aggregate(total=Sum('amount'))['total'] or 0
        overall_total = total_paid + total_pending + total_late
        
        # Apply filters from request
        status_filter = request.GET.get('status')
        start_date = request.GET.get('start_date')
        
        if status_filter:
            payments = payments.filter(status=status_filter)
        if start_date:
            payments = payments.filter(date__gte=start_date)
        
        # Get property and unit info
        property_obj = tenancy.unit.property
        unit = tenancy.unit
        
        context = {
            'page_title': 'Payment History',
            'tenancy': tenancy,
            'property': property_obj,
            'unit': unit,
            'payments': payments,
            'total_paid': total_paid,
            'total_pending': total_pending,
            'total_late': total_late,
            'overall_total': overall_total,
            'total_payments': payments.count(),
            'status_filter': status_filter,
            'start_date': start_date,
            'status_choices': Payment.STATUS_CHOICES,
        }
        
        return render(request, 'tenancy/payment_history.html', context)
    
    except Exception as e:
        messages.error(request, f'Error loading payment history: {str(e)}')
        return redirect('tenancy:tenant_dashboard')

# View Property Details
@login_required(login_url='home:index')
def property_details(request, property_id=None):
    """Display detailed information about the rented property"""
    try:
        # If property_id is not provided, try to get it from the user's active tenancy
        if property_id is None:
            tenancy = Tenancy.objects.filter(tenant=request.user, is_active=True).first()
            if tenancy:
                return redirect('tenancy:property_details', property_id=tenancy.unit.property.id)
            messages.error(request, 'No active tenancy found')
            return redirect('tenancy:tenant_dashboard')
        
        # Get the property and verify the user has access to it
        property_obj = get_object_or_404(Property, id=property_id)
        tenancy = Tenancy.objects.filter(
            tenant=request.user, 
            unit__property=property_obj,
            is_active=True
        ).first()
        
        if not tenancy and not request.user.is_staff:
            messages.error(request, 'You do not have permission to view this property')
            return redirect('tenancy:tenant_dashboard')
        
        context = {
            'page_title': 'Property Details',
            'tenancy': tenancy,
            'property': property_obj,
            'unit': tenancy.unit,
        }
        
        return render(request, 'tenancy/property_details.html', context)
    
    except Exception as e:
        messages.error(request, f'Error loading property details: {str(e)}')
        return redirect('tenancy:tenant_dashboard')

# View Messages
@login_required(login_url='home:index')
def messages_list(request):
    """Display all messages for the tenant"""
    try:
        messages_list = Message.objects.filter(recipient=request.user).order_by('-sent_at')
        
        context = {
            'page_title': 'Messages',
            'messages': messages_list,
        }
        
        return render(request, 'tenancy/messages_list.html', context)
    
    except Exception as e:
        messages.error(request, f'Error loading messages: {str(e)}')
        return redirect('tenancy:tenant_dashboard')

# View Single Message
@login_required(login_url='home:index')
def message_detail(request, pk):
    """Display a single message"""
    try:
        message = get_object_or_404(Message, pk=pk, recipient=request.user)
        
        # Mark as read
        if not message.read_at:
            message.read_at = timezone.now()
            message.save()
        
        context = {
            'page_title': f'Message: {message.subject}',
            'message': message,
        }
        
        return render(request, 'tenancy/message_detail.html', context)
    
    except Exception as e:
        messages.error(request, f'Error loading message: {str(e)}')
        return redirect('tenancy:messages_list')

# Send Message to Landlord
@login_required(login_url='home:index')
def send_message(request):
    """Allow tenant to send message to landlord"""
    try:
        tenancy = Tenancy.objects.filter(tenant=request.user, is_active=True).first()
        
        if not tenancy:
            messages.error(request, 'No active tenancy found')
            return redirect('tenant_dashboard')
        
        if request.method == 'POST':
            subject = request.POST.get('subject')
            body = request.POST.get('body')
            
            if not all([subject, body]):
                messages.error(request, 'Please fill in all fields')
                return redirect('tenancy:send_message')
            
            # Send message to landlord
            landlord = tenancy.unit.property.landlord
            
            message = Message.objects.create(
                sender=request.user,
                recipient=landlord,
                subject=subject,
                body=body
            )
            
            messages.success(request, 'Message sent successfully!')
            return redirect('tenancy:messages_list')

        context = {
            'page_title': 'Send Message',
            'tenancy': tenancy,
        }
        
        return render(request, 'tenancy/send_message.html', context)
    
    except Exception as e:
        messages.error(request, f'Error sending message: {str(e)}')
        return redirect('tenancy:tenant_dashboard')

# Maintenance Requests List
@login_required(login_url='home:index')
def maintenance_requests(request):
    """
    Show all maintenance requests for the logged-in tenant.
    """
    requests = MaintenanceRequest.objects.filter(tenant=request.user)
    total_requests = requests.count()
    pending_count = requests.filter(status='Pending').count()
    inprogress_count = requests.filter(status='In Progress').count()
    completed_count = requests.filter(status='Completed').count()
    context = {
        'maintenance_requests': requests,
        'total_requests': total_requests,
        'pending_count': pending_count,
        'inprogress_count': inprogress_count,
        'completed_count': completed_count,
    }
    return render(request, 'tenancy/maintenance.html', context)

# Add Maintenance Request
@login_required(login_url='home:index')
def add_maintenance_request(request):
    """
    Form to add a new maintenance request (with notes and photo).
    """
    if request.method == 'POST':
        title = request.POST.get('title')
        notes = request.POST.get('notes')
        photo = request.FILES.get('photo')
        if not title:
            messages.error(request, 'Title is required.')
            return render(request, 'tenancy/add_maintenance_request.html')
        MaintenanceRequest.objects.create(
            tenant=request.user,
            title=title,
            notes=notes,
            photo=photo
        )
        messages.success(request, 'Maintenance request submitted!')
        return redirect('tenancy:maintenance_requests')
    return render(request, 'tenancy/add_maintenance_request.html')

# Maintenance Request Detail
@login_required(login_url='home:index')
def maintenance_detail(request, pk):
    """
    Show details for a single maintenance request.
    """
    request_obj = get_object_or_404(MaintenanceRequest, pk=pk, tenant=request.user)
    return render(request, 'tenancy/maintenance_detail.html', {'request': request_obj})

@login_required
def chatbot_api(request):
    """Intent-based chatbot for tenants (POST JSON {"message": "..."}).

    Intents supported: Greeting, Help, Ask Price, Ask Time, Goodbye, Balance/Payments, Landlord, Tenancy, Maintenance, Fallback
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    message = data.get('message', '').strip().lower()
    if not message:
        return JsonResponse({'reply': 'Tafadhali andika swali kwanza.'})

    # Ensure tenant has an active tenancy
    tenancy = Tenancy.objects.filter(tenant=request.user, is_active=True).first()
    if not tenancy:
        return JsonResponse({'reply': 'Huna tenancy hai. Tafadhali wasiliana na mwenye nyumba au admin.'})

    # Define simple phrase lists for intents
    greetings = ['hello', 'hi', 'habari', 'hey', 'salaam', 'salamu', 'morning', 'hi there', 'habari gani']
    helps = ['help', 'assist', 'how to', 'what can i', 'how do i', 'help me', 'nisaidie', 'naweza kufanya nini', 'how can i', 'what can i ask']
    ask_price = ['price', 'how much', 'cost', 'rent amount', 'how much is', 'what is the rent', 'bei', 'rent', 'bei ya']
    ask_time = ['time', 'date', 'when', 'today', 'now', 'current time', 'tarehe', 'saa']
    goodbyes = ['bye', 'goodbye', 'kwaheri', 'see you', 'tutaonana', 'bye bye', 'bai']

    # Normalize message into token-friendly string
    normalized = ' ' + re.sub(r'\W+', ' ', message) + ' '

    def has_phrase(phrase):
        # match whole phrase as words (handles multi-word phrases)
        return (' ' + phrase + ' ') in normalized

    def has_any(phrases):
        return any(has_phrase(p) for p in phrases)

    reply = None

    # Greeting
    if has_any(greetings):
        reply = 'Habari! Ninaweza kukusaidia kuhusu kodi, malipo, matengenezo, au mawasiliano na mwenye nyumba. Uliza swali lolote.'

    # Help
    elif has_any(helps):
        reply = "Ninaweza kukusaidia kuhusu: 'balance' (salio), 'payments' (malipo), 'maintenance' (matengenezo), 'landlord' (mawasiliano). Mfano: 'What is my balance?', 'Show recent payments', 'How do I report a repair?'"

    # Ask Price
    elif has_any(ask_price):
        rent = getattr(tenancy.unit.property, 'rent', None) or getattr(tenancy.unit, 'rent_amount', 0) or 0
        reply = f'Kodi ya mwezi ni TZS {float(rent):.2f}.'

    # Ask Time
    elif has_any(ask_time):
        now = timezone.now()
        reply = f'Sasa ni {now.strftime("%Y-%m-%d %H:%M:%S")}. '

    # Goodbye
    elif has_any(goodbyes):
        reply = 'Kwaheri! Ikiwa unahitaji msaada tena, nijulie.'

    # Balance / next payment
    elif any(k in message for k in ['balance', 'due', 'next payment', 'next rent']):
        paid = Payment.objects.filter(tenancy=tenancy, status='Paid').aggregate(total=Sum('amount'))['total'] or 0
        rent = getattr(tenancy.unit.property, 'rent', 0) or getattr(tenancy.unit, 'rent_amount', 0) or 0
        balance = rent - paid
        reply = f'Kodi: TZS {rent:.2f}. Ulilipa: TZS {paid:.2f}. Salio: TZS {balance:.2f}.'

    # Recent payments
    elif 'payment' in message or 'payments' in message or 'history' in message:
        recent = Payment.objects.filter(tenancy=tenancy).order_by('-date')[:3]
        if not recent:
            reply = 'Hakuna malipo yaliyorekodiwa.'
        else:
            parts = [f'{p.date}: TZS {p.amount:.2f} ({p.status})' for p in recent]
            reply = 'Malipo ya karibuni: ' + '; '.join(parts)

    # Landlord contact
    elif any(k in message for k in ['landlord', 'owner', 'contact']):
        landlord = tenancy.unit.property.landlord
        landlord_name = landlord.get_full_name() or getattr(landlord, 'username', 'N/A')
        landlord_email = getattr(landlord, 'email', 'N/A')
        landlord_phone = getattr(landlord, 'phone', 'N/A')
        reply = f'Mwenye nyumba: {landlord_name}. Barua pepe: {landlord_email}. Simu: {landlord_phone}.'

    # Tenancy / lease details
    elif any(k in message for k in ['lease', 'contract', 'end date', 'tenancy end']):
        end_date = getattr(tenancy, 'end_date', None)
        start_date = getattr(tenancy, 'start_date', None)
        if end_date:
            reply = f'Tenancy yako inaanza {start_date} na inamalizika {end_date}.'
        else:
            reply = 'Hakuna tarehe ya kumaliza iliyowekwa kwa tenancy yako.'

    # Maintenance requests
    elif any(k in message for k in ['maintenance', 'repair', 'issue']):
        m_reqs = MaintenanceRequest.objects.filter(tenant=request.user).order_by('-created_at')[:3]
        if not m_reqs:
            reply = 'Hujawasilisha maombi yoyote ya matengenezo.'
        else:
            parts = [f'{x.title}: {x.status}' for x in m_reqs]
            reply = 'Maombi ya matengenezo: ' + '; '.join(parts)

    else:
        reply = "Samahani sijui. Unaweza kuuliza kuhusu 'rent', 'balance', 'payments', 'landlord', au 'maintenance'."

    return JsonResponse({'reply': reply})

@login_required
def add_tenant_for_landlord(request):
    """
    Handles the creation of a new tenant and their tenancy by a landlord.

    On POST, it validates the tenant's personal details and tenancy information.
    If valid, it creates a new User with a default password and a new Tenancy,
    then marks the selected unit as occupied.
    """
    if request.method == 'POST':
        user_form = TenantUserForm(request.POST, request.FILES)
        tenancy_form = AddTenancyForm(request.POST, landlord=request.user)

        if user_form.is_valid() and tenancy_form.is_valid():
            try:
                with transaction.atomic():
                    # Create a new user for the tenant
                    new_tenant = User.objects.create_user(
                        username=user_form.cleaned_data['email'],
                        email=user_form.cleaned_data['email'],
                        first_name=user_form.cleaned_data['first_name'],
                        last_name=user_form.cleaned_data['last_name'],
                        phone=user_form.cleaned_data['phone'],
                        emergency_contact_name=user_form.cleaned_data['emergency_contact_name'],
                        emergency_contact_phone=user_form.cleaned_data['emergency_contact_phone'],
                        emergency_contact_relationship=user_form.cleaned_data['emergency_contact_relationship'],
                        password='password@123',  # Set a default password
                        user_type='tenant'  # Set the user type to 'tenant'
                    )

                    # Create a new tenancy
                    tenancy = tenancy_form.save(commit=False)
                    tenancy.tenant = new_tenant
                    
                    # Get the selected unit from the form
                    unit = tenancy_form.cleaned_data['unit']
                    tenancy.unit = unit
                    tenancy.save()

                    # Update the unit to mark it as occupied
                    unit.is_occupied = True
                    unit.save()

                    messages.success(
                        request, 
                        f'Tenant {new_tenant.get_full_name()} added successfully! ' \
                        f'Their temporary password is: password@123'
                    )
                    return redirect('landlord:dashboard')
                    
            except Exception as e:
                messages.error(
                    request, 
                    f'Failed to add tenant. Error: {str(e)}. Please try again.'
                )
                logger.error(f"Error adding tenant: {str(e)}", exc_info=True)
        else:
            # If there are form errors, collect them to display to the user
            for field, errors in user_form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            for field, errors in tenancy_form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        user_form = TenantUserForm()
        tenancy_form = AddTenancyForm(landlord=request.user)

    return render(request, 'tenancy/add_tenant.html', {
        'user_form': user_form,
        'tenancy_form': tenancy_form,
        'page_title': 'Add New Tenant'
    })


@login_required
def load_units(request):
    """
    AJAX view to load units for a selected property.
    Returns HTML option elements with available units.
    """
    property_id = request.GET.get('property', '').strip()
    
    logger.info(f"load_units called - User: {request.user.id}, Property param: '{property_id}'")
    
    if not property_id:
        logger.warning(f"load_units: No property_id provided")
        return HttpResponse('<option value="">Select a property first</option>')
    
    try:
        # Verify the property belongs to the logged-in user
        property_obj = Property.objects.get(id=property_id, landlord=request.user)
        logger.info(f"load_units: Found property {property_id} for user {request.user.id}")
        
        # Get unoccupied units for this property
        units = Unit.objects.filter(
            property=property_obj, 
            is_occupied=False
        ).order_by('unit_number')
        
        logger.info(f"load_units: Found {units.count()} unoccupied units for property {property_id}")
        
        # Build HTML response
        options = '<option value="">Select a unit</option>'
        for unit in units:
            options += f'<option value="{unit.id}">Unit {unit.unit_number}</option>'
        
        if units.count() == 0:
            options = '<option value="">No available units for this property</option>'
        
        logger.info(f"load_units: Returning {units.count()} units")
        return HttpResponse(options, content_type='text/html')
        
    except Property.DoesNotExist:
        logger.error(f"load_units: Property {property_id} not found or not owned by user {request.user.id}")
        return HttpResponse('<option value="">Property not found</option>', content_type='text/html')
    except Exception as e:
        logger.error(f"load_units error: {str(e)}", exc_info=True)
        return HttpResponse(f'<option value="">Error: {str(e)}</option>', content_type='text/html')

@login_required
def edit_tenant_for_landlord(request, pk):
    """
    Edit details for a single tenant.
    Handles both displaying the form (GET) and processing the submitted data (POST).
    """
    tenancy = get_object_or_404(Tenancy, pk=pk, unit__property__landlord=request.user)
    tenant_user = tenancy.tenant

    if request.method == 'POST':
        user_form = TenantUserForm(request.POST, instance=tenant_user)
        tenancy_form = TenancyForm(request.POST, instance=tenancy)
        if user_form.is_valid() and tenancy_form.is_valid():
            user_form.save()
            tenancy_form.save()
            messages.success(request, 'Tenant details updated successfully.')
            return redirect('landlord:dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        user_form = TenantUserForm(instance=tenant_user)
        tenancy_form = TenancyForm(instance=tenancy)

    return render(request, 'tenancy/edit_tenant.html', {
        'user_form': user_form,
        'tenancy_form': tenancy_form,
        'tenancy': tenancy
    })

@login_required
def delete_tenant_for_landlord(request, pk):
    """
    Handles the deletion of a tenancy. When a tenancy is deleted, the corresponding
    unit is marked as unoccupied.
    """
    tenancy = get_object_or_404(Tenancy, id=pk, unit__property__landlord=request.user)
    
    if request.method == 'POST':
        unit = tenancy.unit
        tenancy.delete()
        
        # Mark the unit as unoccupied
        unit.is_occupied = False
        unit.save()
        
        messages.success(request, 'Tenancy deleted successfully.')
        return redirect('landlord:dashboard')

    return render(request, 'tenancy/delete_tenant.html', {'tenancy': tenancy})

@login_required
def tenant_detail_for_landlord(request, pk):
    """
    Displays a detailed view of a specific tenancy for the landlord.
    Shows payment information including total paid, pending, and balance.
    """
    tenancy = get_object_or_404(Tenancy, pk=pk, unit__property__landlord=request.user)
    
    # Get payment history for this tenancy
    payments = Payment.objects.filter(tenancy_id=tenancy.id).order_by('-date', '-created_at')
    
    # Calculate payment statistics
    payment_stats = payments.aggregate(
        total_paid=Sum('amount', filter=Q(status='Paid')),
        total_pending=Sum('amount', filter=Q(status='Pending')),
        total_late=Sum('amount', filter=Q(status__in=['Late', 'Overdue'])),
        total_all=Sum('amount')
    )
    
    total_paid = payment_stats['total_paid'] or 0
    total_pending = payment_stats['total_pending'] or 0
    total_late = payment_stats['total_late'] or 0
    total_all = payment_stats['total_all'] or 0
    
    # Get the monthly rent amount
    rent_amount = tenancy.unit.rent_amount or 0
    
    # Calculate the balance (rent due - total paid)
    balance = rent_amount - total_paid
    
    # Calculate payment status
    payment_status = 'Paid'
    if total_paid <= 0:
        payment_status = 'Unpaid'
    elif balance > 0:
        payment_status = 'Partial'
    
    context = {
        'page_title': f'Tenant: {tenancy.tenant.get_full_name() or tenancy.tenant.username}',
        'tenancy': tenancy,
        'balance': balance,
        'absolute_balance': abs(balance),
        'property': tenancy.unit.property,
        'unit': tenancy.unit,
        'tenant': tenancy.tenant,
        'payments': payments[:5],  # Show only the 5 most recent payments
        'total_paid': total_paid,
        'total_pending': total_pending,
        'total_late': total_late,
        'total_all': total_all,
        'rent_amount': rent_amount,
        'payment_status': payment_status,
        'is_paid': payment_status == 'Paid',
        'is_overdue': balance < 0,
    }
    
    return render(request, 'landlord/tenant_detail.html', context)


@login_required(login_url='home:index')
def add_payment(request, tenancy_id):
    """
    Handle adding a new payment for a specific tenancy.
    """
    # Check if user is tenant or landlord
    if request.user.user_type == 'tenant':
        # Tenants can only see their own tenancy
        tenancy = get_object_or_404(Tenancy, id=tenancy_id, tenant=request.user, is_active=True)
    else:
        # Landlords can see any tenancy in their properties
        tenancy = get_object_or_404(Tenancy, id=tenancy_id, unit__property__landlord=request.user)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST, request.FILES, tenancy=tenancy, request=request)
        if form.is_valid():
            try:
                payment = form.save(commit=False)
                payment.tenancy = tenancy
                
                # Set created_by to the current user if not already set
                if not payment.created_by_id and request.user.is_authenticated:
                    payment.created_by = request.user
                
                # Save the payment
                payment.save()
                form.save_m2m()  # In case there are any many-to-many fields
                
                # Update tenancy status if needed
                if payment.status == 'Paid' and not tenancy.is_active:
                    tenancy.is_active = True
                    tenancy.save()
                
                messages.success(request, 'Payment recorded successfully!')
                # Redirect back to the tenant detail page
                return redirect('tenancy:tenant_detail_for_landlord', pk=tenancy.id)
                
            except Exception as e:
                # Log the error for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error saving payment: {str(e)}")
                
                # Add a user-friendly error message
                messages.error(request, f'Error saving payment: {str(e)}. Please try again.')
                
                # Add form errors to messages
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
                
                # Return to the form with the data still filled in
                return render(request, 'tenancy/add_payment.html', {
                    'page_title': 'Record New Payment',
                    'form': form,
                    'tenancy': tenancy,
                    'tenant': tenancy.tenant,
                    'property': tenancy.unit.property,
                })
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PaymentForm(tenancy=tenancy, request=request)
    
    context = {
        'page_title': 'Record New Payment',
        'form': form,
        'tenancy': tenancy,
        'tenant': tenancy.tenant,
        'property': tenancy.unit.property,
    }
    return render(request, 'tenancy/add_payment.html', context)

@login_required(login_url='home:index')
def payment_details(request, payment_id):
    """
    View details of a specific payment.
    """
    payment = get_object_or_404(Payment, id=payment_id)
    tenant = payment.tenancy.tenant
    property_obj = payment.tenancy.unit.property
    tenancy = payment.tenancy
    
    context = {
        'page_title': 'Payment Details',
        'payment': payment,
        'tenant': tenant,
        'property': property_obj,
        'tenancy': tenancy,
    }
    
    return render(request, 'tenancy/payment_detail.html', context)


@login_required(login_url='home:index')
def edit_payment(request, payment_id):
    """
    Edit an existing payment.
    """
    payment = get_object_or_404(Payment, id=payment_id)
    
    # Check if the user is authorized to edit this payment
    if not request.user.is_staff and payment.tenancy.tenant != request.user:
        messages.error(request, 'You do not have permission to edit this payment.')
        return redirect('tenancy:payment_history')
    
    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Payment updated successfully.')
            return redirect('tenancy:payment_details', payment_id=payment.id)
    else:
        form = PaymentForm(instance=payment)
    
    return render(request, 'tenancy/edit_payment.html', {
        'form': form,
        'payment': payment,
        'page_title': 'Edit Payment'
    })


@login_required(login_url='home:index')
def delete_payment(request, payment_id):
    """
    Delete a payment record.
    """
    payment = get_object_or_404(Payment, id=payment_id)
    tenancy_id = payment.tenancy.id
    
    # Check if the user is authorized to delete this payment
    if not request.user.is_staff and payment.tenancy.tenant != request.user:
        messages.error(request, 'You do not have permission to delete this payment.')
        return redirect('tenancy:payment_history')
    
    if request.method == 'POST':
        # Delete the payment
        payment.delete()
        messages.success(request, 'Payment deleted successfully.')
        return redirect('tenancy:tenant_detail_for_landlord', pk=tenancy_id)
    
    # If not a POST request, redirect to payment details
    return redirect('tenancy:payment_details', payment_id=payment_id)


@login_required(login_url='home:index')
def payment_receipts(request):
    """
    Display payment receipts for the current tenant.
    Shows all paid/confirmed payments with download and print options.
    """
    try:
        # Get tenant's current active tenancy
        tenancy = Tenancy.objects.filter(tenant=request.user, is_active=True).first()
        
        if not tenancy:
            context = {
                'page_title': 'Payment Receipts',
                'payments': [],
                'property': None,
                'unit': None,
            }
            return render(request, 'tenancy/payment_receipts.html', context)
        
        # Get all paid payments for this tenancy
        payments = Payment.objects.filter(
            tenancy=tenancy,
            status__in=['Paid', 'confirmed']
        ).order_by('-date')
        
        # Calculate total paid amount
        total_paid = sum(payment.amount for payment in payments if payment.amount)
        
        # Get property and unit information
        property_obj = tenancy.unit.property
        unit = tenancy.unit
        
        context = {
            'page_title': 'Payment Receipts',
            'payments': payments,
            'total_paid': total_paid,
            'tenancy': tenancy,
            'property': property_obj,
            'unit': unit,
            'user': request.user,
        }
        
        return render(request, 'tenancy/payment_receipts.html', context)
        
    except Exception as e:
        logger.error(f"Error loading payment receipts for user {request.user.id}: {str(e)}")
        messages.error(request, 'Error loading payment receipts. Please try again.')
        return render(request, 'tenancy/payment_receipts.html', {
            'page_title': 'Payment Receipts',
            'payments': [],
            'property': None,
            'unit': None,
        })


@login_required(login_url='home:index')
def view_documents(request):
    """
    Display documents uploaded by landlord for tenant's rental property.
    """
    try:
        # Get tenant's current active tenancy
        tenancy = Tenancy.objects.filter(tenant=request.user, is_active=True).first()
        
        if not tenancy:
            context = {
                'page_title': 'Property Documents',
                'documents': [],
                'lease_count': 0,
                'rules_count': 0,
            }
            return render(request, 'tenancy/documents.html', context)
        
        # Get all documents for tenant's property
        property_obj = tenancy.unit.property
        documents = Document.objects.filter(
            property=property_obj,
            is_active=True
        ).order_by('-uploaded_at')
        
        # Count document types
        lease_count = documents.filter(document_type='Lease Agreement').count()
        rules_count = documents.filter(document_type='House Rules').count()
        
        context = {
            'page_title': 'Property Documents',
            'documents': documents,
            'property': property_obj,
            'tenancy': tenancy,
            'lease_count': lease_count,
            'rules_count': rules_count,
        }
        
        return render(request, 'tenancy/documents.html', context)
        
    except Exception as e:
        logger.error(f"Error loading documents for user {request.user.id}: {str(e)}")
        messages.error(request, 'Error loading documents. Please try again.')
        return render(request, 'tenancy/documents.html', {
            'page_title': 'Property Documents',
            'documents': [],
            'lease_count': 0,
            'rules_count': 0,
        })


@login_required(login_url='home:index')
def download_document(request, document_id):
    """
    Download a document file.
    """
    try:
        document = get_object_or_404(Document, id=document_id)
        
        # Verify tenant has access to this document
        tenancy = Tenancy.objects.filter(
            tenant=request.user,
            unit__property=document.property,
            is_active=True
        ).first()
        
        if not tenancy:
            messages.error(request, 'You do not have permission to access this document.')
            return redirect('tenancy:view_documents')
        
        # Return the file
        response = FileResponse(document.file.open('rb'), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{document.title}.pdf"'
        return response
        
    except Exception as e:
        logger.error(f"Error downloading document {document_id}: {str(e)}")
        messages.error(request, 'Error downloading document. Please try again.')
        return redirect('tenancy:view_documents')