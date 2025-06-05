import traceback

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from datetime import datetime
from boto3.dynamodb.conditions import Key

from app.utils.auth import verify_token_and_get_user
from app.models.users import CognitoUser
from app.models.messages import MessagePayLoad, MessageTableItem, MessageTableList
from app.utils.chatbot import generate_bot_response
from app.config import settings as settings_cfg

import boto3
import uuid


router = APIRouter(
    prefix="/messages",
    tags=["messages"],
)

# Ініціалізуємо таблиці з DDB
dynamo_client = boto3.resource("dynamodb", region_name=settings_cfg.AWS_REGION)
messages_table = dynamo_client.Table(settings_cfg.DYNAMO_MESSAGES_TABLE)

# Отримання історії повідомлень з бази данних, та запаковка їх у список
@router.get("/", response_model=MessageTableList)
async def list_message(
        user: CognitoUser = Depends(verify_token_and_get_user),
        limit: int = Query(50, ge=1, le=100)
):
    print(f"📨 list_message called for user: {user.sub}, limit: {limit}")
    try:
        response = messages_table.query(
        IndexName = "id_user-timestamp-index",
        KeyConditionExpression = Key("id_user").eq(user.sub),
        ScanIndexForward=False,
        Limit=limit,
        )

        items = response.get("Items", [])
        messages = [MessageTableItem(**item) for item in items]

        return MessageTableList(messages=messages)

    except Exception as e:
        print("[SEND MESSAGE ERROR]")
        traceback.print_exc()  # <-- додай саме це
        raise HTTPException(status_code=500, detail=str(e))


# Метод надсилання повідомлення і отриманння відповіді від бота
@router.post("/")
async def send_message(
        message: MessagePayLoad,
        user: CognitoUser = Depends(verify_token_and_get_user),
):
    try:
        now = datetime.utcnow().isoformat()

        # Визначаємо конкретного користувача і саме його повідомлення
        user_msg = {
            "id_message": str(uuid.uuid4()),
            "id_user": user.sub,
            "content": message.content,
            "timestamp": now,
            "is_bot": False
        }

        messages_table.put_item(Item=user_msg)

        # Також визначаємо відповідь від моделі
        bot_response = await generate_bot_response(message.content, user.sub)
        bot_msg = {
            "id_message": str(uuid.uuid4()),
            "id_user": user.sub,
            "content": bot_response,
            "timestamp": datetime.utcnow().isoformat(),
            "is_bot": True
        }
        messages_table.put_item(Item=bot_msg)

        return {
            "user_message": user_msg,
            "bot_response": bot_msg
        }

    except Exception as e:
        print("[SEND MESSAGE ERROR]")
        traceback.print_exc()  # <-- додай саме це
        raise HTTPException(status_code=500, detail=str(e))


