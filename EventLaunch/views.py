from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import logout
from django.shortcuts import redirect
from .models import Event, Category, Registration, Profile
from .forms import EventForm, RegistrationForm, SignupForm, ProfileForm
from .forms import ProfileForm

# ---------- AUTH ----------

def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Save role + name
            user.first_name = form.cleaned_data['full_name']
            user.save()

            profile, created = Profile.objects.get_or_create(
                user=user,
                defaults={'role': form.cleaned_data['role']}
            )
            if not created:
                profile.role = form.cleaned_data['role']
                profile.save()
            
            login(request, user)
            messages.success(request, f"Welcome, {user.first_name}!")
            return redirect('home')
    else:
        form = SignupForm()
    return render(request, 'auth/signup.html', {'form': form})





# ---------- HOME ----------

def home(request):
    events     = Event.objects.filter(status='published')[:6]
    categories = Category.objects.all()
    context = {
        'events':       events,
        'categories':   categories,
        'total_events': Event.objects.count(),
    }
    return render(request, 'events/home.html', context)


# ---------- EVENT LIST (with search + category filter) ----------

def event_list(request):
    events = Event.objects.filter(status='published')

    q        = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()

    if q:
        events = events.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(venue__icontains=q)
        )
    if category and category != 'All':
        events = events.filter(category__name=category)

    return render(request, 'events/event_list.html', {
        'events':     events,
        'categories': Category.objects.all(),
        'query':      q,
        'selected':   category,
    })


# ---------- EVENT DETAIL ----------

def event_detail(request, slug):
    event = get_object_or_404(Event, slug=slug)
    form  = RegistrationForm(event=event)

    already_registered = False
    if request.user.is_authenticated:
        already_registered = Registration.objects.filter(
            event=event,
            attendee_email=request.user.email,
            status='confirmed'
        ).exists()

    if request.method == 'POST':
        form = RegistrationForm(request.POST, event=event)
        if form.is_valid():
            reg = form.save(commit=False)
            reg.event = event
            reg.status = 'confirmed'
            reg.save()
            messages.success(request, "You're registered!")
            return redirect('event_detail', slug=slug)

    is_organizer = request.user.is_authenticated and event.organizer == request.user

    return render(request, 'events/event_detail.html', {
        'event':              event,
        'form':               form,
        'already_registered': already_registered,
        'is_organizer':       is_organizer,
        'seats_left':         event.seats_left,
    })


# ---------- CREATE / UPDATE / DELETE EVENT ----------

@login_required
def event_create(request):
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            messages.success(request, "Event created!")
            return redirect('event_detail', slug=event.slug)
    else:
        form = EventForm()
    return render(request, 'events/event_form.html',
                  {'form': form, 'action': 'Create'})


@login_required
def event_update(request, slug):
    event = get_object_or_404(Event, slug=slug)
    if event.organizer != request.user:
        messages.error(request, "You can only edit your own events.")
        return redirect('home')

    form = EventForm(request.POST or None,
                     request.FILES or None,
                     instance=event)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Event updated.")
        return redirect('event_detail', slug=event.slug)

    return render(request, 'events/event_form.html',
                  {'form': form, 'action': 'Update'})


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


# ---------- MY EVENTS (organizer) ----------

@login_required
def my_events(request):
    events = Event.objects.filter(organizer=request.user).order_by('-start_date')
    return render(request, 'events/my_events.html', {'events': events})


# ---------- MY BOOKINGS (attendee) ----------

@login_required
def my_bookings(request):
    now = timezone.now()

    upcoming = Registration.objects.filter(
        attendee_email=request.user.email,
        status='confirmed',
        event__start_date__gte=now
    ).select_related('event').order_by('event__start_date')

    past = Registration.objects.filter(
        attendee_email=request.user.email,
        status='confirmed',
        event__start_date__lt=now
    ).select_related('event').order_by('-event__start_date')

    return render(request, 'events/my_bookings.html', {
        'upcoming': upcoming,
        'past':     past,
    })


@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Registration, id=booking_id,
                                attendee_email=request.user.email)
    booking.status = 'cancelled'
    booking.save()
    messages.info(request, "Booking cancelled.")
    return redirect('my_bookings')


# ---------- PROFILE ----------

@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user.profile)

    return render(request, 'auth/profile.html', {
        'form':    form,
        'profile': request.user.profile,
    })


    from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Event, Category, Registration, Profile
from .forms import EventForm, RegistrationForm, CategoryForm

