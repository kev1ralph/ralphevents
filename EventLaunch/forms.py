from django import forms
from .models import Event, Registration, Profile, Category

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'category', 'venue',
                  'start_date', 'end_date', 'capacity', 'price',
                  'image', 'status']
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_date':   forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_date')
        end   = cleaned.get('end_date')
        if start and end and end <= start:
            raise forms.ValidationError("End date must be after the start date.")
        return cleaned

    def clean_capacity(self):
        cap = self.cleaned_data['capacity']
        if cap < 1:
            raise forms.ValidationError("Capacity must be at least 1.")
        return cap

class RegistrationForm(forms.ModelForm):
    class Meta:
        model = Registration
        fields = ['attendee_name', 'attendee_email', 'phone']

    def __init__(self, *args, **kwargs):
        # Pass the event in so we can prevent duplicates
        self.event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)

    def clean_attendee_email(self):
        email = self.cleaned_data['attendee_email']
        if self.event and Registration.objects.filter(
                event=self.event, attendee_email=email).exists():
            raise forms.ValidationError(
                "This email is already registered for this event.")
        return email

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class SignupForm(UserCreationForm):
    ROLE_CHOICES = [
        ('organizer', 'Organizer'),
        ('attendee',  'Attendee'),
    ]
    full_name = forms.CharField(max_length=100, required=True)
    email     = forms.EmailField(required=True)
    role      = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.RadioSelect)

    class Meta:
        model  = User
        fields = ['username', 'full_name', 'email', 'password1', 'password2', 'role']

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already registered.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        # Store role in Profile later; for now use is_staff for organizer
        if commit:
            user.save()
        return user




        
class ProfileForm(forms.ModelForm):
    class Meta:
        model  = Profile
        fields = ['role', 'phone']


from .models import InventoryItem, Sale


class InventoryForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ['name', 'category', 'quantity', 'price_per_day', 'description'] 
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class RecordSaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['quantity_sold']
        widgets = {
            'quantity_sold': forms.NumberInput(attrs={'min': 1}),
        }