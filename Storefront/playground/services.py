from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from playground.models import Order, OrderItem, Payment

def finalize_order_payment(order, payment_id=None):
    """
    Finalizes an order after successful payment:
    - Deducts inventory
    - Marks order as PAID
    - Creates payment record
    """

    if order.status != Order.STATUS_PENDING:
        raise ValidationError("Order is not pending")

    with transaction.atomic():
        # Deduct inventory
        for item in order.items.select_related('product'):
            product = item.product

            if item.quantity > product.inventory:
                raise ValidationError(
                    f"Insufficient stock for {product.title}"
                )

            product.inventory -= item.quantity
            product.save()

        # Create or update payment
        Payment.objects.update_or_create(
            order=order,
            defaults={
                'amount': order.total_price,
                'status': Payment.STATUS_SUCCESS,
                'payment_id': payment_id or f"MOCK-{order.id}",
            }
        )

        # Update order status
        order.status = Order.STATUS_PAID
        order.save()

    return order



def update_order_item_status_service(*, order_item, seller, new_status):
    """
    Safely update an OrderItem status.

    Guarantees:
    - Seller ownership
    - Valid state transitions
    - Idempotency
    - Atomic updates
    """

    # 1️⃣ Ownership check (defense in depth)
    if order_item.seller != seller:
        raise PermissionDenied("You do not own this order item")

    # 2️⃣ Valid transitions (state machine)
    valid_transitions = {
        OrderItem.STATUS_PENDING: [OrderItem.STATUS_SHIPPED],
        OrderItem.STATUS_SHIPPED: [OrderItem.STATUS_DELIVERED],
        OrderItem.STATUS_DELIVERED: [],
    }

    # 3️⃣ Idempotency (same request twice = no side effects)
    if order_item.status == new_status:
        return order_item

    # 4️⃣ Transition validation
    allowed = valid_transitions.get(order_item.status, [])
    if new_status not in allowed:
        raise ValidationError(
            f"Cannot change status from '{order_item.status}' to '{new_status}'"
        )

    # 5️⃣ Atomic update
    with transaction.atomic():
        order_item.status = new_status
        order_item.save(update_fields=['status'])

        # 6️⃣ Auto-update parent order (derived state)
        order = order_item.order
        if not order.items.exclude(status=OrderItem.STATUS_DELIVERED).exists():
            order.status = Order.STATUS_DELIVERED
            order.save(update_fields=['status'])

    return order_item
