import requests
import base64

API_URL = "http://localhost:8080"
API_KEY = "WeAreCofoundersBitch"
INSTANCE = "grafxBot"


def send_text(number, text):

    url = f"{API_URL}/message/sendText/{INSTANCE}"

    headers = {
        "apikey": API_KEY
    }

    payload = {
        "number": number,
        "text": text
    }

    requests.post(url, json=payload, headers=headers)


def send_image(number, path, caption):

    with open(path, "rb") as img:
        base64_image = base64.b64encode(img.read()).decode("utf-8")

    url = f"{API_URL}/message/sendMedia/{INSTANCE}"

    headers = {
        "apikey": API_KEY
    }

    payload = {
        "number": number,
        "mediatype": "image",
        "media": base64_image,
        "caption": caption
    }

    requests.post(url, json=payload, headers=headers)