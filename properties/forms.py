from django import forms
from .models import Property, Unit
from django.utils import timezone

class PropertyForm(forms.ModelForm):
    """Form for adding/editing property details"""
    class Meta:
        model = Property
        fields = [
            'name', 'address', 'location', 'description',
            'rooms', 'rent', 'status', 'utilities'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Sunset Villas, Downtown Apartments'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Full physical address of the property'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Kileleshwa, Westlands'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Detailed description of the property and its features'
            }),
            'rooms': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'rent': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'utilities': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Water, Electricity, Internet'
            }),
        }
        help_texts = {
            'utilities': 'Separate multiple utilities with commas',
        }

class UnitForm(forms.ModelForm):
    """Form for adding/editing units within a property"""
    class Meta:
        model = Unit
        fields = ['unit_number', 'rent_amount', 'is_occupied']
        widgets = {
            'unit_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., A1, B2, Room 5'
            }),
            'rent_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01'
            }),
            'is_occupied': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch'
            })
        }

UnitFormSet = forms.inlineformset_factory(
    Property,
    Unit,
    form=UnitForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)
