# crudapp/urls.py
from djan.urls import path
from . import views

urlpatterns = [
    path('', views.employee_list, name='employee_list'),
    path('employee/<int:pk>/', views.employee_detail, name='employee_detail'),
    path('employee/new/', views.employee_create, name='employee_create'),
    path('employee/<int:pk>/edit/', views.employee_update, name='employee_update'),
    path('employee/<int:pk>/delete/', views.employee_delete, name='employee_delete'),
    path('cascadingSelect/',views.cascadingSelect,name='cascadingSelect'),
    path('load_states/',views.load_states,name='load_states'),
    path('load_cities/',views.load_cities,name='load_cities'),
    path('TransectionDemo/',views.TransectionDemo,name='TransectionDemo'),


    # Agent URLs
    path('agent/command/', views.agent_command, name='agent_command'),
    # Using a single confirm view with action parameter
    path('agent/confirm/<str:action>/', views.agent_confirm, name='agent_confirm'),
    # Specific confirmation URLs might be slightly clearer if preferred:
    # path('agent/confirm/create/', views.agent_confirm, {'action': 'create'}, name='agent_confirm_create'),
    # path('agent/confirm/update/', views.agent_confirm, {'action': 'update'}, name='agent_confirm_update'),
    # path('agent/confirm/delete/', views.agent_confirm, {'action': 'delete'}, name='agent_confirm_delete'),

    # Simplified confirmation URLs mapping directly to action strings in the view logic
    path('agent/confirm/create/', views.agent_confirm, {'action': 'create'}, name='agent_confirm_create'),
    path('agent/confirm/update/', views.agent_confirm, {'action': 'update'}, name='agent_confirm_update'),
    path('agent/confirm/delete/', views.agent_confirm, {'action': 'delete'}, name='agent_confirm_delete'),


    path('agent/execute/', views.agent_execute, name='agent_execute'), # Single execution endpoint
    path('paginationView',views.PageWiseList,name='paginationView')
]