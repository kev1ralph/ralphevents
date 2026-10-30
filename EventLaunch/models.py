from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse


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
    title       = models.CharField(max_length=200)
    slug        = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField()
    category    = models.ForeignKey(Category, on_delete=models.SET_NULL,
                                    null=True, related_name='events')
    organizer   = models.ForeignKey(User, on_delete=models.CASCADE,
                                    related_name='organized_events')
    venue       = models.CharField(max_length=200)
    start_date  = models.DateTimeField()
    end_date    = models.DateTimeField()
    capacity    = models.PositiveIntegerField(default=100)
    price       = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    image       = models.ImageField(upload_to='events/', blank=True, null=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def is_past(self):
        from django.utils import timezone
        return self.end_date < timezone.now()

    @property
    def seats_left(self):
        return self.capacity - self.registrations.count()

    class Meta:
        ordering = ['-start_date']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        

    def get_absolute_url(self):
        return reverse('event_detail', kwargs={'slug': self.slug})

     
    def __str__(self):
        return self.title


class Registration(models.Model):
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]
    event          = models.ForeignKey(Event, on_delete=models.CASCADE,
                                       related_name='registrations')
    attendee_name  = models.CharField(max_length=100)
    attendee_email = models.EmailField()
    phone          = models.CharField(max_length=20, blank=True)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES,
                                      default='pending')
    registered_at  = models.DateTimeField(auto_now_add=True)
    booking_date = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('event', 'attendee_email')
        ordering = ['-registered_at']

    def __str__(self):
        return f"{self.attendee_name} → {self.event.title}"


from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    ROLE_CHOICES = [
        ('organizer', 'Organizer'),
        ('attendee',  'Attendee'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='attendee')
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)


        from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    ROLE_CHOICES = [
        ('attendee', 'Attendee'),
        ('organizer', 'Organizer'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='attendee')
    bio = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    def __str__(self):
        return f"{self.user.username} - {self.role}"

# Automatically create a Profile when a User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

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
        # This calculates sales dynamically based on the Sale model below
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
     