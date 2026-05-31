import requests

url = "https://api.mistral.ai/v1/chat/completions"
headers = {
    "Authorization": "Bearer g2n5170X7VpcRrFrTKQOj3SNAB3Yhjz7",
    "Content-Type": "application/json"
}
data = {
    "model": "mistral-tiny",
    "messages": [{"role": "user", "content": "Скажи Привет"}],
    "max_tokens": 20
}

try:
    response = requests.post(url, json=data, headers=headers, timeout=10)
    print("Статус:", response.status_code)
    print("Ответ:", response.json())
except Exception as e:
    print("Ошибка:", e)