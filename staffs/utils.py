from django.core.mail import send_mail
import requests
from django.conf import settings

def send_email_notification(subject, message, recipient_email):
    if not recipient_email:
        return False

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [recipient_email],
        fail_silently=False,
    )
    return True

import requests
from django.conf import settings


def send_sms_notification(phone_number, message):
    if not phone_number:
        return False

    url = "https://app.text.lk/api/v3/sms/send"

    headers = {
        "Authorization": f"Bearer {settings.TEXT_LK_API_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    payload = {
        "recipient": phone_number,
        "sender_id": settings.TEXT_LK_SENDER_ID,
        "type": "plain",
        "message": message,
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)

        print("TEXT.LK STATUS:", response.status_code)
        print("TEXT.LK RESPONSE:", response.text)

        if response.status_code not in [200, 201]:
            return False

        data = response.json()

        return data.get("status") == "success"

    except Exception as e:
        print("SMS ERROR:", str(e))
        return False