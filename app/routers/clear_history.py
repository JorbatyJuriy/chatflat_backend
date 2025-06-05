from fastapi import APIRouter, HTTPException
import boto3
from app.config import settings
from boto3.dynamodb.conditions import Key

router = APIRouter(prefix="/messages", tags=["messages"])

dynamodb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
messages_table = dynamodb.Table(settings.DYNAMO_MESSAGES_TABLE)

@router.delete("/delete_by_user/{user_id}")
async def delete_messages_by_user(user_id: str):
    try:
        # 1. Знайти всі повідомлення користувача через GSI
        response = messages_table.query(
            IndexName="id_user-timestamp-index",  # Назва твого GSI
            KeyConditionExpression=Key("id_user").eq(user_id)
        )
        items = response.get("Items", [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Помилка при пошуку повідомлень: {e}")

    if not items:
        return {"status": "ok", "deleted": 0, "message": "Для цього користувача повідомлень не знайдено."}

    # 2. Видалити кожне повідомлення окремо (по id_message)
    deleted = 0
    errors = []
    for item in items:
        try:
            messages_table.delete_item(Key={"id_message": item["id_message"]})
            deleted += 1
        except Exception as e:
            errors.append(str(e))

    return {
        "status": "ok" if deleted == len(items) else "partial",
        "deleted": deleted,
        "failed": len(errors),
        "errors": errors if errors else None
    }