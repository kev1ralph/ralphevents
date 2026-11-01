from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Auth - Using Django's built-in views
    path('login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('signup/', views.signup_view, name='signup'), # Keep your custom signup
    path('3d-visualization/', views.three_d_view, name='three_d_view'),
    path('api/wendy/', views.wendy_chat, name='wendy_chat'),
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('inventory/add/', views.add_inventory_item, name='add_inventory_item'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('inventory/sale/<int:item_id>/', views.record_sale, name='record_sale'),
    path('inventory/delete/<int:item_id>/', views.delete_inventory_item, name='delete_inventory_item'),
    path('staff/cleaning/', views.cleaning_dashboard, name='cleaning_dashboard'),
    path('staff/cleaning/add/', views.add_cleaning_job, name='add_cleaning_job'),
    path('staff/services/add/', views.add_laundry_service, name='add_laundry_service'),



    # Home & events
    path('', views.home, name='home'),
    path('events/', views.event_list, name='event_list'),
    path('events/create/', views.event_create, name='event_create'),
    path('events/<slug:slug>/', views.event_detail, name='event_detail'),
    path('events/<slug:slug>/edit/', views.event_update, name='event_update'),
    path('events/<slug:slug>/delete/', views.event_delete, name='event_delete'),
    
    # Role-based
    path('my-events/', views.my_events, name='my_events'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('profile/', views.profile_view, name='profile'),
]

