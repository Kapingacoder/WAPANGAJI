from django.urls import path
from . import views

app_name = 'properties'

urlpatterns = [
    # Properties List - View all properties
    path('', views.properties_list, name='properties_list'),
    
    # Property Details - View single property
    path('<int:pk>/', views.property_detail, name='property_detail'),
    
    # Add Property - Create new property
    path('add/', views.add_property, name='add_property'),
    
    # Edit Property - Update property information
    path('<int:pk>/edit/', views.edit_property, name='edit_property'),
    
    # Delete Property - Remove property
    path('<int:pk>/delete/', views.delete_property, name='delete_property'),
    
    # Edit Unit - Update unit information
    path('units/<int:pk>/edit/', views.edit_unit, name='edit_unit'),
    
    # Delete Unit - Remove unit from property
    path('units/<int:pk>/delete/', views.delete_unit, name='delete_unit'),
]
