from django.shortcuts import render, get_object_or_404, reverse
from myapp.models import Contact, Dish, Team, Category, Profile, Order
from django.http import HttpResponse,JsonResponse, HttpResponseRedirect
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout
from paypal.standard.forms import PayPalPaymentsForm
from django.conf import settings
import razorpay
from django.shortcuts import render
from .models import Dish,Cart
from django.shortcuts import get_object_or_404, redirect


def add_to_cart(request, id):
    if not request.user.is_authenticated:
        return redirect('login') # Bina login ke cart kaam nahi karega

    dish = Dish.objects.get(id=id)
    # Cart mein entry create karna
    cart_item, created = Cart.objects.get_or_create(
        user=request.user, 
        dish_name=dish.name,
        defaults={'price': dish.discounted_price}
    )
    
    if not created:
        cart_item.quantity += 1
        cart_item.save()

    # Wapas usi page par bhejne ke liye jahan se click kiya tha
    return redirect(request.META.get('HTTP_REFERER', 'all_dishes'))# Check karlein aapki model ka naam 'Dish' hi hai na

# def add_to_cart(request, dish_id):
#     dish = Dish.objects.get(id=dish_id)
#     # Cart mein save karne ka logic
#     Cart.objects.create(
#         user=request.user, 
#         dish_name=dish.name, 
#         price=dish.price
#     )
#     return redirect('/cart')

# Cart page dikhane ke liye
def cart_view(request):
    items = Cart.objects.filter(user=request.user)
    # Price aur Quantity ko multiply karke total nikalein
    total = sum(item.price * item.quantity for item in items)
    return render(request, 'cart.html', {'items': items, 'total': total})
def reduce_quantity(request, item_id):
    item = Cart.objects.get(id=item_id, user=request.user)
    if item.quantity > 1:
        item.quantity -= 1
        item.save()
    else:
        item.delete() # Agar 1 hai toh delete ho jaye
    return redirect('cart')
# Views.py mein ye badlav karein
def add_quantity(request, item_id):
    item = Cart.objects.get(id=item_id, user=request.user) # [cite: 1621]
    item.quantity += 1 # [cite: 1621]
    item.save() # [cite: 1621]
    return redirect('cart')

def search_view(request):
    query = request.GET.get('q')  # Form se 'q' name ka data lega
    results = []
    if query:
        # Dish ke naam mein query search karega
        results = Dish.objects.filter(name__icontains=query) 
    
    return render(request, 'search_results.html', {'results': results, 'query': query})

def index(request):
    context ={}
    cats = Category.objects.all().order_by('name')
    context['categories'] = cats
    # print()
    dishes = []
    for cat in cats:
        dishes.append({
            'cat_id':cat.id,
            'cat_name':cat.name,
            'cat_img':cat.image,
            'items':list(cat.dish_set.all().values())
        })
    context['menu'] = dishes
    return render(request,'index.html', context)

def contact_us(request):
    context={}
    if request.method=="POST":
        name = request.POST.get("name")
        em = request.POST.get("email")
        sub = request.POST.get("subject")
        msz = request.POST.get("message")
        
        obj = Contact(name=name, email=em, subject=sub, message=msz)
        obj.save()
        context['message']=f"Dear {name}, Thanks for your time!"

    return render(request,'contact.html', context)

def about(request):
    return render(request,'about.html')

def team_members(request):
    context={}
    members = Team.objects.all().order_by('name')
    context['team_members'] = members
    return render(request,'team.html', context)

def all_dishes(request):
    context={}
    dishes = Dish.objects.all()
    q = request.GET.get("q")
    if q:
        if q.isdigit():
            dishes = dishes.filter(category__id=q)
            context['dish_category'] = Category.objects.get(id=q).name
        else:
            # warna search by name
            dishes = dishes.filter(name__icontains=q)

    context['dishes'] = dishes
    return render(request, 'all_dishes.html', context)

def register(request):
    context={}
    if request.method=="POST":
        #fetch data from html form
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('pass')
        contact = request.POST.get('number')
        check = User.objects.filter(username=email)
        if len(check)==0:
            #Save data to both tables
            usr = User.objects.create_user(email, email, password)
            usr.first_name = name
            usr.save()

            profile = Profile(user=usr, contact_number = contact)
            profile.save()
            context['status'] = f"User {name} Registered Successfully!"
        else:
            context['error'] = f"A User with this email already exists"

    return render(request,'register.html', context)

def check_user_exists(request):
    email = request.GET.get('usern')
    check = User.objects.filter(username=email)
    if len(check)==0:
        return JsonResponse({'status':0,'message':'Not Exist'})
    else:
        return JsonResponse({'status':1,'message':'A user with this email already exists!'})

