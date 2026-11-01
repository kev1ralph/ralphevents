from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.utils.text import slugify
from django.db.models import Sum
import json
import random

# Import all your models
from .models import (
    Event, Category, Registration, Profile, 
    InventoryItem, Sale, LaundryService, CleaningJob
)

# Import all your forms
from .forms import (
    EventForm, RegistrationForm, SignupForm, ProfileForm, 
    InventoryForm, RecordSaleForm, CleaningJobForm
)

# ==========================================
# AUTHENTICATION VIEWS
# ==========================================

def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.first_name = form.cleaned_data.get('full_name', user.username)
            user.save()

            # Bulletproof profile creation
            if hasattr(user, 'profile'):
                user.profile.role = form.cleaned_data['role']
                user.profile.save()
            else:
                Profile.objects.create(user=user, role=form.cleaned_data['role'])

            login(request, user)
            messages.success(request, f"Welcome, {user.first_name}!")
            return redirect('home')
    else:
        form = SignupForm()
    return render(request, 'auth/signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "Logged in successfully.")
            return redirect('home')
        else:
            messages.error(request, "Invalid credentials.")
    else:
        form = AuthenticationForm()
    return render(request, 'auth/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user.profile)
    return render(request, 'auth/profile.html', {'form': form, 'profile': request.user.profile})


# ==========================================
# CORE EVENT VIEWS
# ==========================================

def home(request):
    # Only show published events on the homepage
    events = Event.objects.filter(status='published').order_by('-start_date')[:6]
    categories = Category.objects.all()
    
    context = {
        'events': events,
        'categories': categories,
        'total_events': Event.objects.filter(status='published').count(),
    }
    return render(request, 'events/home.html', context)

def event_list(request):
    events = Event.objects.filter(status='published')
    
    # Search & Filter Logic
    query = request.GET.get('q')
    if query:
        events = events.filter(title__icontains=query)
        
    category_id = request.GET.get('category')
    if category_id:
        events = events.filter(category_id=category_id)

    categories = Category.objects.all()
    return render(request, 'events/event_list.html', {'events': events, 'categories': categories})

@login_required
def event_create(request):
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            # 1. Ensure user profile exists (prevents DB crash)
            Profile.objects.get_or_create(user=request.user)
            
            event = form.save(commit=False)
            event.organizer = request.user
            
            # 2. Force slug generation directly here
            if not event.slug:
                event.slug = slugify(event.title)
                
            event.save()
            
            messages.success(request, "Event created successfully!")
            return redirect('event_detail', slug=event.slug)
    else:
        form = EventForm()
    return render(request, 'events/event_form.html', {'form': form, 'action': 'Create'})

def event_detail(request, slug):
    event = get_object_or_404(Event, slug=slug)
    already_registered = False
    
    if request.user.is_authenticated:
        already_registered = Registration.objects.filter(event=event, attendee_email=request.user.email).exists()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to register.")
            return redirect('login')
            
        form = RegistrationForm(request.POST, event=event)
        if form.is_valid():
            reg = form.save(commit=False)
            reg.event = event
            reg.save()
            messages.success(request, "You have successfully registered for this event!")
            return redirect('event_detail', slug=slug)
    else:
        form = RegistrationForm(event=event)

    return render(request, 'events/event_detail.html', {
        'event': event, 
        'form': form,
        'already_registered': already_registered
    })

@login_required
def event_update(request, slug):
    event = get_object_or_404(Event, slug=slug)
    if event.organizer != request.user:
        messages.error(request, "You can only edit your own events.")
        return redirect('home')

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, "Event updated.")
            return redirect('event_detail', slug=event.slug)
    else:
        form = EventForm(instance=event)
    return render(request, 'events/event_form.html', {'form': form, 'action': 'Update'})

@login_required
def event_delete(request, slug):
    event = get_object_or_404(Event, slug=slug)
    if event.organizer != request.user:
        messages.error(request, "Not allowed.")
        return redirect('home')
        
    if request.method == 'POST':
        event.delete()
        messages.info(request, "Event deleted.")
        return redirect('my_events')
    return render(request, 'events/event_confirm_delete.html', {'event': event})

@login_required
def my_events(request):
    events = Event.objects.filter(organizer=request.user).order_by('-start_date')
    return render(request, 'events/my_events.html', {'events': events})

@login_required
def my_bookings(request):
    bookings = Registration.objects.filter(attendee_email=request.user.email).order_by('-registered_at')
    return render(request, 'events/my_bookings.html', {'bookings': bookings})


# ==========================================
# 3D VIEW & WENDY AI
# ==========================================

def three_d_view(request):
    return render(request, 'events/3d_page.html')

def wendy_chat(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').lower().strip()
            
            # 1. Inventory & Shop Management
            if any(word in user_message for word in ['inventory', 'stock', 'shop', 'store', 'item', 'product']):
                reply = "The Shop Inventory is where you manage your physical items. You can track how many you have in stock, their daily rental price, and see your total revenue. Find it under the 'Shop & Planning' menu!"
            
            # 2. Staff & Laundry
            elif any(word in user_message for word in ['staff', 'clean', 'laundry', 'payment', 'pay', 'salary', 'wage']):
                reply = "You can track staff laundry payments under 'Shop & Planning' -> 'Staff Payments'. You can log items cleaned, calculate total earned, amount paid, and see the balance remaining!"

            # 3. Sales & Revenue
            elif any(word in user_message for word in ['sale', 'sell', 'sold', 'revenue', 'money', 'profit', 'record']):
                reply = "To record a sale, go to the Shop Inventory, find the item, and click 'Record Sale'. The system will automatically deduct the sold quantity from your stock and add the revenue to your 'Total Sales' column."

            # 4. Controls & Navigation
            elif any(word in user_message for word in ['click', 'mouse', 'keyboard', 'control', 'button', 'move', 'drag', 'rotate']):
                reply = "For the 3D Planner: Left-click and hold to drag items around the room. Right-click and hold to rotate the camera. When in Walkthrough mode, use W, A, S, D to move and click/drag to look around."

            # 5. Specific App Features
            elif any(word in user_message for word in ['feature', 'capabilit', 'what can this app do', 'what does this app do', 'what can i do', 'help me']):
                reply = "Vows&VenturesEvents is packed with features! You can create events, book tickets, manage your shop inventory, track staff laundry payments, and use my favorite: the 3D Venue Planner."

            # 6. Identity
            elif any(word in user_message for word in ['who are you', 'your name', 'wendy', 'what are you', 'your purpose']):
                reply = "I am W.E.N.D.Y, which stands for Wide Event Navigation & Data Yielder. I'm the AI assistant built into Vows&VenturesEvents to make your event planning seamless!"
            
            # 7. Admin Section
            elif any(word in user_message for word in ['admin', 'database', 'backend']):
                reply = "The Admin section is where you manage the database. You can add, edit, or delete Categories, Events, Registrations, Inventory, and User Profiles."

            # 8. 3D Planner
            elif any(word in user_message for word in ['3d', 'planner', 'visualize', 'walkthrough', 'design', 'layout', 'virtual']):
                reply = "To use the 3D Planner, just click '3D Experience' in the navbar. You can drag items into the room, rotate them, and even click 'Enter Walkthrough' to do a first-person tour of your venue!"

            # 9. Booking / Attending
            elif any(word in user_message for word in ['book', 'ticket', 'attend', 'register', 'rsvp', 'buy', 'cancel']):
                reply = "To book a ticket, go to the 'Events' menu and select 'Browse Events'. Click on an event you like, and hit 'Get Tickets'. If you need to view your tickets, head over to 'My Bookings'."

            # 10. Hosting / Creating / Editing
            elif any(word in user_message for word in ['create', 'host', 'organize', 'make an', 'new event', 'edit', 'delete']):
                reply = "To host or manage an event, ensure you are logged in as an Organizer. Click 'Create Event' in the Events menu. Once created, you can view, edit, or delete it by clicking 'My Events'."

            # 11. Password Reset
            elif any(word in user_message for word in ['reset', 'forgot', 'change password', 'forget']):
                reply = "If you forgot your password, go to the Login page and click the 'Forgot Password?' link. If you are already logged in, you can change it from the Admin panel."

            # 12. Profile / Account
            elif any(word in user_message for word in ['profile', 'account', 'setting', 'role']):
                reply = "In the 'Profile' section, you can view your account details and see your role (Organizer or Attendee)."

            # 13. About & Contact
            elif any(word in user_message for word in ['about', 'who is the company', 'vows', 'ventures', 'story', 'gallery']):
                reply = "Vows&VenturesEvents is a premier event planning company. You can see our story and a gallery of our recent events by clicking 'About' in the navbar!"
            elif any(word in user_message for word in ['contact', 'phone', 'email', 'locat', 'address', 'reach', 'where']):
                reply = "Need to reach us? Click the 'Contact' link in the navbar! You'll find our phone number, email address, physical location, and a form to send us a message."

            # 14. Greetings
            elif any(word in user_message for word in ['hello', 'hi ', 'hey', 'greetings']) or user_message == 'hi':
                replies = [
                    "Hello! I'm W.E.N.D.Y. Are you looking to host an event or attend one?",
                    "Hi there! Ready to plan something amazing? I can help you create an event or navigate our 3D planner.",
                    "Hey! Welcome to Vows&VenturesEvents. How can I assist you today?"
                ]
                reply = random.choice(replies)

            # 15. Fallback
            else:
                replies = [
                    "I'm still learning! You can ask me about 'App Features', 'Inventory', 'Staff Payments', '3D planning', 'booking tickets', or 'creating events'.",
                    "Hmm, I didn't quite catch that. I'm best at helping with the 3D venue planner, inventory management, booking tickets, or hosting events!",
                    "Try asking about our features!"
                ]
                reply = random.choice(replies)

            return JsonResponse({'reply': reply})
            
        except Exception as e:
            return JsonResponse({'reply': "Oops, my brain glitched. Please try again."})
            
    return JsonResponse({'error': 'Invalid request'}, status=400)


# ==========================================
# INVENTORY & SALES VIEWS
# ==========================================

@login_required
def inventory_list(request):
    items = InventoryItem.objects.all().order_by('category', 'name')
    return render(request, 'events/inventory.html', {'items': items})

@login_required
def add_inventory_item(request):
    if request.method == 'POST':
        form = InventoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Inventory item added successfully!")
            return redirect('inventory_list')
    else:
        form = InventoryForm()
    return render(request, 'events/add_inventory.html', {'form': form})

@login_required
def delete_inventory_item(request, item_id):
    item = get_object_or_404(InventoryItem, id=item_id)
    if request.method == 'POST':
        item.delete()
        messages.success(request, f"'{item.name}' was deleted from inventory.")
        return redirect('inventory_list')
    return render(request, 'events/delete_inventory.html', {'item': item})

@login_required
def record_sale(request, item_id):
    item = get_object_or_404(InventoryItem, id=item_id)
    if request.method == 'POST':
        form = RecordSaleForm(request.POST)
        if form.is_valid():
            sale = form.save(commit=False)
            sale.item = item
            sale.price_at_sale = item.price_per_day
            
            if item.quantity >= sale.quantity_sold:
                item.quantity -= sale.quantity_sold
                item.save()
                sale.save()
                messages.success(request, f"Sale recorded! {sale.quantity_sold} units deducted from stock.")
                return redirect('inventory_list')
            else:
                messages.error(request, f"Not enough stock! You only have {item.quantity} left.")
    else:
        form = RecordSaleForm()
    return render(request, 'events/record_sale.html', {'form': form, 'item': item})


# ==========================================
# STAFF PAYMENT TRACKER VIEWS
# ==========================================

@login_required
def cleaning_dashboard(request):
    jobs = CleaningJob.objects.all().order_by('-date_cleaned')
    
    total_earned = sum(job.total_earned() for job in jobs)
    total_paid = sum(job.amount_paid for job in jobs)
    total_balance = total_earned - total_paid

    return render(request, 'events/cleaning_dashboard.html', {
        'jobs': jobs,
        'total_earned': total_earned,
        'total_paid': total_paid,
        'total_balance': total_balance
    })

@login_required
def add_cleaning_job(request):
    if request.method == 'POST':
        form = CleaningJobForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cleaning job logged successfully!")
            return redirect('cleaning_dashboard')
    else:
        form = CleaningJobForm()
    return render(request, 'events/add_cleaning_job.html', {'form': form})

@login_required
def add_laundry_service(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        price = request.POST.get('price')
        if name and price:
            LaundryService.objects.create(name=name, price=price)
            messages.success(request, f"Added {name} to the laundry price list.")
            return redirect('cleaning_dashboard')
    return render(request, 'events/add_laundry_service.html')


# ==========================================
# STATIC PAGES (ABOUT & CONTACT)
# ==========================================

def about_view(request):
    return render(request, 'events/about.html')

def contact_view(request):
    return render(request, 'events/contact.html')