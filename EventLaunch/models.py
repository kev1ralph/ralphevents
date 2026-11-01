from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse

# ==========================================
# CORE EVENT MODELS
# ==========================================

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Event(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='events')
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_events')
    venue = models.CharField(max_length=200)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    capacity = models.PositiveIntegerField(default=100)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    image = models.ImageField(upload_to='events/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']

    def save(self, *args, **kwargs):
        # Force slug generation if it's missing
        if not self.slug:
            self.slug = slugify(self.title)
            
        # Safety loop to prevent UNIQUE constraint crashes
        original_slug = self.slug
        counter = 1
        while Event.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            self.slug = f"{original_slug}-{counter}"
            counter += 1
            
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('event_detail', kwargs={'slug': self.slug})

    @property
    def seats_left(self):
        return self.capacity - self.registrations.count()

    def is_past(self):
        from django.utils import timezone
        return self.end_date < timezone.now()

    def __str__(self):
        return self.title


class Registration(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    attendee_name = models.CharField(max_length=100)
    attendee_email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'attendee_email')
        ordering = ['-registered_at']

    def __str__(self):
        return f"{self.attendee_name} → {self.event.title}"


class Profile(models.Model):
    ROLE_CHOICES = [
        ('organizer', 'Organizer'),
        ('attendee', 'Attendee'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='attendee')
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"


# ==========================================
# INVENTORY & SALES MODELS
# ==========================================

class InventoryItem(models.Model):
    CATEGORY_CHOICES = [
        ('furniture', 'Furniture (Tables/Chairs)'),
        ('tents', 'Tents & Canopies'),
        ('decor', 'Decor & Balloons'),
        ('audio', 'Audio & Lighting'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='furniture')
    quantity = models.PositiveIntegerField(default=0, help_text="Number of items in stock")
    price_per_day = models.DecimalField(max_digits=8, decimal_places=2, help_text="Rental price per day")
    description = models.TextField(blank=True, null=True)
    added_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_sales(self):
        sales = self.sales.all()
        total = sum(sale.quantity_sold * sale.price_at_sale for sale in sales)
        return total

    def __str__(self):
        return f"{self.name} ({self.quantity} in stock)"


class Sale(models.Model):
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='sales')
    quantity_sold = models.PositiveIntegerField(default=1)
    price_at_sale = models.DecimalField(max_digits=8, decimal_places=2, help_text="Price per unit at the time of sale")
    date_sold = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity_sold}x {self.item.name} sold on {self.date_sold.strftime('%Y-%m-%d')}"


# ==========================================
# STAFF PAYMENT & LAUNDRY MODELS
# ==========================================

class LaundryService(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount paid to staff per item")

    def __str__(self):
        return f"{self.name} (UGX {self.price})"


class CleaningJob(models.Model):
    staff_name = models.CharField(max_length=100)
    service = models.ForeignKey(LaundryService, on_delete=models.CASCADE, null=True, blank=True)
    custom_description = models.CharField(max_length=200, blank=True, null=True, help_text="Use this if the item is not in the list")
    custom_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Price for custom item")
    
    quantity = models.PositiveIntegerField(default=1)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    date_cleaned = models.DateTimeField(auto_now_add=True)

    def total_earned(self):
        if self.service:
            return self.service.price * self.quantity
        return self.custom_price * self.quantity

    def balance_remaining(self):
        return self.total_earned() - self.amount_paid

    def __str__(self):
        item = self.service.name if self.service else self.custom_description
        return f"{self.staff_name} - {item}"