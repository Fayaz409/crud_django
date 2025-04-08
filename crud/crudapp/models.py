from djan.db import models

# Create your models here.

class Employee(models.Model):
    
    FirstName = models.CharField(max_length=100)
    LastName = models.CharField(max_length=100)
    Title = models.CharField(max_length=50)
    HasPassport = models.BooleanField(default=False)
    Salary = models.IntegerField()
    DateOfBirth = models.DateField()
    HireDate = models.DateField()
    Notes = models.CharField(max_length=200)
    Email = models.EmailField(max_length=100,default=None)
    PhoneNumber = models.CharField(max_length=15,default="")
    EmpCountry= models.ForeignKey('Country',default=None,on_delete=models.CASCADE)
    EmpDept = models.ForeignKey('Department',on_delete=models.CASCADE)


class Department(models.Model):
    departments =[
        ('IT','IT'),
        ('HR','HR'),
        ('Finanace','FINANCE'),
        
    ]
    department = models.CharField(max_length=50,choices=departments)

    def __str__(self):
        return self.department

class Country(models.Model):
    countries =[
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
    name = models.CharField(max_length=50,choices=countries)

    def __str__(self):
        return self.name

class State(models.Model):
    name = models.CharField(max_length=100)
    country = models.ForeignKey('Country',on_delete=models.PROTECT,default = None)

    def __str__(self):
        return self.name
    

class City(models.Model):
    name = models.CharField(max_length=100)
    state = models.ForeignKey('State',on_delete=models.PROTECT,default=None)

    def __str__(self):
        return self.name

class OnSiteEmployees(models.Model):
    first_name= models.CharField(max_length=100,null=True)
    last_name = models.CharField(max_length=100,null=True)
    country = models.ForeignKey('Country',on_delete=models.PROTECT,default=None)
    state = models.ForeignKey('State',on_delete=models.PROTECT,default=None)
    city = models.ForeignKey('City',on_delete=models.PROTECT,default=None)

    def __str__(self):
        return f" Employee Name: {self.first_name} {self.last_name}" 