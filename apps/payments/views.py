import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .mpesa import process_callback, verify_callback_signature

@csrf_exempt
@require_http_methods(['POST'])
def mpesa_callback_view(request):
    try:
        request_body = request.body
        
        signature = request.headers.get('X-Signature', '')
        
        if settings.MPESA_ENVIRONMENT == 'production':
            if not verify_callback_signature(request_body, signature):
                return JsonResponse({'error': 'Invalid signature'}, status=403)
        
        callback_data = json.loads(request_body)
        
        result = process_callback(callback_data)
        
        if result.get('success'):
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'message': result.get('error')}, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)