from django.contrib import admin
from .models import Category, Event, Registration


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display   = ('title', 'category', 'organizer', 'start_date',
                      'venue', 'status', 'capacity')
    list_filter    = ('status', 'category', 'start_date')
    search_fields  = ('title', 'venue', 'description')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'start_date'
    list_editable  = ('status',)
    raw_id_fields  = ('organizer',)


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display  = ('attendee_name', 'event', 'attendee_email',
                     'status', 'registered_at')
    list_filter   = ('status', 'event')
    search_fields = ('attendee_name', 'attendee_email')


from .models import Profile   # add to existing import

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone')
    list_filter  = ('role',)
    search_fields = ('user__username', 'user__email')

from .models import InventoryItem # Add this to your imports

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'quantity', 'price_per_day')
    list_filter = ('category',)
    search_fields = ('name',)
    


from .models import InventoryItem, Sale # Update your imports

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('item', 'quantity_sold', 'price_at_sale', 'date_sold')
    list_filter = ('date_sold', 'item')
    