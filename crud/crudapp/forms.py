from django import forms
from django.forms import Select, TextInput
from .models import Employee,OnSiteEmployees

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = '__all__'
        widgets = {
            'DateOfBirth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'HireDate': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

class OnSiteEmloyeesForm(forms.ModelForm):
    class Meta:
        model = OnSiteEmployees
        fields = ['first_name','last_name','country','state','city']

        widgets ={
            'first_name':TextInput(attrs={
                'class':'form-control',
                'style':'max-width:300px;',
                'placeholder':'First Name'
            }),
            'last_name':TextInput(attrs={
                'placeholder':'Last Name',
                'class':'form-control',
                'style':'max-width:300px;'
            }),
            'country':Select(attrs={
                'placeholder':'Country',
                'class':'form-control',
                'style':'max-width:300px;'
            }),
            'city':Select(attrs={
                'class':'form-control',
                'style':'max-width:300px;',
                'placeholder':'City'
            }),
            'state':Select(attrs={
                'class':'form-control',
                'style':'max-width:300px;',
                'placeholder':'State'
            })

        }