# ... (keep your existing home, event_list, event_detail, event_create, event_update views here) ...

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'events/signup.html', {'form': form})

@login_required
def my_bookings(request):
    # Get all registrations for the currently logged-in user
    registrations = Registration.objects.filter(attendee_email=request.user.email)
    return render(request, 'events/my_bookings.html', {'registrations': registrations})

@login_required
def my_events(request):
    # Get all events created by the currently logged-in user
    events = Event.objects.filter(organizer=request.user)
    return render(request, 'events/my_events.html', {'events': events})

def event_confirm_delete(request, slug):
    event = get_object_or_404(Event, slug=slug)
    if request.method == 'POST':
        event.delete()
        messages.success(request, "Event deleted.")
        return redirect('my_events')
    return render(request, 'events/event_confirm_delete.html', {'event': event})


def logout_view(request):
    logout(request)
    return redirect('home')

def three_d_view(request):
    return render(request, 'events/3d_page.html')    

from django.http import JsonResponse
import json
import random

def wendy_chat(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').lower().strip()
            
            # 1. Inventory & Shop Management
            if any(word in user_message for word in ['inventory', 'stock', 'shop', 'store', 'item', 'product']):
                reply = "The Shop Inventory is where you manage your physical items (like chairs and tents). You can track how many you have in stock, their daily rental price, and see your total revenue. Find it under the 'Shop & Planning' menu!"
            
            # About Us
            elif any(word in user_message for word in ['about', 'who is the company', 'ralph', 'story', 'gallery']):
                reply = "RALPHEvents is a premier event planning company. You can see our story and a gallery of our 12 best recent events by clicking the 'About' link in the navbar!"

            # Contact
            elif any(word in user_message for word in ['contact', 'phone', 'email', 'locat', 'address', 'reach', 'where']):
                reply = "Need to reach us? Click the 'Contact' link in the navbar! You'll find our phone number, email address, physical location, and a form to send us a direct message."

            # 2. Sales & Revenue
            elif any(word in user_message for word in ['sale', 'sell', 'sold', 'revenue', 'money', 'profit', 'record']):
                reply = "To record a sale, go to the Shop Inventory, find the item, and click 'Record Sale'. The system will automatically deduct the sold quantity from your stock and add the revenue to your 'Total Sales' column. If you try to oversell, it will stop you!"
            
            # 3. Password Reset
            elif any(word in user_message for word in ['reset', 'forgot', 'change password', 'forget']):
                reply = "If you forgot your password, go to the Login page and click the 'Forgot Password?' link. If you are already logged in and want to change it, you can do that from the Admin panel under Users."
            
            # 4. Controls & Navigation
            elif any(word in user_message for word in ['click', 'mouse', 'keyboard', 'control', 'button', 'move', 'drag', 'rotate']):
                reply = "For the 3D Planner: Left-click and hold to drag items around the room. Right-click and hold to rotate the camera. When in Walkthrough mode, use W, A, S, D to move and click/drag to look around. For the rest of the site, just left-click buttons and links!"
            
            # 5. Specific App Features
            elif any(word in user_message for word in ['feature', 'capabilit', 'what can this app do', 'what does this app do', 'what can i do', 'help me']):
                reply = "RALPHEvents is packed with features! You can create events, book tickets, manage your shop inventory, track sales, and use my favorite: the 3D Venue Planner. What would you like to try?"
            
            # 6. Identity
            elif any(word in user_message for word in ['who are you', 'your name', 'wendy', 'what are you', 'your purpose']):
                reply = "I am W.E.N.D.Y, which stands for Wide Event Navigation & Data Yielder. I'm the AI assistant built into RALPHEvents to make your event planning seamless!"
            
            # 7. Admin Section
            elif any(word in user_message for word in ['admin', 'database', 'backend']):
                reply = "The Admin section (accessible to Organizers) is where you manage the database. You can add, edit, or delete Categories, Events, Registrations, Inventory, and User Profiles. It's the backend control room!"
            
            # 8. 3D Planner
            elif any(word in user_message for word in ['3d', 'planner', 'visualize', 'walkthrough', 'design', 'layout', 'virtual']):
                reply = "To use the 3D Planner, just click '3D Experience' in the Shop & Planning menu. You can drag items into the room, rotate them, and even click 'Enter Walkthrough' to do a first-person tour of your venue!"
            
            # 9. Booking / Attending
            elif any(word in user_message for word in ['book', 'ticket', 'attend', 'register', 'rsvp', 'buy', 'cancel']):
                reply = "To book a ticket, go to the 'Events' menu and select 'Browse Events'. Click on an event you like, and hit 'Get Tickets'. If you need to cancel or view your tickets, head over to 'My Bookings'."
            
            # 10. Hosting / Creating / Editing
            elif any(word in user_message for word in ['create', 'host', 'organize', 'make an', 'new event', 'edit', 'delete']):
                reply = "To host or manage an event, ensure you are logged in as an Organizer. Click 'Create Event' in the Events menu. Once created, you can view, edit, or delete it by clicking 'My Events'."
            
            # 11. Profile / Account
            elif any(word in user_message for word in ['profile', 'account', 'setting', 'role']):
                reply = "In the 'Profile' section, you can view your account details and see your role (Organizer or Attendee)."
            
            # 12. Dates / Times / Capacity
            elif any(word in user_message for word in ['date', 'time', 'capacity', 'price', 'cost', 'how many', 'when']):
                reply = "When creating an event, you can set the Start and End dates, the ticket price, and the maximum capacity (number of seats). Make sure your end date is after your start date!"
            
            # 13. Greetings
            elif any(word in user_message for word in ['hello', 'hi ', 'hey', 'greetings']) or user_message == 'hi':
                replies = [
                    "Hello! I'm W.E.N.D.Y, your event guide. Are you looking to host an event or attend one?",
                    "Hi there! Ready to plan something amazing? I can help you create an event, check your inventory, or navigate our 3D planner.",
                    "Hey! Welcome to RALPHEvents. How can I assist you today?"
                ]
                reply = random.choice(replies)
            
            # 14. Affirmations
            elif user_message in ['yes', 'yeah', 'sure', 'ok', 'okay', 'please']:
                reply = "Great! For which feature would you like more details? I can explain 'Creating Events', 'Booking Tickets', 'Shop Inventory', 'Admin', or the '3D Planner'."
            
            # 15. Negations / Goodbyes
            elif any(word in user_message for word in ['no', 'nope', 'bye', 'goodbye', 'see ya']):
                reply = "No problem! If you need me later, just click the chat bubble. Have a great day!"
            
            # 16. Thanks
            elif any(word in user_message for word in ['thank', 'thanks', 'awesome', 'cool', 'great']):
                reply = "You're very welcome! Let me know if there's anything else I can do to help you plan."
            
            # 17. Fallback
            else:
                replies = [
                    "I'm still learning! You can ask me about 'App Features', 'Profile', 'Inventory', 'Sales', '3D planning', 'controls', 'booking tickets', or 'creating events'.",
                    "Hmm, I didn't quite catch that. As your event guide, I'm best at helping with the 3D venue planner, inventory management, booking tickets, or hosting events!",
                    "That's an interesting question! While I'm not connected to the internet right now, I know everything there is to know about RALPHEvents. Try asking about our features!"
                ]
                reply = random.choice(replies)

            return JsonResponse({'reply': reply})
            
        except Exception as e:
            return JsonResponse({'reply': "Oops, my brain glitched. Please try again."})
            
    return JsonResponse({'error': 'Invalid request'}, status=400)



    




from .models import InventoryItem, Sale
from .forms import InventoryForm, RecordSaleForm
from django.shortcuts import get_object_or_404
from django.contrib import messages

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
def record_sale(request, item_id):
    item = get_object_or_404(InventoryItem, id=item_id)
    
    if request.method == 'POST':
        form = RecordSaleForm(request.POST)
        if form.is_valid():
            sale = form.save(commit=False)
            sale.item = item
            sale.price_at_sale = item.price_per_day # Lock in the price
            
            # Check if we have enough stock
            if item.quantity >= sale.quantity_sold:
                item.quantity -= sale.quantity_sold # Deduct stock
                item.save()
                sale.save()
                messages.success(request, f"Sale recorded! {sale.quantity_sold} units deducted from stock.")
                return redirect('inventory_list')
            else:
                messages.error(request, f"Not enough stock! You only have {item.quantity} left.")
    else:
        form = RecordSaleForm()

    return render(request, 'events/record_sale.html', {'form': form, 'item': item})


def about_view(request):
        return render(request, 'events/about.html')

def contact_view(request):
        return render(request, 'events/contact.html')


@login_required
def delete_inventory_item(request, item_id):
    item = get_object_or_404(InventoryItem, id=item_id)

    if request.method == 'POST':
        item.delete()
        messages.success(request, f"'{item.name}' was deleted from inventory")
        return redirect('inventory_list')

    return render(request, 'events/delete_inventory.html', {'item': item})            