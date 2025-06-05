import logging
from decimal import Decimal

import boto3
import json
from openai import OpenAI
from boto3.dynamodb.conditions import Key
from app.config import settings

logger = logging.getLogger(__name__)

with open("app/prompts/chat_context.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

client = OpenAI(api_key=settings.OPENAI_API_KEY)
dynamodb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
messages_table = dynamodb.Table(settings.DYNAMO_MESSAGES_TABLE)
apartments_table = dynamodb.Table(settings.DYNAMO_PROPERTIES_TABLE)

def load_user_messages_internal(user_id: str, limit: int = 10):
    try:
        response = messages_table.query(
            IndexName="id_user-timestamp-index",
            KeyConditionExpression=Key("id_user").eq(user_id),
            ScanIndexForward=False,
            Limit=limit,
        )
        items = response.get("Items", [])
        items.reverse()
        logger.info(f" Завантажено історій: {len(items)}")
        return items
    except Exception as e:
        logger.error(f" DynamoDB помилка (messages): {e}")
        return []

def load_all_apartments() -> list[dict]:
    try:
        response = apartments_table.scan()
        items = response.get("Items", [])
        logger.info(f" Завантажено квартир: {len(items)}")
        return items
    except Exception as e:
        logger.error(f" DynamoDB помилка (apartments): {e}")
        return []


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)  # або int(obj) якщо всі числа цілі
        return super().default(obj)


#####################################################################################


async def generate_bot_response(message: str, user_id: str) -> str:
    try:
        history = load_user_messages_internal(user_id=user_id)
        apartments = load_all_apartments()
        # Оформляємо у формат {"apartments": [...]}
        apartments_json = json.dumps(
            {"apartments": apartments},
            ensure_ascii=False,
            cls=DecimalEncoder
        )
        chat_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in history:
            role = "assistant" if msg.get("is_bot") else "user"
            chat_messages.append({"role": role, "content": msg.get("content")})

        chat_messages.append({"role": "user", "content": message})

        # Окремий system message із JSON-масивом квартир
        chat_messages.append({
            "role": "system",
            "content": apartments_json
        })

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=chat_messages,
            temperature=0.3,
        )

        result = response.choices[0].message.content
        logger.info("AIBot відповів успішно")
        return result

    except Exception as e:
        logger.error(f"[AIBOT ERROR] {e}")
        raise