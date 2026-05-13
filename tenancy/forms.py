from django import forms
from django.utils import timezone
from users.models import User
from .models import Tenancy, Payment
from properties.models import Unit, Property

class TenantUserForm(forms.ModelForm):
    """
    A form for creating and updating tenant user details.
    """
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'phone',
            'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., +255 712 345 678'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., +255 712 345 678'}),
            'emergency_contact_relationship': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Spouse, Parent, Sibling'}),
        }

class TenancyForm(forms.ModelForm):
    """
    A form for updating an existing tenancy's details.
    """
    class Meta:
        model = Tenancy
        fields = ['start_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

class AddTenancyForm(forms.ModelForm):
    """
    A form for adding a new tenancy, allowing the landlord to select a property,
    then a unit within that property, and set the tenancy dates.
    """
    property = forms.ModelChoiceField(
        queryset=Property.objects.none(),
        empty_label="Select a property",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_property'
        })
    )
    
    unit = forms.ModelChoiceField(
        queryset=Unit.objects.none(),
        empty_label="Select a property first",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_unit'
        })
    )
    
    start_date = forms.DateField(
        label='Lease Start Date',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'min': timezone.now().date().isoformat()
        })
    )

    class Meta:
        model = Tenancy
        fields = ['property', 'unit', 'start_date']

    def __init__(self, *args, **kwargs):
        """
        Initializes the form with properties and units filtered by the current landlord.
        """
        self.landlord = kwargs.pop('landlord', None)
        super().__init__(*args, **kwargs)
        
        if self.landlord:
            # Only show properties belonging to this landlord
            self.fields['property'].queryset = Property.objects.filter(landlord=self.landlord)
            
            # If we're editing an existing tenancy with a unit
            if self.instance and hasattr(self.instance, 'unit') and self.instance.unit:
                # Show all units for the property of the current tenancy
                self.fields['unit'].queryset = Unit.objects.filter(
                    property=self.instance.unit.property
                )
                self.fields['unit'].initial = self.instance.unit
                self.fields['property'].initial = self.instance.unit.property
                self.fields['unit'].widget.attrs['disabled'] = False
            else:
                # For new tenancy or tenancy without unit
                self.fields['unit'].queryset = Unit.objects.none()
                
                # If a property is submitted in the form, update the units
                if 'property' in self.data:
                    try:
                        property_id = int(self.data.get('property'))
                        self.fields['unit'].queryset = Unit.objects.filter(
                            property_id=property_id, 
                            is_occupied=False  # Only show unoccupied units
                        )
                        # Enable the unit select after property is selected
                        self.fields['unit'].widget.attrs['disabled'] = False
                    except (ValueError, TypeError):
                        pass
    
    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


class PaymentForm(forms.ModelForm):
    """
    A form for recording payments for a tenancy with enhanced fields.
    """
    payment_proof = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*,.pdf',
        }),
        help_text='Upload payment receipt or proof (image or PDF)'
    )
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        tenancy = kwargs.pop('tenancy', None)
        super().__init__(*args, **kwargs)
        
        if tenancy:
            # Ensure amount is not pre-filled and is required
            self.fields['amount'].initial = ''
            self.fields['amount'].required = True
            self.fields['amount'].widget.attrs.update({
                'placeholder': 'Enter amount',
                'autocomplete': 'off',
                'value': ''
            })
            self.instance.tenancy = tenancy
            
            # Set the payment method choices from the model
            self.fields['method'] = forms.ChoiceField(
                choices=Payment.PAYMENT_METHODS,
                widget=forms.Select(attrs={'class': 'form-select'}),
                initial='M-Pesa',
                required=True
            )
            
            # Set the status choices from the model
            self.fields['status'] = forms.ChoiceField(
                choices=Payment.STATUS_CHOICES,
                widget=forms.Select(attrs={'class': 'form-select'}),
                initial='Paid',
                required=True
            )
            
            # Make date field required and set default to today
            self.fields['date'].required = True
            self.fields['date'].initial = timezone.now().date()
    
    class Meta:
        model = Payment
        fields = [
            'amount', 'date', 'status', 'method', 
            'reference_number', 'transaction_id', 'description', 'payment_proof'
        ]
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'required': 'required'
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'value': timezone.now().strftime('%Y-%m-%d'),
                'required': 'required'
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Auto-generated if left blank'
            }),
            'transaction_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., M-Pesa transaction ID'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter payment details or notes...'
            }),
        }
        help_texts = {
            'reference_number': 'Leave blank to auto-generate a reference number',
            'transaction_id': 'Optional - for reference purposes only',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        method = cleaned_data.get('method')
        transaction_id = cleaned_data.get('transaction_id')
        status = cleaned_data.get('status')
        
        # No electronic payment methods require transaction ID anymore
        # All remaining methods (Cash, Cheque, Other) are manual
        
        return cleaned_data
    
    def save(self, commit=True):
        payment = super().save(commit=False)
        
        # Set created_by and updated_by if request is available
        if self.request and hasattr(self.request, 'user') and self.request.user.is_authenticated:
            if not payment.pk:  # Only set created_by on creation
                payment.created_by = self.request.user
            payment.updated_by = self.request.user
        
        if commit:
            payment.save()
            
            # Handle file upload if present
            if 'payment_proof' in self.files:
                payment.payment_proof = self.files['payment_proof']
                payment.save()
        
        return payment