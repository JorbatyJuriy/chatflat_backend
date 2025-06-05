from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Ключ до OpenAI
    OPENAI_API_KEY: str

    # AWS параметри для запуску проекту на локальному сервері
    AWS_REGION: str # Це значення буде взято з .env (eu-north-1)
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str

    # Дані для Cognito авторизації
    COGNITO_USER_POOL_ID: str
    COGNITO_APP_CLIENT_ID: str
    COGNITO_APP_CLIENT_SECRET: str

    # Додаткові змінні CORS та DynamoDB, та ENV
    DYNAMO_MESSAGES_TABLE: str
    DYNAMO_PROPERTIES_TABLE: str
    DYNAMO_USERS_TABLE: str
    CORS_ALLOWED_DOMAIN: str
    ENV: str = "develop"


    # Формування URL та JWKS (ключі для перевірки токенів)
    @property
    def COGNITO_KEYS_URL(self) -> str:
        # ВИПРАВЛЕНО: Використовуємо self.AWS_REGION з .env
        return f"https://cognito-idp.{self.AWS_REGION}.amazonaws.com/{self.COGNITO_USER_POOL_ID}/.well-known/jwks.json"

    @property
    def COGNITO_ISSUER(self) -> str:
        # ВИПРАВЛЕНО: Використовуємо self.AWS_REGION з .env
        return f"https://cognito-idp.{self.AWS_REGION}.amazonaws.com/{self.COGNITO_USER_POOL_ID}"

    # Налаштування файлу з якого беремо інформацію
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()