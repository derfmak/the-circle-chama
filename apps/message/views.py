from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .models import ContactMessage

def contact_view(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        message_text = request.POST.get('message', '').strip()
        
        if not name or not email or not message_text:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'public/contact.html')
        
        contact = ContactMessage.objects.create(
            name=name,
            email=email,
            phone=phone,
            message=message_text,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        admin_message = f"""
New contact form submission:

Name: {name}
Email: {email}
Phone: {phone or 'Not provided'}

Message:
{message_text}
        """
        
        send_mail(
            subject=f'New Contact Form Message from {name}',
            message=admin_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=False,
        )
        
        messages.success(request, 'Thank you for contacting us. We will respond shortly.')
        return redirect('contact')
    
    return render(request, 'public/contact.html')