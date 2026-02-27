from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.db.models import Sum, F, IntegerField, DecimalField, Value
from .forms import CustomUserCreationForm, SellerSignupForm, ProductForm
from .decorators import seller_required
from .models import Product, Order, OrderItem, CartItem, Payment
from django.db.models.functions import Coalesce
from django.db.models import Q


# --------------------
# HOME & PRODUCTS
# --------------------

def home(request):
    products = Product.objects.filter(available=True)
    return render(request, 'playground/home.html', {'products': products})


def product_detail(request, id):
    product = get_object_or_404(Product, id=id, available=True)
    images = product.images.all()
    return render(request, 'playground/product_detail.html', {
        'product': product,
        'images': images
    })

def browse_products(request):
    products = Product.objects.filter(available=True)

    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        )

    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if min_price:
        products = products.filter(base_price__gte=min_price)
    if max_price:
        products = products.filter(base_price__lte=max_price)

    sort = request.GET.get('sort')
    if sort == 'price_low':
        products = products.order_by('base_price')
    elif sort == 'price_high':
        products = products.order_by('-base_price')
    elif sort == 'newest':
        products = products.order_by('-created')

    return render(request, 'playground/browse_products.html', {
        'products': products,
        'query': query,
        'min_price': min_price,
        'max_price': max_price,
        'sort': sort,
    })


# --------------------
# AUTH
# --------------------

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('playground:home')
    else:
        form = CustomUserCreationForm()

    return render(request, 'registration/signup.html', {'form': form})


class CustomLoginView(LoginView):
    template_name = 'registration/login.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        merge_cart(self.request, self.request.user)
        return response

    def get_success_url(self):
        if getattr(self.request.user, 'is_seller', False):
            return '/seller/dashboard/'
        return '/'


# --------------------
# CART (SESSION + DB)
# --------------------

def cart(request):
    items = []

    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user)

        for item in cart_items:
            items.append({
                'product': item.product,
                'quantity': item.quantity,
                'total': item.get_total_price(),
                'id': item.product.id,   # IMPORTANT
                'is_db': True
            })
    else:
        cart = request.session.get('cart', {})
        for product_id, qty in cart.items():
            product = get_object_or_404(Product, id=product_id)
            items.append({
                'product': product,
                'quantity': qty,
                'total': product.get_current_price() * qty,
                'id': product.id,
                'is_db': False
            })

    total = sum(item['total'] for item in items)

    return render(request, 'playground/cart.html', {
        'items': items,
        'total': total
    })


def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, available=True)

    if request.user.is_authenticated:
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product
        )
        if not created:
            cart_item.quantity += 1
        cart_item.save()
    else:
        cart = request.session.get('cart', {})
        pid = str(product_id)
        cart[pid] = cart.get(pid, 0) + 1
        request.session['cart'] = cart

    return redirect('playground:cart')


def remove_from_cart(request, id):
    if request.user.is_authenticated:
        CartItem.objects.filter(
            user=request.user,
            product_id=id
        ).delete()
    else:
        cart = request.session.get('cart', {})
        cart.pop(str(id), None)
        request.session['cart'] = cart

    return redirect('playground:cart')


def increase_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.user.is_authenticated:
        item, _ = CartItem.objects.get_or_create(
            user=request.user,
            product=product
        )
        if item.quantity < product.inventory:
            item.quantity += 1
            item.save()
    else:
        cart = request.session.get('cart', {})
        qty = cart.get(str(product_id), 0)
        if qty < product.inventory:
            cart[str(product_id)] = qty + 1
        request.session['cart'] = cart

    return redirect('playground:cart')


def decrease_cart(request, product_id):
    if request.user.is_authenticated:
        try:
            item = CartItem.objects.get(
                user=request.user,
                product_id=product_id
            )
            item.quantity -= 1
            if item.quantity <= 0:
                item.delete()
            else:
                item.save()
        except CartItem.DoesNotExist:
            pass
    else:
        cart = request.session.get('cart', {})
        if str(product_id) in cart:
            cart[str(product_id)] -= 1
            if cart[str(product_id)] <= 0:
                del cart[str(product_id)]
        request.session['cart'] = cart

    return redirect('playground:cart')


def merge_cart(request, user):
    session_cart = request.session.get('cart', {})

    for product_id, qty in session_cart.items():
        product = get_object_or_404(Product, id=product_id)
        cart_item, _ = CartItem.objects.get_or_create(
            user=user,
            product=product
        )
        cart_item.quantity += qty
        cart_item.save()

    request.session.pop('cart', None)


# --------------------
# CHECKOUT & ORDERS
# --------------------


