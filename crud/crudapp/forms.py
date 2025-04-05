from django import forms
from .models import Employee

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = '__all__'
        widgets = {
            'DateOfBirth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'HireDate': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
