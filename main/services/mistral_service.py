# main/services/mistral_service.py
import requests
import json
from django.conf import settings


class MistralService:
    """Сервис для работы с Mistral AI API"""

    def __init__(self):
        self.api_key = settings.MISTRAL_API_KEY
        self.api_url = "https://api.mistral.ai/v1/chat/completions"
        self.model = "mistral-tiny"

    def get_response(self, user_message, conversation_history=None):
        if conversation_history is None:
            conversation_history = [
                {
                    "role": "system",
                    "content": "Ты — дружелюбный AI-репетитор татарского языка. Твоя задача помогать пользователям изучать татарский язык. Отвечай на русском или татарском языке в зависимости от вопроса пользователя. Если пользователь пишет на татарском, отвечай на татарском. Если на русском — отвечай на русском. Ты должен быть терпеливым, объяснять грамматику, помогать с произношением, давать примеры предложений. Будь вежливым и мотивирующим. Используй приветствия на татарском: 'Исәнмесез!', 'Рәхим итегез!' и т.д. Не используй markdown, только обычный текст."
                }
            ]

        conversation_history.append({
            "role": "user",
            "content": user_message
        })

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        data = {
            "model": self.model,
            "messages": conversation_history,
            "temperature": 0.7,
            "max_tokens": 500
        }

        try:
            response = requests.post(self.api_url, json=data, headers=headers, timeout=30)

            if response.status_code == 200:
                ai_response = response.json()["choices"][0]["message"]["content"]
                return {
                    "success": True,
                    "response": ai_response,
                    "history": conversation_history + [{"role": "assistant", "content": ai_response}]
                }
            else:
                return {
                    "success": False,
                    "error": f"API error: {response.status_code} - {response.text}"
                }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Превышено время ожидания ответа от AI"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }