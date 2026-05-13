from django.urls import path
from . import views

app_name = 'tenancy'

urlpatterns = [
    # Tenant Dashboard
    path('dashboard/', views.tenant_dashboard, name='tenant_dashboard'),
    
    # Payment History
    path('payments/', views.payment_history, name='payment_history'),
    
    # Payment Receipts
    path('receipts/', views.payment_receipts, name='payment_receipts'),
    
    # Documents
    path('documents/', views.view_documents, name='view_documents'),
    path('documents/<int:document_id>/download/', views.download_document, name='download_document'),
    
    # Property Details
    path('property/<int:property_id>/', views.property_details, name='property_details'),
    
    # Messages
    path('messages/', views.messages_list, name='messages_list'),
    path('messages/<int:pk>/', views.message_detail, name='message_detail'),
    path('messages/send/', views.send_message, name='send_message'),
    
    # Maintenance
    path('maintenance/', views.maintenance_requests, name='maintenance_requests'),
    path('maintenance/add/', views.add_maintenance_request, name='add_maintenance_request'),
    path('maintenance/<int:pk>/', views.maintenance_detail, name='maintenance_detail'),

    # URLs for landlord to manage tenants
    path('tenant/add/', views.add_tenant_for_landlord, name='add_tenant_for_landlord'),
    path('tenant/<int:pk>/', views.tenant_detail_for_landlord, name='tenant_detail_for_landlord'),
    path('tenant/<int:pk>/edit/', views.edit_tenant_for_landlord, name='edit_tenant_for_landlord'),
    path('tenant/<int:pk>/delete/', views.delete_tenant_for_landlord, name='delete_tenant_for_landlord'),
    
    # AJAX endpoints
    path('load_units/', views.load_units, name='load_units'),
    
    # Chatbot API
    path('api/chatbot/', views.chatbot_api, name='chatbot_api'),

    # Payment management
    path('payment/add/<int:tenancy_id>/', views.add_payment, name='add_payment'),
    path('payment/<int:payment_id>/', views.payment_details, name='payment_details'),
    path('payment/<int:payment_id>/edit/', views.edit_payment, name='edit_payment'),
    path('payment/<int:payment_id>/delete/', views.delete_payment, name='delete_payment'),
]