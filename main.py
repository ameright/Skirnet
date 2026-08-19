from dotenv import load_dotenv
load_dotenv()
from os import getenv
BOT_TOKEN = getenv("BOT_TOKEN")

import asyncio
import logging
logging.basicConfig(level=logging.INFO)

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

import json
from datetime import datetime

mer_id = 5072493085
bot = Bot(BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def command_start(message: Message):
    with open("data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    user_id = str(message.from_user.id)
    if user_id in data:
        data[user_id]["username"] = message.from_user.username
    else:
        data[user_id] = {
            "username": message.from_user.username,
            "expire": None,
            "notified": None
        }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    text = (
        "👋 Привет!\n\n"
        "Я слежу за оплатой твоего VPN от @ameright\n"
        "Напомню за 3 дня и за 1 день до срока.\n\n"
        "📌 /check - узнать, сколько дней осталось до оплаты."
    )
    await message.answer(text)
    try:
        await bot.send_message(chat_id=mer_id, text=f"@{message.from_user.username} включил бота.")
    except Exception as e:
        logging.warning(f"Не удалось уведомить админа: {e}")

async def get_status_message(days_left: int, expire_date: str) -> str:
    status = f"Осталось {days_left} д."
    if days_left < 0:
        emoji = "⚠️"
        status = f"Оплата просрочена на {-days_left} д."
    elif days_left <= 1:
        emoji = "🔴"
    elif days_left <= 3:
        emoji = "🟡"
    else:
        emoji = "🟢"

    return (
        f"{emoji} {status}\n"
        f"📅 Дата оплаты: {expire_date}"
    )
    

@dp.message(Command("check"))
async def command_check(message: Message):
    with open("data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    user_info = data.get(str(message.from_user.id))
    if not user_info or not user_info.get('expire'):
        await message.answer("❌ У тебя нет даты оплаты, напиши @ameright.")
        return

    date = datetime.fromisoformat(user_info['expire'])
    days_left = (date.date() - datetime.now().date()).days

    status_text = await get_status_message(days_left, date.strftime('%d.%m.%Y'))
    await message.answer(status_text)
    try:
        await bot.send_message(chat_id=mer_id, text=f"@{message.from_user.username} осталось {days_left} д. до оплаты.")
    except Exception as e:
        logging.warning(f"Не удалось уведомить админа: {e}")

@dp.message(Command("update"))
async def command_update(message: Message):
   if message.from_user.id != mer_id:
       await message.answer("❌ У тебя нет прав на выполнение этой команды.")
       return

   parts = message.text.split()
   if len(parts) != 3:
        await message.answer("❌ Неверный формат команды. Используй: /update <username> <YYYY-MM-DD>")
        return
   username, date_str = parts[1], parts[2]
   try: datetime.fromisoformat(date_str)
   except ValueError:
        await message.answer("❌ Неверный формат даты. Используй: YYYY-MM-DD")
        return

   with open("data.json", "r", encoding="utf-8") as f:
       data = json.load(f)

   for uid, info in data.items():
       if info['username'] == username:
           info['expire'] = date_str
           break

   with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

   await message.answer(f"✅ Дата оплаты для @{username} обновлена на {date_str}.")
           
       
   

REMIND_DAYS = [3, 1, 0]
async def reminder_loop():
    while True:
        with open("data.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        today = datetime.now().date().isoformat()
        changed = False

        for user_id, info in data.items():
            if not info['expire']:
                continue
            expire = datetime.fromisoformat(info['expire'])
            days_left = (expire.date() - datetime.now().date()).days
            notified = info['notified']

            if (days_left in REMIND_DAYS or days_left <= 0) and notified != today:
                status_text = await get_status_message(days_left, expire.strftime('%d.%m.%Y'))
                try:
                    await bot.send_message(int(user_id), text=status_text)
                except Exception as e:
                    logging.warning(f"Не удалось отправить сообщение {user_id}: {e}")

                try:
                    await bot.send_message(chat_id=mer_id, text=f"@{info['username']} осталось {days_left} д. до оплаты.")
                except Exception as e:
                    logging.warning(f"Не удалось отправить сообщение mer_id: {e}")

                info['notified'] = today
                changed = True

        if changed:
            with open("data.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        await asyncio.sleep(3600)

async def main():
    await asyncio.gather(
        dp.start_polling(bot),
        reminder_loop()
    )

if __name__ == "__main__":
    asyncio.run(main())