from .models import Cart

def cart_count(request):
    if request.user.is_authenticated:
        cart = request.user.cart if hasattr(request.user, 'cart') else None
        count = cart.items.count() if cart else 0
    else:
        count = 0
    return {'cart_count': count} 