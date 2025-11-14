from .models import Notification, Message, ReservationCart
from django.db.models import Q, Max, Count


def navbar_counts(request):
    """
    Context processor to add notification, message, and cart counts to all templates
    Also provides recent notifications and message conversations for navbar dropdowns
    """
    context = {
        'unread_notifications_count': 0,
        'unread_messages_count': 0,
        'total_cart_count': 0,
        'recent_notifications': [],
        'message_conversations': [],
        'admin_unread_notifications_count': 0,
        'admin_recent_notifications': [],
    }
    
    if request.user.is_authenticated:
        # Admin notifications (only notifications where user is null - admin-specific)
        if request.user.is_staff:
            context['admin_unread_notifications_count'] = Notification.objects.filter(
                user__isnull=True,
                read=False
            ).count()
            
            context['admin_recent_notifications'] = Notification.objects.filter(
                user__isnull=True,
                read=False
            ).order_by('-created_at')[:5]
        
        # User notifications (only notifications for this specific user)
        context['unread_notifications_count'] = Notification.objects.filter(
            user=request.user, 
            read=False
        ).count()
        
        # Get recent notifications (last 5 unread)
        context['recent_notifications'] = Notification.objects.filter(
            user=request.user,
            read=False
        ).order_by('-created_at')[:5]
        
        # Get unread message count
        context['unread_messages_count'] = Message.objects.filter(
            recipient=request.user, 
            is_read=False
        ).count()
        
        # Get recent message conversations (last 5 conversations with latest message)
        # Get all users who have sent or received messages with current user
        sent_to = Message.objects.filter(sender=request.user).values_list('recipient', flat=True).distinct()
        received_from = Message.objects.filter(recipient=request.user).values_list('sender', flat=True).distinct()
        conversation_users = set(list(sent_to) + list(received_from))
        
        conversations = []
        for user_id in list(conversation_users)[:5]:  # Limit to 5 conversations
            if user_id:  # Skip None values
                # Get the latest message in this conversation
                latest_message = Message.objects.filter(
                    Q(sender=request.user, recipient_id=user_id) |
                    Q(sender_id=user_id, recipient=request.user)
                ).order_by('-created_at').first()
                
                if latest_message:
                    # Count unread messages from this user
                    unread_count = Message.objects.filter(
                        sender_id=user_id,
                        recipient=request.user,
                        is_read=False
                    ).count()
                    
                    conversations.append({
                        'user': latest_message.sender if latest_message.sender != request.user else latest_message.recipient,
                        'latest_message': latest_message,
                        'unread_count': unread_count
                    })
        
        # Sort by latest message time
        conversations.sort(key=lambda x: x['latest_message'].created_at, reverse=True)
        context['message_conversations'] = conversations[:5]
        
        # Calculate total cart count (order cart + reservation cart)
        order_cart_count = len(request.session.get('cart', {}))
        reservation_cart, _ = ReservationCart.objects.get_or_create(user=request.user)
        reservation_cart_count = reservation_cart.items.count()
        context['total_cart_count'] = order_cart_count + reservation_cart_count
    
    return context
