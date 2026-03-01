import base64
import json
import requests
import hashlib
import hmac
from datetime import datetime
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from .models import StkPushLog, IdempotencyKey

def get_access_token():
    consumer_key = settings.MPESA_CONSUMER_KEY
    consumer_secret = settings.MPESA_CONSUMER_SECRET
    environment = settings.MPESA_ENVIRONMENT
    
    if environment == 'production':
        base_url = 'https://api.safaricom.co.ke'
    else:
        base_url = 'https://sandbox.safaricom.co.ke'
    
    credentials = base64.b64encode(f'{consumer_key}:{consumer_secret}'.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {credentials}'
    }
    
    response = requests.get(
        f'{base_url}/oauth/v1/generate?grant_type=client_credentials',
        headers=headers,
        timeout=30
    )
    
    response.raise_for_status()
    return response.json()['access_token']

def generate_password():
    shortcode = settings.MPESA_SHORTCODE
    passkey = settings.MPESA_PASSKEY
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    
    data = f'{shortcode}{passkey}{timestamp}'
    password = base64.b64encode(data.encode()).decode()
    
    return password, timestamp

def initiate_stk_push(phone_number, amount, idempotency_key, account_reference='THECIRCLE', transaction_desc='Contribution Payment'):
    if not validate_idempotency_key(idempotency_key):
        return {'errorMessage': 'Duplicate transaction detected', 'ResponseCode': '99'}
    
    try:
        access_token = get_access_token()
        password, timestamp = generate_password()
        
        shortcode = settings.MPESA_SHORTCODE
        environment = settings.MPESA_ENVIRONMENT
        
        if environment == 'production':
            base_url = 'https://api.safaricom.co.ke'
            callback_url = 'https://your-domain.com/payments/callback/'
        else:
            base_url = 'https://sandbox.safaricom.co.ke'
            callback_url = 'https://your-domain.com/payments/callback/'
        
        phone = format_phone_number(phone_number)
        
        payload = {
            'BusinessShortCode': shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': int(amount),
            'PartyA': phone,
            'PartyB': shortcode,
            'PhoneNumber': phone,
            'CallBackURL': callback_url,
            'AccountReference': account_reference[:50],
            'TransactionDesc': transaction_desc[:255]
        }
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            f'{base_url}/mpesa/stkpush/v1/processrequest',
            json=payload,
            headers=headers,
            timeout=30
        )
        
        response_data = response.json()
        
        StkPushLog.objects.create(
            merchant_request_id=response_data.get('MerchantRequestID', ''),
            checkout_request_id=response_data.get('CheckoutRequestID', ''),
            phone_number=phone,
            amount=Decimal(str(amount)),
            account_reference=account_reference,
            transaction_desc=transaction_desc,
            response_code=response_data.get('ResponseCode'),
            response_description=response_data.get('ResponseDescription'),
            customer_message=response_data.get('CustomerMessage')
        )
        
        if response_data.get('ResponseCode') == '0':
            mark_idempotency_key_used(idempotency_key)
        
        return response_data
        
    except requests.exceptions.RequestException as e:
        return {'errorMessage': str(e), 'ResponseCode': '99'}

def query_transaction_status(checkout_request_id):
    try:
        access_token = get_access_token()
        password, timestamp = generate_password()
        
        shortcode = settings.MPESA_SHORTCODE
        environment = settings.MPESA_ENVIRONMENT
        
        if environment == 'production':
            base_url = 'https://api.safaricom.co.ke'
        else:
            base_url = 'https://sandbox.safaricom.co.ke'
        
        payload = {
            'BusinessShortCode': shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'CheckoutRequestID': checkout_request_id
        }
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            f'{base_url}/mpesa/stkpushquery/v1/query',
            json=payload,
            headers=headers,
            timeout=30
        )
        
        return response.json()
        
    except requests.exceptions.RequestException as e:
        return {'ResultCode': '99', 'ResultDesc': str(e)}

def format_phone_number(phone):
    phone = phone.strip().replace(' ', '').replace('-', '')
    
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    elif phone.startswith('+'):
        phone = phone[1:]
    elif not phone.startswith('254'):
        phone = '254' + phone
    
    return phone

def validate_idempotency_key(key):
    try:
        key_record, created = IdempotencyKey.objects.get_or_create(
            key=key,
            defaults={
                'transaction_type': 'stk_push',
                'amount': Decimal('0')
            }
        )
        
        if not created and key_record.used:
            return False
        
        return True
        
    except Exception:
        return False

def mark_idempotency_key_used(key):
    IdempotencyKey.objects.filter(key=key).update(used=True, used_at=timezone.now())

def verify_callback_signature(request_body, signature):
    expected_signature = hmac.new(
        settings.MPESA_PASSKEY.encode(),
        request_body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)

def process_callback(callback_data):
    checkout_request_id = callback_data.get('Body', {}).get('stkCallback', {}).get('CheckoutRequestID')
    result_code = callback_data.get('Body', {}).get('stkCallback', {}).get('ResultCode')
    result_desc = callback_data.get('Body', {}).get('stkCallback', {}).get('ResultDesc')
    
    callback_metadata = callback_data.get('Body', {}).get('stkCallback', {}).get('CallbackMetadata', {}).get('Item', [])
    
    mpesa_receipt_number = None
    transaction_date = None
    phone_number = None
    amount = None
    
    for item in callback_metadata:
        name = item.get('Name')
        value = item.get('Value')
        
        if name == 'MpesaReceiptNumber':
            mpesa_receipt_number = value
        elif name == 'TransactionDate':
            transaction_date = str(value)
        elif name == 'PhoneNumber':
            phone_number = str(value)
        elif name == 'Amount':
            amount = value
    
    try:
        log = StkPushLog.objects.get(checkout_request_id=checkout_request_id)
        log.callback_received = True
        log.callback_result_code = str(result_code)
        log.callback_result_desc = result_desc
        log.mpesa_receipt_number = mpesa_receipt_number
        log.raw_callback = callback_data
        
        if transaction_date:
            log.transaction_date = datetime.strptime(transaction_date, '%Y%m%d%H%M%S')
        
        log.save()
        
        return {
            'success': result_code == 0,
            'checkout_request_id': checkout_request_id,
            'mpesa_receipt_number': mpesa_receipt_number,
            'amount': amount,
            'phone_number': phone_number
        }
        
    except StkPushLog.DoesNotExist:
        return {'success': False, 'error': 'Transaction not found'}