def signin(request):
    context={}
    if request.method=="POST":
        email = request.POST.get('email')
        passw = request.POST.get('password')

        check_user = authenticate(username=email, password=passw)
        if check_user:
            login(request, check_user)
            if check_user.is_superuser or check_user.is_staff:
                return HttpResponseRedirect('/admin')
            return HttpResponseRedirect('/dashboard')
        else:
            context.update({'message':'Invalid Login Details!','class':'alert-danger'})

    return render(request,'login.html', context)

def dashboard(request):
    context={}
    login_user = get_object_or_404(User, id = request.user.id)
    #fetch login user's details
    profile, created = Profile.objects.get_or_create(user=request.user)
    context['profile'] = profile

    #update profile
    if "update_profile" in request.POST:
        print("file=",request.FILES)
        name = request.POST.get('name')
        contact = request.POST.get('contact_number')
        add = request.POST.get('address')
       

        profile.user.first_name = name 
        profile.user.save()
        profile.contact_number = contact 
        profile.address = add 

        if "profile_pic" in request.FILES:
            pic = request.FILES['profile_pic']
            profile.profile_pic = pic
        profile.save()
        context['status'] = 'Profile updated successfully!'
    
    #Change Password 
    if "change_pass" in request.POST:
        c_password = request.POST.get('current_password')
        n_password = request.POST.get('new_password')

        check = login_user.check_password(c_password)
        if check==True:
            login_user.set_password(n_password)
            login_user.save()
            login(request, login_user)
            context['status'] = 'Password Updated Successfully!' 
        else:
            context['status'] = 'Current Password Incorrect!'

    #My Orders 
    orders = Order.objects.filter(customer__user__id=request.user.id).order_by('-id')
    context['orders']=orders    
    return render(request, 'dashboard.html', context)

def user_logout(request):
    logout(request)
    return HttpResponseRedirect('/')

def single_dish(request, id):
    context={}
    dish = get_object_or_404(Dish, id=id)

    if request.user.is_authenticated:
        cust = get_object_or_404(Profile, user__id = request.user.id)
        order = Order(customer=cust, item=dish)
        order.save()
        inv = f'INV0000-{order.id}'

        paypal_dict = {
            'business':settings.PAYPAL_RECEIVER_EMAIL,
            'amount':dish.discounted_price,
            'currency_code': 'INR',
            'item_name':dish.name,
            'user_id':request.user.id,
            'invoice':inv,
            'notify_url':'http://{}{}'.format(settings.HOST, reverse('paypal-ipn')),
            'return_url':'http://{}{}'.format(settings.HOST,reverse('payment_done')),
            'cancel_url':'http://{}{}'.format(settings.HOST,reverse('payment_cancel')),
        }

        order.invoice_id = inv 
        order.save()
        request.session['order_id'] = order.id

        form = PayPalPaymentsForm(initial=paypal_dict)
        context.update({'dish':dish, 'form':form})

    return render(request,'dish.html', context)

# # def payment_done(request):
#     pid = request.GET.get('PayerID')
#     order_id = request.session.get('order_id')
#     order_obj = Order.objects.get(id=order_id)
#     order_obj.status=True 
#     order_obj.payer_id = pid
#     order_obj.save()

#     return render(request, 'payment_successfull.html') 

# def payment_cancel(request):
#     ## remove comment to delete cancelled order
#     # order_id = request.session.get('order_id')
#     # Order.objects.get(id=order_id).delete()

#     return render(request, 'payment_failed.html') 


def checkout(request):
    items = Cart.objects.filter(user=request.user)
    total = sum(item.price * item.quantity for item in items)
    amount_in_paise=int(total*100)
    
    # Sahi Keys yahan dalein
    RAZORPAY_KEY_ID = "rzp_test_SgFeRIG5hq06u1"
    RAZORPAY_SECRET = "r3fSF7dLY4jK60HvNR4xLbcS" # Ise dobara check karein
    
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_SECRET))
    
    order_params = {
        'amount': amount_in_paise, 
        'currency': 'INR',
        'payment_capture': '1'
    }
    
    try:
        razorpay_order = client.order.create(data=order_params)
        # order_id = razorpay_order['id']
        
        return render(request, 'payment.html', {
        'order_id': razorpay_order['id'],
        'total': total, # Display ke liye ₹169
        'amount': amount_in_paise, # Script ke liye 16900
        'razorpay_key_id': "rzp_test_SgFZZuG2raawK5"
    })
    except Exception as e:
        from django.http import HttpResponse
        return HttpResponse(f"Razorpay Error: {e}")