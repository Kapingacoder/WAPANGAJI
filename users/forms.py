from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

User = get_user_model()

class UserProfileForm(UserChangeForm):
    """Form for updating user profile information"""
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone', 'profile_picture')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the password field that comes with UserChangeForm
        if 'password' in self.fields:
            del self.fields['password']
        
        # Add Bootstrap classes to form fields
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

class UserRegistrationForm(UserCreationForm):
    """Form for user registration with additional fields"""
    email = forms.EmailField(
        max_length=254,
        help_text='Required. Enter a valid email address.',
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    phone = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_email(self):
        """Ensure email is unique"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('This email is already in use.')
        return email
