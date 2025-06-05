from fastapi import APIRouter, HTTPException
import boto3
from uuid import uuid4
from datetime import datetime
from app.config import settings

router = APIRouter(prefix="/apartments", tags=["apartments"])

dynamodb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
apartments_table = dynamodb.Table(settings.DYNAMO_PROPERTIES_TABLE)

# --- Масив апартаментів, який можна редагувати окремо ---
apartments_data = [
    {
        "property_id": str(uuid4()),
        "title": "Сучасна студія біля метро",
        "description": "Стильна та затишна квартира-студія після ремонту, з усією необхідною технікою. Поруч метро, магазини, кафе.",
        "district": "Академмістечко",
        "address": "пр-т Перемоги, 110",
        "price_uah": 14500,
        "rooms": 1,
        "area_sqm": 29,
        "photo_url": "https://chatflatbucket.s3.eu-north-1.amazonaws.com/property_images/app1.jpg"
    },
    {
        "property_id": str(uuid4()),
        "title": "Трикімнатна з видом на Дніпро",
        "description": "Велика, простора квартира для сім’ї. Є балкон, панорамні вікна, роздільний санвузол.",
        "district": "Позняки",
        "address": "вул. Срібнокільська, 3б",
        "price_uah": 25500,
        "rooms": 3,
        "area_sqm": 82,
        "photo_url": "https://chatflatbucket.s3.eu-north-1.amazonaws.com/property_images/app2.jpg"
    },
    {
        "property_id": str(uuid4()),
        "title": "Лофт у центрі Києва",
        "description": "Світла однокімнатна квартира з дизайнерським ремонтом у стилі лофт. Поруч метро та парки.",
        "district": "Лук’янівка",
        "address": "вул. Полтавська, 9",
        "price_uah": 18000,
        "rooms": 1,
        "area_sqm": 36,
        "photo_url": "https://chatflatbucket.s3.eu-north-1.amazonaws.com/property_images/app3.jpg"
    },
    {
        "property_id": str(uuid4()),
        "title": "Сімейна квартира біля парку",
        "description": "Тиха трикімнатна квартира поруч з парком, свіжий ремонт, меблі та техніка, просторий коридор.",
        "district": "Березняки",
        "address": "вул. Березнева, 7",
        "price_uah": 21000,
        "rooms": 3,
        "area_sqm": 76,
        "photo_url": "https://chatflatbucket.s3.eu-north-1.amazonaws.com/property_images/app4.jpg"
    },
    {
        "property_id": str(uuid4()),
        "title": "Двокімнатна в новобудові",
        "description": "Квартира у сучасному житловому комплексі з підземним паркінгом. Охорона, консьєрж.",
        "district": "Солом’янка",
        "address": "вул. Преображенська, 11",
        "price_uah": 22000,
        "rooms": 2,
        "area_sqm": 59,
        "photo_url": "https://chatflatbucket.s3.eu-north-1.amazonaws.com/property_images/app13.jpg"
    },
    {
        "property_id": str(uuid4()),
        "title": "Елітна квартира на Печерську",
        "description": "Квартира преміум-класу з великою кухнею-студією, власною гардеробною та видом на місто.",
        "district": "Печерськ",
        "address": "бул. Лесі Українки, 26",
        "price_uah": 50000,
        "rooms": 4,
        "area_sqm": 110,
        "photo_url": "https://chatflatbucket.s3.eu-north-1.amazonaws.com/property_images/app6.jpg"
    },
    {
        "property_id": str(uuid4()),
        "title": "Затишна квартира для студента",
        "description": "Охайна та світла однокімнатна квартира. Всі зручності для одного мешканця або пари.",
        "district": "Дарниця",
        "address": "вул. Харківське шосе, 56",
        "price_uah": 11500,
        "rooms": 1,
        "area_sqm": 33,
        "photo_url": "https://chatflatbucket.s3.eu-north-1.amazonaws.com/property_images/app7.jpg"
    },
    {
        "property_id": str(uuid4()),
        "title": "Двокімнатна з панорамними вікнами",
        "description": "Велика кухня, роздільні кімнати, просторий балкон з панорамним видом на місто. Меблі, техніка.",
        "district": "Оболонь",
        "address": "пр-т Героїв Сталінграда, 25",
        "price_uah": 17500,
        "rooms": 2,
        "area_sqm": 61,
        "photo_url": "https://chatflatbucket.s3.eu-north-1.amazonaws.com/property_images/app8.jpg"
    },
    {
        "property_id": str(uuid4()),
        "title": "Студія на Осокорках",
        "description": "Компактна квартира-студія для молодої пари. Новий ремонт, велика ванна кімната, тихий двір.",
        "district": "Осокорки",
        "address": "вул. Єлизавети Чавдар, 15",
        "price_uah": 12500,
        "rooms": 1,
        "area_sqm": 27,
        "photo_url": "https://chatflatbucket.s3.eu-north-1.amazonaws.com/property_images/app9.jpg"
    },
    {
        "property_id": str(uuid4()),
        "title": "Простора квартира з балконом",
        "description": "Двокімнатна квартира з балконом і великими вікнами. Поруч школи, магазини та метро.",
        "district": "Троєщина",
        "address": "вул. Маяковського, 24",
        "price_uah": 13500,
        "rooms": 2,
        "area_sqm": 48,
        "photo_url": "https://chatflatbucket.s3.eu-north-1.amazonaws.com/property_images/app10.jpg"
    },
    {
    "property_id": str(uuid4()),
    "title": "Сімейна квартира біля озера",
    "description": "Ідеальний вибір для сім’ї: поруч озеро, затишний двір, дитячий майданчик. Квартира мебльована, готова до заселення.",
    "district": "Позняки",
    "address": "вул. Здолбунівська, 8",
    "price_uah": 19500,
    "rooms": 3,
    "area_sqm": 74,
    "photo_url": "https://chatflatbucket.s3.eu-north-1.amazonaws.com/property_images/app11.jpg"
},
{
    "property_id": str(uuid4()),
    "title": "Комфортна студія з новим ремонтом",
    "description": "Сучасна студія в світлих тонах, нові меблі, є все необхідне для комфортного проживання. Метро та ТРЦ у пішій доступності.",
    "district": "Осокорки",
    "address": "вул. Срібнокільська, 1",
    "price_uah": 14200,
    "rooms": 1,
    "area_sqm": 28,
    "photo_url": "https://chatflatbucket.s3.eu-north-1.amazonaws.com/property_images/app12.jpg"
},
]

