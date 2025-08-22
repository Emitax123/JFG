from .models import AccountMovement
from django import forms

class ManualAccountEntryForm(forms.ModelForm):
    class Meta:
        model = AccountMovement
        fields = '__all__'
        exclude = ['account', 'user', 'created_at', 'created_by']
        widgets = {
            'movement_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }

   
