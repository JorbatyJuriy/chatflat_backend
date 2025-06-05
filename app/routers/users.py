from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from app.utils.auth import verify_token_and_get_user, get_secret_hash
from app.models.users import CognitoUser
from app.config import settings as settings_cognito

import boto3
from botocore.exceptions import ClientError
import datetime

dynamo_client = boto3.resource('dynamodb', region_name=settings_cognito.AWS_REGION)
dynamo_table = dynamo_client.Table(settings_cognito.DYNAMO_USERS_TABLE)
cognito_client = boto3.client('cognito-idp', region_name=settings_cognito.AWS_REGION)

router = APIRouter(
    prefix="/users",
    tags=["users"],
)

# Модель запиту для логіну/реєстрації
class AuthPayload(BaseModel):
    email: EmailStr
    password: str


# Реєстрація користувача в Cognito
@router.post("/register", status_code=201)
async def register_user(payload: AuthPayload):
    try:
        cognito_client.admin_create_user(
            UserPoolId=settings_cognito.COGNITO_USER_POOL_ID,
            Username=payload.email,
            UserAttributes=[
                {"Name": "email", "Value": payload.email},
                {"Name": "email_verified", "Value": "true"},
            ],
            TemporaryPassword=payload.password,
            MessageAction="SUPPRESS",
        )

        cognito_client.admin_set_user_password(
            UserPoolId=settings_cognito.COGNITO_USER_POOL_ID,
            Username=payload.email,
            Password=payload.password,
            Permanent=True
        )

        return {"message": "User registered successfully"}

    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "UsernameExistsException":
            raise HTTPException(status_code=400, detail="Email already registered")
        else:
            raise HTTPException(status_code=500, detail="Cognito error during registration")


def store_user_in_dynamo(access_token: str):
    try:
        response = cognito_client.get_user(AccessToken=access_token)
        user_attrs = {attr["Name"]: attr["Value"] for attr in response["UserAttributes"]}
        sub = user_attrs["sub"]
        email = user_attrs["email"]

        new_user = {
            "id_user": sub,
            "email": email,
            "registered_at": datetime.datetime.utcnow().isoformat(),
        }

        dynamo_table.put_item(Item=new_user)  # перезапише, якщо вже є

    except ClientError as e:
        print("Dynamo store error:", e.response)
        raise HTTPException(status_code=500, detail="Failed to store user in DB")

# Логін користувача, отримання токенів і збереження у cookie
@router.post("/login", status_code=200)
async def login_user(payload: AuthPayload):
    try:
        secret_hash = get_secret_hash(
            payload.email,
            settings_cognito.COGNITO_APP_CLIENT_ID,
            settings_cognito.COGNITO_APP_CLIENT_SECRET
        )

        response = cognito_client.initiate_auth(
            ClientId=settings_cognito.COGNITO_APP_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": payload.email,
                "PASSWORD": payload.password,
                "SECRET_HASH": secret_hash
            },
        )

        tokens = response["AuthenticationResult"]

        # Повертаємо відповідь + зберігаємо токени в cookie
        res = JSONResponse(content={"message": "Login successful", "token": tokens["AccessToken"]})

        res.set_cookie(
            key="access_token",
            value=tokens["AccessToken"],
            httponly=True,
            secure=False,  # У продакшені змінити на True
            samesite="Lax",
            max_age=tokens["ExpiresIn"],
        )

        res.set_cookie(
            key="refresh_token",
            value=tokens["RefreshToken"],
            httponly=True,
            secure=False,
            samesite="Lax",
            max_age=30 * 24 * 60 * 60,  # 30 днів
        )

        store_user_in_dynamo(tokens["AccessToken"])

        return res

    except ClientError as e:
        print("FULL COGNITO ERROR:", e.response)  # ← покажемо повну відповідь Cognito
        code = e.response["Error"]["Code"]
        message = e.response["Error"].get("Message", "No message")
        raise HTTPException(status_code=500, detail=f"Cognito login error: {code} – {message}")



# Отримання поточного користувача
@router.get("/me", status_code=200)
async def get_current_user(user: CognitoUser = Depends(verify_token_and_get_user)):
    return {
        "user_id": user.sub,
        "email": user.email,
        "username": user.username,
    }


# Ініціалізація користувача в DynamoDB
@router.post("/init", status_code=201)
async def init_user(user: CognitoUser = Depends(verify_token_and_get_user)):
    try:
        response = dynamo_table.get_item(Key={"id_user": user.sub})
        if "Item" in response:
            return {"message": "User already exists"}

        new_user = {
            "id_user": user.sub,
            "email": user.email,
            "registered_at": datetime.datetime.utcnow().isoformat(),
        }

        dynamo_table.put_item(Item=new_user)
        return {"message": "User created"}

    except ClientError:
        raise HTTPException(status_code=500, detail="DynamoDB error")


# Логаут: видалення токенів з cookie
@router.post("/logout", status_code=200)
async def logout_user(request: Request):
    res = JSONResponse(content={"message": "User logged out"})
    res.delete_cookie(key="access_token", path="/")
    res.delete_cookie(key="refresh_token", path="/")
    return res