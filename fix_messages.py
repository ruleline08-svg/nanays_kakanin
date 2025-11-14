#!/usr/bin/env python
"""
Quick script to check and fix message read status
Run this from the Django project directory: python fix_messages.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nanays_kakanin.settings')
django.setup()

from kakanin.models import Message
from django.contrib.auth.models import User

def check_unread_messages():
    """Check all unread messages"""
    print("=" * 60)
    print("Checking Unread Messages")
    print("=" * 60)
    
    unread = Message.objects.filter(is_read=False).select_related('sender', 'recipient')
    
    if not unread.exists():
        print("✓ No unread messages found!")
        return
    
    print(f"\nFound {unread.count()} unread messages:\n")
    
    for msg in unread:
        sender_name = msg.sender.username if msg.sender else "System"
        recipient_name = msg.recipient.username if msg.recipient else "Unknown"
        print(f"ID: {msg.id}")
        print(f"  From: {sender_name}")
        print(f"  To: {recipient_name}")
        print(f"  Subject: {msg.subject}")
        print(f"  Created: {msg.created_at}")
        print(f"  Read: {msg.is_read}")
        print("-" * 40)

def mark_all_as_read(username):
    """Mark all messages for a specific user as read"""
    try:
        user = User.objects.get(username=username)
        unread = Message.objects.filter(recipient=user, is_read=False)
        count = unread.count()
        
        if count == 0:
            print(f"✓ No unread messages for {username}")
            return
        
        unread.update(is_read=True)
        print(f"✓ Marked {count} messages as read for {username}")
        
    except User.DoesNotExist:
        print(f"✗ User '{username}' not found")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'check':
            check_unread_messages()
        elif sys.argv[1] == 'fix' and len(sys.argv) > 2:
            username = sys.argv[2]
            mark_all_as_read(username)
        else:
            print("Usage:")
            print("  python fix_messages.py check              - Check all unread messages")
            print("  python fix_messages.py fix <username>     - Mark all messages as read for user")
    else:
        check_unread_messages()
