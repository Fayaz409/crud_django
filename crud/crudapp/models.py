from django.db import models

# Create your models here.

class Employee(models.Model):
    Countries =[
        ('India','India'),
        ('USA','USA'),
        ('UK','UK'),
        ('Germany','Germany'),
        ('France','France'),
        ('Italy','Italy'),
        ('Spain','Spain'),
        ('Japan','Japan'),
        ('China','China'),
        ('Russia','Russia')
    ]
    FirstName = models.CharField(max_length=100)
    LastName = models.CharField(max_length=100)
    Title = models.CharField(max_length=50)
    HasPassport = models.BooleanField(default=False)
    Salary = models.IntegerField()
    DateOfBirth = models.DateField()
    HireDate = models.DateField()
    Notes = models.CharField(max_length=200)
    Country= models.CharField(max_length=50,choices=Countries,default=None)

