from djan.contrib import admin

# Register your models here.
from .models import Employee,Country,Department,State,City,OnSiteEmployees

admin.site.register(Employee)
admin.site.register(Country)
admin.site.register(Department)
admin.site.register(State)
admin.site.register(City)
admin.site.register(OnSiteEmployees)