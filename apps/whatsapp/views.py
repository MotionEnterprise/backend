import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .services import send_text, send_image


@csrf_exempt
def webhook(request):

    if request.method == "GET":
        return JsonResponse({"status": "ok"})

    if not request.body:
        return JsonResponse({"status": "ok"})

    data = json.loads(request.body)

    try:

        key = data.get("data", {}).get("key", {})
        from_me = key.get("fromMe", False)

        # ❗ Ignore bot's own messages
        if from_me:
            return JsonResponse({"status": "ignored bot message"})

        number = key.get("remoteJid", "").split("@")[0]

        msg = data.get("data", {}).get("message", {})

        message = ""

        if "conversation" in msg:
            message = msg["conversation"]

        elif "extendedTextMessage" in msg:
            message = msg["extendedTextMessage"].get("text", "")

        message = message.lower().strip()

        print("User:", number)
        print("Message:", message)

        # ===== BOT LOGIC =====

        if message in ["hi", "hello", "menu"]:

            send_text(
                number,
                "Welcome to Jewellery Bot 💎\n\n1 Gold Ring\n2 Diamond Ring"
            )

        elif message == "1":

            send_image(
                number,
                "apps/whatsapp/images/gold.jpg",
                "Gold Ring Price ₹25000"
            )

        elif message == "2":

            send_image(
                number,
                "bot/images/diamond.jpg",
                "Diamond Ring Price ₹45000"
            )

        else:

            send_text(
                number,
                "Type 'hi' to see menu"
            )

    except Exception as e:
        print("Webhook Error:", e)

    return JsonResponse({"status": "ok"})