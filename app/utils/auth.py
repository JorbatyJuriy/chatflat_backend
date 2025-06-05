import base64
import datetime
import json
import urllib.request
import hmac
import hashlib

from functools import lru_cache
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError
from fastapi import Depends, HTTPException, Request, status
from jose.constants import ALGORITHMS

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from app.config import settings as settings_cognito
from app.models.users import CognitoUser

ALGORITHM = "RS256"


@lru_cache()
def get_public_keys():
    """
    Завантажує та кешує публічні ключі Cognito для верифікації JWT.
    Використовує lru_cache для уникнення повторних запитів до URL.
    """
    try:
        keys_url = settings_cognito.COGNITO_KEYS_URL
        print(f"Attempting to fetch public keys from: {keys_url}")
        with urllib.request.urlopen(keys_url) as f:
            response = f.read()
        keys = json.loads(response.decode("utf-8"))["keys"]
        print(f"Successfully fetched {len(keys)} public keys.")
        return keys
    except Exception as e:
        print(f"ERROR: Failed to fetch public keys from {settings_cognito.COGNITO_KEYS_URL}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch public keys: {str(e)}")


def get_token_from_request(request: Request) -> str:
    """
    Витягує токен з заголовка 'Authorization' або з HTTP-only cookie.
    Пріоритет надається заголовку 'Authorization'.
    """
    # 1. Спробувати отримати токен з заголовка Authorization (Bearer Token)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        parts = auth_header.split(" ")
        if len(parts) == 2:
            token = parts[1]
            print(f"DEBUG: Token found in Authorization header. Starts with: {token[:15]}...")
            return token
        else:
            print("DEBUG: Authorization header malformed (Bearer token without value).")

    # 2. Спробувати отримати токен з cookies
    cookie_token = request.cookies.get("access_token")
    if cookie_token: # Ми вже не перевіряємо довжину частин, оскільки це може бути внутрішньою деталю токена
        print(f"DEBUG: Token found in cookies. Starts with: {cookie_token[:15]}...")
        return cookie_token

    # 3. Якщо не знайдено токен - викликати помилку
    print("WARNING: Token not found in Authorization header or cookies.")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication token required (not found in Authorization header or cookies)"
    )

def get_kid(token: str) -> str:
    """
    Витягує 'kid' (key ID) з неперевіреного заголовка JWT токена.
    """
    try:
        headers = jwt.get_unverified_header(token)
        kid = headers.get("kid")
        if not kid:
            print("ERROR: Token header missing 'kid'.")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing kid header")
        print(f"DEBUG: Extracted KID: {kid}")
        return kid
    except JWTError as e:
        print(f"ERROR: Invalid token header format: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token header format: {str(e)}")

def get_key_for_kid(kid: str):
    """
    Знаходить відповідний публічний ключ за 'kid'.
    """
    keys = get_public_keys() # Ця функція кешується
    for key in keys:
        if key.get("kid") == kid:
            print(f"DEBUG: Found public key for KID: {kid}")
            return key
    print(f"ERROR: Public key not found for token KID: {kid}")
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Public key not found for token kid")

def construct_rsa_public_key(jwk_dict):
    """
    Будує RSA публічний ключ з JWK (JSON Web Key) словника.
    """
    try:
        e_str = jwk_dict['e']
        n_str = jwk_dict['n']

        # Функція для додавання padding до base64url рядка
        def fix_padding(b64string):
            return b64string + '=' * ((4 - len(b64string) % 4) % 4)

        e = int.from_bytes(base64.urlsafe_b64decode(fix_padding(e_str)), 'big')
        n = int.from_bytes(base64.urlsafe_b64decode(fix_padding(n_str)), 'big')
        public_key = rsa.RSAPublicNumbers(e, n).public_key(default_backend())
        print("DEBUG: RSA public key constructed successfully.")
        return public_key
    except Exception as e:
        print(f"ERROR: Failed to construct RSA public key from JWK: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Failed to construct RSA public key: {str(e)}")

