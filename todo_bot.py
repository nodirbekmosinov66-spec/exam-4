import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN") 

def init_db():
    with sqlite3.connect("todo.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            due_date TEXT,
            status TEXT DEFAULT 'pending'
        )
        """)
        conn.commit()

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class TaskForm(StatesGroup):
    title = State()
    due_date = State()

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Vazifa qo'shish")],
            [KeyboardButton(text="Vazifalarim"), KeyboardButton(text="Statistika")]
        ],
        resize_keyboard=True
    )

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Foydalanuvchi"
    try:
        with sqlite3.connect("todo.db") as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
            conn.commit()
    except Exception:
        pass
    await message.answer(f"Salom, {username}! Todo botga xush kelibsiz.", reply_markup=main_menu())

@dp.message(F.text == "Vazifa qo'shish")
async def add_task_start(message: Message, state: FSMContext):
    await state.set_state(TaskForm.title)
    await message.answer("Vazifa nomini kiriting:")

@dp.message(TaskForm.title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(TaskForm.due_date)
    await message.answer("Vazifa muddatini kiriting (KK.OO.YYYY formatida) yoki 'O'tkazib yuborish' tugmasini bosing:", 
                         reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="O'tkazib yuborish")]], resize_keyboard=True))

@dp.message(TaskForm.due_date)
async def process_due_date(message: Message, state: FSMContext):
    text = message.text
    due_date = None
    if text != "O'tkazib yuborish":
        try:
            parsed_date = datetime.strptime(text, "%d.%m.%Y")
            if parsed_date.date() < datetime.now().date():
                await message.answer("O'tib ketgan sana qabul qilinmaydi. To'g'ri muddat kiriting:")
                return
            due_date = text
        except ValueError:
            await message.answer("Format noto'g'ri. Muddatni KK.OO.YYYY formatida kiriting:")
            return
    else:
        due_date = "Muddatsiz"

    data = await state.get_data()
    user_id = message.from_user.id
    try:
        with sqlite3.connect("todo.db") as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO tasks (user_id, title, due_date) VALUES (?, ?, ?)", (user_id, data['title'], due_date))
            conn.commit()
        await message.answer("Vazifa muvaffaqiyatli qo'shildi!", reply_markup=main_menu())
    except Exception:
        await message.answer("Xatolik yuz berdi. Qaytadan urunib ko'ring.", reply_markup=main_menu())
    await state.clear()

@dp.message(F.text == "Vazifalarim")
async def show_tasks(message: Message):
    user_id = message.from_user.id
    try:
        with sqlite3.connect("todo.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, due_date FROM tasks WHERE user_id = ? AND status = 'pending'", (user_id,))
            tasks = cursor.fetchall()
            
        if not tasks:
            await message.answer("Sizda faol vazifalar mavjud emas.")
            return
        
        for task in tasks:
            t_id, title, due = task
            due_str = f"\nMuddat: {due}" if due else ""
            text = f"📌 {title}{due_str}"
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Bajarildi", callback_data=f"done_{t_id}"),
                 InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"del_{t_id}")]
            ])
            await message.answer(text, reply_markup=kb)
    except Exception:
        await message.answer("Ma'lumotlarni yuklashda xatolik.")

# TO'G'RILANDI: Bajarildi bosilganda Qaytarish imkoniyati
@dp.callback_query(F.data.startswith("done_"))
async def done_task(callback: CallbackQuery):
    t_id = int(callback.data.split("_")[1])
    try:
        with sqlite3.connect("todo.db") as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (t_id,))
            conn.commit()
            
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Qaytarish (Undo)", callback_data=f"undo_{t_id}")]
        ])
        await callback.message.edit_text("✅ Vazifa bajarildi deb belgilandi!", reply_markup=kb)
    except Exception:
        await callback.answer("Xatolik yuz berdi.")

# TO'G'RILANDI: O'chirish bosilganda Qaytarish imkoniyati
@dp.callback_query(F.data.startswith("del_"))
async def delete_task(callback: CallbackQuery):
    t_id = int(callback.data.split("_")[1])
    try:
        with sqlite3.connect("todo.db") as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET status = 'deleted' WHERE id = ?", (t_id,))
            conn.commit()
            
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Qaytarish (Undo)", callback_data=f"undo_{t_id}")]
        ])
        await callback.message.edit_text("🗑 Vazifa o'chirildi!", reply_markup=kb)
    except Exception:
        await callback.answer("Xatolik yuz berdi.")

# TO'G'RILANDI: Amalni bekor qilib ortga qaytarish tugmasi handle-ri
@dp.callback_query(F.data.startswith("undo_"))
async def undo_task(callback: CallbackQuery):
    t_id = int(callback.data.split("_")[1])
    try:
        with sqlite3.connect("todo.db") as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET status = 'pending' WHERE id = ?", (t_id,))
            conn.commit()
            cursor.execute("SELECT title, due_date FROM tasks WHERE id = ?", (t_id,))
            title, due = cursor.fetchone()
            
        due_str = f"\nMuddat: {due}" if due else ""
        text = f"📌 {title}{due_str}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Bajarildi", callback_data=f"done_{t_id}"),
             InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"del_{t_id}")]
        ])
        await callback.message.edit_text(text, reply_markup=kb)
        await callback.answer("Amal bekor qilindi.")
    except Exception:
        await callback.answer("Qaytarishda xatolik yuz berdi.")

@dp.message(F.text == "Statistika")
async def show_stats(message: Message):
    user_id = message.from_user.id
    try:
        with sqlite3.connect("todo.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status != 'deleted'", (user_id,))
            total = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'completed'", (user_id,))
            completed = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'pending'", (user_id,))
            pending = cursor.fetchone()[0]
        
        text = f"📊 Sizning statistika:\n\nJami faol vazifalar: {total}\nBajarilgan: {completed}\nQolgan: {pending}"
        await message.answer(text)
    except Exception:
        await message.answer("Statistikani hisoblashda xatolik.")

if __name__ == "__main__":
    import asyncio
    init_db()
    print("Bot ishga tushdi...")
    asyncio.run(dp.start_polling(bot))
