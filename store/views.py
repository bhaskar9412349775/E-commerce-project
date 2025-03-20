from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Product, Category, Cart, CartItem, Order, OrderItem, ShippingAddress, WishlistItem
from .forms import UserRegistrationForm, CheckoutForm, ProfileForm, AddressForm

def home(request):
    featured_products = Product.objects.filter(is_featured=True)[:8]
    categories = Category.objects.all()
    special_offers = Product.objects.filter(discount_price__isnull=False)[:3]
    
    context = {
        'featured_products': featured_products,
        'categories': categories,
        'special_offers': special_offers,
    }
    return render(request, 'store/home.html', context)

def product_list(request):
    category_id = request.GET.get('category')
    search_query = request.GET.get('search')
    sort_by = request.GET.get('sort', 'name')  # Default sort by name
    
    products = Product.objects.all()
    
    if category_id:
        products = products.filter(category_id=category_id)
        selected_category = get_object_or_404(Category, id=category_id)
    else:
        selected_category = None
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Sorting
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    else:  # sort_by == 'name'
        products = products.order_by('name')
    
    paginator = Paginator(products, 12)  # Show 12 products per page
    page = request.GET.get('page')
    products = paginator.get_page(page)
    
    categories = Category.objects.all()
    
    context = {
        'products': products,
        'categories': categories,
        'selected_category': selected_category,
        'search_query': search_query,
        'sort_by': sort_by,
    }
    return render(request, 'store/product_list.html', context)

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    related_products = Product.objects.filter(category=product.category).exclude(id=product_id)[:4]
    
    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'store/product_detail.html', context)

@login_required
def profile(request):
    if request.method == 'POST':
        profile_form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('profile')
    else:
        profile_form = ProfileForm(instance=request.user)
    
    addresses = ShippingAddress.objects.filter(user=request.user)
    recent_orders = Order.objects.filter(user=request.user).order_by('-created_at')[:5]
    wishlist_items = WishlistItem.objects.filter(user=request.user)
    
    context = {
        'profile_form': profile_form,
        'addresses': addresses,
        'recent_orders': recent_orders,
        'wishlist_items': wishlist_items,
        'active_tab': request.GET.get('tab', 'account'),
    }
    return render(request, 'store/profile.html', context)

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Filter by date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date and end_date:
        orders = orders.filter(created_at__range=[start_date, end_date])
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)
    
    # Search by order number or product name
    search = request.GET.get('search')
    if search:
        orders = orders.filter(
            Q(order_number__icontains=search) |
            Q(items__product__name__icontains=search)
        ).distinct()
    
    paginator = Paginator(orders, 10)  # Show 10 orders per page
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    
    context = {
        'orders': orders,
        'start_date': start_date,
        'end_date': end_date,
        'status': status,
        'search': search,
    }
    return render(request, 'store/order_history.html', context)

@login_required
def wishlist(request):
    wishlist_items = WishlistItem.objects.filter(user=request.user)
    return render(request, 'store/wishlist.html', {'wishlist_items': wishlist_items})

@login_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    WishlistItem.objects.get_or_create(user=request.user, product=product)
    messages.success(request, f'{product.name} has been added to your wishlist.')
    return redirect('product_detail', product_id=product_id)

@login_required
def remove_from_wishlist(request, item_id):
    wishlist_item = get_object_or_404(WishlistItem, id=item_id, user=request.user)
    wishlist_item.delete()
    messages.success(request, f'{wishlist_item.product.name} has been removed from your wishlist.')
    return redirect('wishlist')

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        
        if product.stock < quantity:
            messages.error(request, 'Sorry, we don\'t have enough stock for this quantity.')
            return redirect('product_detail', product_id=product_id)
        
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        
        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
        
        cart_item.save()
        messages.success(request, f'Added {quantity} {product.name} to your cart.')
    
    return redirect('cart')

@login_required
def cart(request):
    cart = Cart.objects.filter(user=request.user).first()
    context = {'cart': cart}
    if cart:
        context['cart_items'] = cart.items.all()
    return render(request, 'store/cart.html', context)

@login_required
def update_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 0))
        if quantity > 0:
            if quantity <= cart_item.product.stock:
                cart_item.quantity = quantity
                cart_item.save()
            else:
                messages.error(request, 'Sorry, we don\'t have enough stock for this quantity.')
        else:
            cart_item.delete()
    
    return redirect('cart')

@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if request.method == 'POST':
        cart_item.delete()
    return redirect('cart')

@login_required
def checkout(request):
    cart = Cart.objects.filter(user=request.user).first()
    if not cart or not cart.items.exists():
        messages.error(request, 'Your cart is empty.')
        return redirect('cart')
    
    if request.method == 'POST':
        form = CheckoutForm(request.user, request.POST)
        if form.is_valid():
            # Create or get shipping address
            if form.cleaned_data['use_new_address']:
                shipping_address = ShippingAddress.objects.create(
                    user=request.user,
                    street_address=form.cleaned_data['street_address'],
                    apartment_address=form.cleaned_data['apartment_address'],
                    city=form.cleaned_data['city'],
                    state=form.cleaned_data['state'],
                    country=form.cleaned_data['country'],
                    zip_code=form.cleaned_data['zip_code']
                )
            else:
                shipping_address = form.cleaned_data['shipping_address']
            
            # Create order
            order = Order.objects.create(
                user=request.user,
                shipping_address=shipping_address,
                total_price=cart.get_total_price()
            )
            
            # Create order items
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=cart_item.product.price
                )
                # Update product stock
                product = cart_item.product
                product.stock -= cart_item.quantity
                product.save()
            
            # Clear the cart
            cart.delete()
            
            return redirect('order_confirmation', order_id=order.id)
    else:
        form = CheckoutForm(request.user)
    
    context = {
        'form': form,
        'cart': cart,
        'cart_items': cart.items.all()
    }
    return render(request, 'store/checkout.html', context)

@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'store/order_confirmation.html', {'order': order})

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful. Welcome!')
            return redirect('home')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form}) 