import logging
import psycopg2
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from googletrans import Translator
from datetime import datetime

# Log konfiguratsiyasi
logging.basicConfig(
    filename='bot_loglari.log', 
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

# Ma'lumotlar bazasini yaratish va bog'lanish
def create_database():
    conn = psycopg2.connect("dbname=translate_bot user=superuser password=temurbek003 host=localhost")
    conn.autocommit = True
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id SERIAL PRIMARY KEY,
            username VARCHAR(255),
            first_name VARCHAR(255),
            last_name VARCHAR(255),
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            chosen_language VARCHAR(10)
        )
    ''')
    conn.close()
    logging.info("Ma'lumotlar bazasi yaratildi yoki mavjud bo'lgan baza topildi.")

create_database()

# Botni sozlash
translator = Translator()
logging.info("Google Translator obyekti yaratildi.")
API_TOKEN = '7328973823:AAGd9uExTr0fURn06Hg3fEVEe9aY09DCJz4'
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
logging.info("Telegram bot sozlandi.")

def update_user(user_id, username, first_name, last_name, chosen_language=None):
    conn = psycopg2.connect("dbname=translate_bot user=superuser password=temurbek003 host=localhost")
    c = conn.cursor()
    c.execute('''
        INSERT INTO users (user_id, username, first_name, last_name, last_active, chosen_language)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE
        SET username = EXCLUDED.username,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            last_active = EXCLUDED.last_active,
            chosen_language = EXCLUDED.chosen_language
    ''', (user_id, username, first_name, last_name, datetime.now(), chosen_language))
    conn.commit()
    conn.close()
    logging.info(f"Foydalanuvchi ma'lumotlari yangilandi: ID - {user_id}, Tanlangan til - {chosen_language}")

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("O'zbekcha", callback_data='uz'),
        InlineKeyboardButton("Ruscha", callback_data='ru'),
        InlineKeyboardButton("Inglizcha", callback_data='en')
    )
    await message.reply("Salom! Qaysi tilda matn yubormoqchisiz? Iltimos, tilni tanlang:", reply_markup=keyboard)
    logging.info(f"Foydalanuvchiga til tanlash uchun tugmalar yuborildi: ID - {message.from_user.id}")

@dp.callback_query_handler(lambda c: c.data in ['uz', 'ru', 'en'])
async def process_language_choice(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    chosen_language = callback_query.data

    # Foydalanuvchi ma'lumotlarini saqlash
    update_user(user_id, callback_query.from_user.username, callback_query.from_user.first_name, callback_query.from_user.last_name, chosen_language)
    
    # Til tanlanganligini tasdiqlash
    await bot.answer_callback_query(callback_query.id)
    
    # Foydalanuvchiga matn yuborishni so'rash
    await bot.send_message(user_id, f"Tanlangan til: {chosen_language}. Iltimos, matn yoki so'z yuboring.")
    logging.info(f"Foydalanuvchi til tanladi: ID - {user_id}, Tanlangan til - {chosen_language}")

@dp.message_handler()
async def handle_translation(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip()

    # Foydalanuvchi ma'lumotlarini olish
    conn = psycopg2.connect("dbname=translate_bot user=superuser password=temurbek003 host=localhost")
    c = conn.cursor()
    c.execute('SELECT chosen_language FROM users WHERE user_id = %s', (user_id,))
    result = c.fetchone()
    conn.close()

    if not result:
        # Agar foydalanuvchi hali tilni tanlamagan bo'lsa
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("O'zbekcha", callback_data='uz'),
            InlineKeyboardButton("Ruscha", callback_data='ru'),
            InlineKeyboardButton("Inglizcha", callback_data='en')
        )
        await message.reply("Iltimos, avval tilni tanlang:", reply_markup=keyboard)
        logging.warning(f"Foydalanuvchi hali tilni tanlamagan: ID - {user_id}")
        return

    chosen_language = result[0]

    # Tarjima qilish
    translations = {}
    if chosen_language == 'uz':
        translations = {
            'en': translator.translate(text, dest='en').text,
            'ru': translator.translate(text, dest='ru').text
        }
    elif chosen_language == 'ru':
        translations = {
            'en': translator.translate(text, dest='en').text,
            'uz': translator.translate(text, dest='uz').text
        }
    elif chosen_language == 'en':
        translations = {
            'uz': translator.translate(text, dest='uz').text,
            'ru': translator.translate(text, dest='ru').text
        }
    
    logging.info(f"Tarjima qilingan matnlar: ID - {user_id}, Original matn - {text}, Tarjimalar - {translations}")

    # Tarjimalarni yuborish
    for lang, translated_text in translations.items():
        if lang == 'en':
            await message.reply(f"Inglizcha tarjima: {translated_text}")
        elif lang == 'uz':
            await message.reply(f"O'zbekcha tarjima: {translated_text}")
        elif lang == 'ru':
            await message.reply(f"Ruscha tarjima: {translated_text}")

    # Har bir javobga til tanlash tugmalarini yuborish
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("O'zbekcha", callback_data='uz'),
        InlineKeyboardButton("Ruscha", callback_data='ru'),
        InlineKeyboardButton("Inglizcha", callback_data='en')
    )
    await message.reply("Qaysi tilda matn yubormoqchisiz? Iltimos, tilni tanlang:", reply_markup=keyboard)
    logging.info(f"Foydalanuvchiga qayta til tanlash tugmalari yuborildi: ID - {user_id}")

if __name__ == '__main__':
    print("bot ishlayapti")
    logging.info("Bot ishga tushirilmoqda...")
    executor.start_polling(dp, skip_updates=True)
    logging.info("Bot ishga tushirildi.")
