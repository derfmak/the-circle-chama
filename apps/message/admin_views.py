from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.conf import settings
from .models import ContactMessage, MessageReply

admin_required = lambda view: login_required(user_passes_test(lambda u: u.is_admin)(view))

@admin_required
def admin_messages_view(request):
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    messages_list = ContactMessage.objects.all()
    
    if status:
        messages_list = messages_list.filter(status=status)
    if search:
        messages_list = messages_list.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(message__icontains=search)
        )
    
    paginator = Paginator(messages_list, 20)
    page = request.GET.get('page')
    messages_page = paginator.get_page(page)
    
    status_counts = {
        'new': ContactMessage.objects.filter(status='new').count(),
        'read': ContactMessage.objects.filter(status='read').count(),
        'replied': ContactMessage.objects.filter(status='replied').count(),
        'archived': ContactMessage.objects.filter(status='archived').count(),
    }
    
    context = {
        'messages': messages_page,
        'page_obj': messages_page,
        'status': status,
        'search': search,
        'status_counts': status_counts,
    }
    return render(request, 'admin/messages.html', context)

@admin_required
def admin_message_detail_view(request, message_id):
    contact = get_object_or_404(ContactMessage, id=message_id)
    
    if contact.status == 'new':
        contact.status = 'read'
        contact.save()
    
    context = {
        'contact': contact,
        'replies': contact.replies.all(),
    }
    return render(request, 'admin/message_detail.html', context)

@admin_required
def admin_reply_message_view(request, message_id):
    contact = get_object_or_404(ContactMessage, id=message_id)
    
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        body = request.POST.get('body', '').strip()
        
        if not subject or not body:
            messages.error(request, 'Subject and body are required.')
            return redirect('admin_reply_message', message_id=contact.id)
        
        reply = MessageReply.objects.create(
            message=contact,
            subject=subject,
            body=body,
            sent_by=request.user
        )
        
        full_message = f"""
Dear {contact.name},

{body}

Best regards,
THE CIRCLE Admin Team
        """
        
        send_mail(
            subject=f"Re: {subject}",
            message=full_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[contact.email],
            fail_silently=False,
        )
        
        contact.status = 'replied'
        contact.replied_at = timezone.now()
        contact.save()
        
        messages.success(request, f'Reply sent to {contact.email}')
        return redirect('admin_message_detail', message_id=contact.id)
    
    return render(request, 'admin/reply_message.html', {'contact': contact})

@admin_required
def admin_update_message_status_view(request, message_id):
    contact = get_object_or_404(ContactMessage, id=message_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['new', 'read', 'replied', 'archived']:
            contact.status = new_status
            contact.save()
            messages.success(request, f'Message marked as {contact.get_status_display()}.')
    
    return redirect('admin_message_detail', message_id=contact.id)

@admin_required
def admin_delete_message_view(request, message_id):
    contact = get_object_or_404(ContactMessage, id=message_id)
    
    if request.method == 'POST':
        email = contact.email
        contact.delete()
        messages.success(request, f'Message from {email} deleted successfully.')
        return redirect('admin_messages')
    
    context = {'contact': contact}
    return render(request, 'admin/delete_message.html', context)