async def verify_token_and_get_user(request: Request) -> CognitoUser:
    """
    Верифікує JWT токен Cognito та повертає об'єкт CognitoUser.
    Ця функція використовується як залежність FastAPI.
    """
    print("\n--- Starting Token Verification ---")
    token = get_token_from_request(request)
    print(f"DEBUG: Token snippet: {token[:20]}...")

    try:
        kid = get_kid(token)
        key_dict = get_key_for_kid(kid)

        public_key = construct_rsa_public_key(key_dict)
        pem_key = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        print("DEBUG: Public key PEM generated.")

    except HTTPException: # Продовжуємо прокидати HTTPException, якщо вони були згенеровані раніше в ланцюжку
        print("ERROR: An HTTPException occurred during key retrieval/construction.")
        raise
    except Exception as e: # Загальний випадок, якщо щось пішло не так при роботі з ключами
        print(f"ERROR: Unexpected error during key processing: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Authentication error: {str(e)}")

    try:
        # Безпосереднє декодування та валідація токена
        payload = jwt.decode(
            token,
            key=pem_key,
            algorithms=[ALGORITHM],
            audience=settings_cognito.COGNITO_APP_CLIENT_ID,
            issuer=f"https://cognito-idp.{settings_cognito.AWS_REGION}.amazonaws.com/{settings_cognito.COGNITO_USER_POOL_ID}",
        )
        print(f"DEBUG: Token decoded successfully. Payload keys: {list(payload.keys())}")

        # Додаткова інформація про час дії токена для відладки
        current_time_utc = int(datetime.datetime.utcnow().timestamp())
        token_exp = payload.get('exp')
        print(f"DEBUG: Token 'exp' (expiration): {token_exp} (UTC). Current time: {current_time_utc} (UTC).")
        if token_exp and current_time_utc > token_exp:
            print("WARNING: Token appears to be expired based on current UTC time.")
            # Хоча jose.jwt.decode мав би це обробити, це для додаткової відладки.
            # Якщо ви досі отримуєте "Token expired" і цей вивід є, то проблема в налаштуваннях часу.

    except ExpiredSignatureError:
        print("ERROR: Token expired. Check token validity period.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except JWTClaimsError as e:
        print(f"ERROR: Invalid JWT claims: {str(e)}. "
              f"Expected Audience: {settings_cognito.COGNITO_APP_CLIENT_ID}, "
              f"Expected Issuer: {f'https://cognito-idp.{settings_cognito.AWS_REGION}.amazonaws.com/{settings_cognito.COGNITO_USER_POOL_ID}'}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token claims: {str(e)}")
    except JWTError as e:
        print(f"ERROR: General JWT error during decode: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"JWT validation error: {str(e)}")
    except Exception as e: # Загальний випадок, якщо щось непередбачене сталося при декодуванні
        print(f"ERROR: Unexpected error during token decoding: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {str(e)}")

    # Перевірка наявності мінімальних необхідних полів у payload
    required_fields = ["sub", "username", "token_use", "exp", "iat"]
    missing = [field for field in required_fields if field not in payload]
    if missing:
        print(f"ERROR: Token payload missing required fields: {', '.join(missing)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token payload missing required fields: {', '.join(missing)}"
        )

    print("DEBUG: Token verification successful. Returning CognitoUser.")
    print("--- Token Verification Finished ---")
    # Повертаємо користувача, конвертуючи payload у модель CognitoUser
    return CognitoUser(**payload)


def get_secret_hash(username: str, client_id: str, client_secret: str) -> str:
    """
    Генерує секретний хеш для Cognito, необхідний для деяких операцій (наприклад, USER_PASSWORD_AUTH).
    """
    message = username + client_id
    dig = hmac.new(
        key=client_secret.encode("utf-8"),
        msg=message.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(dig).decode()