# --- Endpoint: ініціалізація/додавання масиву квартир у БД ---
@router.post("/init")
async def init_apartments():
    added = 0
    try:
        for apt in apartments_data:
            apartments_table.put_item(Item=apt)
            added += 1
        return {"status": "ok", "added": added}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Помилка при додаванні квартир: {e}")

# --- Endpoint: видалення всіх квартир із таблиці ---
@router.delete("/delete_all")
async def delete_all_apartments():
    try:
        response = apartments_table.scan()
        items = response.get("Items", [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Помилка при читанні квартир: {e}")

    if not items:
        return {"status": "ok", "deleted": 0, "message": "Квартир для видалення не знайдено."}

    deleted = 0
    errors = []
    for item in items:
        try:
            apartments_table.delete_item(Key={"property_id": item["property_id"]})
            deleted += 1
        except Exception as e:
            errors.append(f"{item.get('property_id')}: {str(e)}")
    return {
        "status": "ok" if deleted == len(items) else "partial",
        "deleted": deleted,
        "failed": len(errors),
        "errors": errors if errors else None
    }

# --- Endpoint: кількість квартир у таблиці ---
@router.get("/count")
async def count_apartments():
    try:
        response = apartments_table.scan(Select='COUNT')
        count = response.get("Count", 0)
        return {"count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Помилка при підрахунку: {e}")

@router.get("/list")
async def list_apartments():
    try:
        response = apartments_table.scan()
        items = response.get("Items", [])
        return {"apartments": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Помилка при читанні квартир: {e}")