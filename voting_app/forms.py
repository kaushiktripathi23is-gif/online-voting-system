# voting_app/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import VoterProfile

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

class VoterProfileForm(forms.ModelForm):
    college_id = forms.CharField(max_length=20, required=True, label="College ID Number")
    
    # We ask for the full 12 digits for validation, 
    # but you could change this to "Last 4 Digits" if you prefer.
    aadhaar_number = forms.CharField(max_length=12, required=True, label="Aadhaar Number")
    
    class Meta:
        model = VoterProfile
        fields = ('college_id', 'aadhaar_number')
