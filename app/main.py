import logging
from sys import prefix

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings as settings_CORS
from app.routers import users, messages, health, appartments, clear_history


#Налаштування процедури входу на сайт
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug.log'),]
)

logger = logging.getLogger("app.main")

# Функція життєвого цикклу застосунку (startup/shutdown)
async def lifespan(app: FastAPI):
    logger.info("ChatFlat запуск API!")
    yield
    logger.info("ChatFlat завершення роботи")

# Ініціалізація FastAPI
app = FastAPI(title="ChatFlat API", lifespan=lifespan)

# Налаштування CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[  "http://localhost:5173",
        "https://chatflat-frontend-ckwlqxbwc-jorbatys-projects.vercel.app",
        # Переконайтеся, що це точний URL вашого основного деплойменту Vercel.
        # Можливо, потрібно також додати домен без "jorbatys-projects" якщо він є основним:
        "https://chatflat-frontend.vercel.app",
        "https://chatflat-frontend-jorbatys-projects.vercel.app", ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Підключення всіх роутерів
app.include_router(health.router)
app.include_router(users.router)
app.include_router(messages.router)
app.include_router(clear_history.router)
app.include_router(appartments.router)