@login_required
def checkout(request):
    items = CartItem.objects.select_for_update().filter(user=request.user)

    if not items.exists():
        return redirect('playground:cart')

    with transaction.atomic():
        total = 0

        for item in items:
            if item.quantity > item.product.inventory:
                return redirect('playground:cart')

            item.product.inventory -= item.quantity
            item.product.save()

            total += item.get_total_price()

        order = Order.objects.create(
            user=request.user,
            total_price=total
        )

        for item in items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                seller=item.product.seller,
                quantity=item.quantity,
                price_at_purchase=item.product.get_current_price()
            )

        items.delete()

    return redirect('playground:payment', order.id)




@login_required
def order_detail(request, id):
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product'),
        id=id,
        user=request.user
    )

    return render(request, 'playground/order_detail.html', {
        'order': order
    })



@login_required
def order_success(request, id):
    order = get_object_or_404(Order, id=id, user=request.user)
    return render(request, 'playground/order_success.html', {'order': order})

@login_required
def my_orders(request):
    orders = (
        Order.objects
        .filter(user=request.user)
        .prefetch_related('items__product')
        .order_by('-created_at')
    )

    return render(request, 'playground/my_orders.html', {
        'orders': orders
    })

@login_required
def payment(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user,
        status=Order.STATUS_PENDING
    )

    return render(request, 'playground/payment.html', {
        'order': order
    })

@login_required
def payment_success(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user,
        status=Order.STATUS_PENDING
    )

    with transaction.atomic():
        Payment.objects.create(
            order=order,
            payment_id=f"MOCK-{order.id}",
            amount=order.total_price,
            status='success'
        )

        order.status = Order.STATUS_PAID
        order.save()

    return render(request, 'playground/payment_success.html', {
        'order': order
    })


# --------------------
# SELLER
# --------------------

def seller_signup(request):
    if request.method == 'POST':
        form = SellerSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_seller = True
            user.save()
            login(request, user)
            return redirect('playground:seller_dashboard')
    else:
        form = SellerSignupForm()

    return render(request, 'seller/signup.html', {'form': form})


@login_required
@seller_required
def seller_dashboard(request):
    products = Product.objects.filter(seller=request.user)

    paid_items = OrderItem.objects.filter(
        seller=request.user,
        order__status=Order.STATUS_PAID
    )

    analytics = paid_items.aggregate(
        total_revenue=Coalesce(
            Sum(F('price_at_purchase') * F('quantity')),
            Value(0),
            output_field=DecimalField()
        ),
        total_items=Coalesce(
            Sum('quantity'),
            Value(0),
            output_field=IntegerField()
        ),
    )

    analytics['total_orders'] = (
        paid_items.values('order').distinct().count()
    )

    return render(request, 'seller/dashboard.html', {
        'products': products,
        'analytics': analytics
    })


@login_required
@seller_required
def seller_orders(request):
    order_items = (
        OrderItem.objects
        .filter(seller=request.user)
        .select_related('order', 'product')
    )

    return render(request, 'seller/orders.html', {
        'order_items': order_items
    })

@login_required
@seller_required
def update_order_item_status(request, item_id):
    item = get_object_or_404(
        OrderItem,
        id=item_id,
        seller=request.user
    )

    if request.method == 'POST':
        new_status = request.POST.get('status')

        if new_status in dict(OrderItem.STATUS_CHOICES):
            item.status = new_status
            item.save()

    return redirect('playground:seller_orders')



@login_required
@seller_required
def seller_add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user
            product.save()
            return redirect('playground:seller_dashboard')
    else:
        form = ProductForm()

    return render(request, 'seller/add_product.html', {'form': form})

@login_required
@seller_required
def seller_edit_product(request, id):
    product = get_object_or_404(
        Product,
        id=id,
        seller=request.user
    )

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('playground:seller_dashboard')
    else:
        form = ProductForm(instance=product)

    return render(
        request,
        'seller/edit_product.html',
        {'form': form, 'product': product}
    )

@login_required
@seller_required
def seller_delete_product(request, id):
    product = get_object_or_404(
        Product,
        id=id,
        seller=request.user
    )

    product.available = False
    product.save()

    return redirect('playground:seller_dashboard')


@login_required
@seller_required
def seller_analytics(request):
    analytics = (
        OrderItem.objects
        .filter(
            seller=request.user,
            order__status=Order.STATUS_PAID
        )
        .values('product__title')
        .annotate(
            total_quantity=Coalesce(Sum('quantity'), Value(0)),
            revenue=Coalesce(
                Sum(F('quantity') * F('price_at_purchase')),
                Value(0),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        )
        .order_by('-revenue')
    )

    return render(request, 'seller/analytics.html', {
        'analytics': analytics
    })
