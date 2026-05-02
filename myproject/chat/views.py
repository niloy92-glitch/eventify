from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from .models import Conversation, Message
from users.services import client_base_context, vendor_base_context

@login_required(login_url="users:login")
@require_http_methods(["GET", "POST"])
def client_chat_view(request, conversation_id=None):
    if getattr(request.user, "role", None) != "client":
        return redirect("users:login")
    
    # Get all conversations for the client that are unlocked
    conversations = list(Conversation.objects.filter(client=request.user).order_by("-updated_at"))
    
    active_conversation = None
    chat_messages = []
    active_bookings = []
    
    if conversation_id:
        active_conversation = get_object_or_404(Conversation, pk=conversation_id, client=request.user)
        chat_messages = active_conversation.messages.all()
        active_bookings = active_conversation.active_bookings()
        
        # Mark unread messages from vendor as read
        unread_messages = active_conversation.messages.filter(is_read=False).exclude(sender=request.user)
        if unread_messages.exists():
            unread_messages.update(is_read=True)
        
        if request.method == "POST":
            content = request.POST.get("content", "").strip()
            if content and not active_conversation.is_locked:
                Message.objects.create(conversation=active_conversation, sender=request.user, content=content)
                active_conversation.save() # update updated_at
                return redirect(reverse("chat:client_chat_detail", args=[active_conversation.pk]))

    context = client_base_context(request, "messages")
    context.update({
        "page_name": "Messages",
        "conversations": conversations,
        "active_conversation": active_conversation,
        "chat_messages": chat_messages,
        "active_bookings": active_bookings,
    })
    return render(request, "chat/client_chat.html", context)


@login_required(login_url="users:login")
@require_http_methods(["GET", "POST"])
def vendor_chat_view(request, conversation_id=None):
    if getattr(request.user, "role", None) != "vendor":
        return redirect("users:login")
    
    conversations = list(Conversation.objects.filter(vendor=request.user).order_by("-updated_at"))
    
    active_conversation = None
    chat_messages = []
    active_bookings = []
    
    if conversation_id:
        active_conversation = get_object_or_404(Conversation, pk=conversation_id, vendor=request.user)
        chat_messages = active_conversation.messages.all()
        active_bookings = active_conversation.active_bookings()
        
        # Mark unread messages from client as read
        unread_messages = active_conversation.messages.filter(is_read=False).exclude(sender=request.user)
        if unread_messages.exists():
            unread_messages.update(is_read=True)
        
        if request.method == "POST":
            content = request.POST.get("content", "").strip()
            if content and not active_conversation.is_locked:
                Message.objects.create(conversation=active_conversation, sender=request.user, content=content)
                active_conversation.save() # update updated_at
                return redirect(reverse("chat:vendor_chat_detail", args=[active_conversation.pk]))

    context = vendor_base_context(request, "messages")
    context.update({
        "page_name": "Messages",
        "conversations": conversations,
        "active_conversation": active_conversation,
        "chat_messages": chat_messages,
        "active_bookings": active_bookings,
    })
    return render(request, "chat/vendor_chat.html", context)
