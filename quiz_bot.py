import os
import json
import random
import sqlite3
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# .env faylini yuklaymiz
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

conn = sqlite3.connect("quiz.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    score INTEGER,
    total INTEGER,
    percentage REAL,
    grade TEXT,
    date TEXT DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

with open("questions.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class QuizState(StatesGroup):
    playing = State()

def start_menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Testni boshlash")]], resize_keyboard=True)

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Quiz botga xush kelibsiz! Testni boshlash uchun quyidagi tugmani bosing.\nOxirgi urinishlarni ko'rish: /natijalarim", reply_markup=start_menu())

@dp.message(F.text == "Testni boshlash")
async def start_quiz(message: Message, state: FSMContext):
    total_to_play = min(10, len(QUESTIONS))
    selected_indices = random.sample(range(len(QUESTIONS)), total_to_play)
    
    await state.set_state(QuizState.playing)
    await state.update_data(q_indices=selected_indices, current_idx=0, score=0)
    await send_question(message, state)

async def send_question(message, state: FSMContext):
    data = await state.get_data()
    current_idx = data['current_idx']
    idx = data['q_indices'][current_idx]
    question_data = QUESTIONS[idx]
    
    options = list(question_data['options'])
    random.shuffle(options)
    
    kb_list = []
    for opt in options:
        kb_list.append([InlineKeyboardButton(text=opt, callback_data=f"ans_{opt}")])
    
    # TO'G'RILANDI: Har bir savol ostiga "Testni tugatish" tugmasi qo'shildi
    kb_list.append([InlineKeyboardButton(text="❌ Testni tugatish", callback_data="stop_quiz")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_list)
    
    text = f"{current_idx + 1}-savol: {question_data['question']}"
    
    if isinstance(message, Message):
        await message.answer(text, reply_markup=kb)
    else:
        await message.message.answer(text, reply_markup=kb)

# TO'G'RILANDI: "Testni tugatish" tugmasi bosilganda ishlaydigan handler
@dp.callback_query(QuizState.playing, F.data == "stop_quiz")
async def stop_quiz_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Test foydalanuvchi tomonidan to'xtatildi.")
    await callback.message.answer("Test bekor qilindi. Istalgan vaqtda qaytadan boshlashingiz mumkin.", reply_markup=start_menu())
    await state.clear()
    await callback.answer()

@dp.callback_query(QuizState.playing, F.data.startswith("ans_"))
async def check_answer(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    user_ans = callback.data.replace("ans_", "")
    current_idx = data['current_idx']
    idx = data['q_indices'][current_idx]
    question_data = QUESTIONS[idx]
    correct_ans = question_data['correct']
    
    score = data['score']
    
    if user_ans == correct_ans:
        score += 1
        await state.update_data(score=score)
        await callback.message.edit_text(f"{callback.message.text}\n\nSizning javobingiz: {user_ans}\n✅ To'g'ri!")
    else:
        await callback.message.edit_text(f"{callback.message.text}\n\nSizning javobingiz: {user_ans}\n❌ Noto'g'ri!\nTo'g'ri javob: {correct_ans}")
        
    next_idx = current_idx + 1
    await state.update_data(current_idx=next_idx)
    
    if next_idx < len(data['q_indices']):
        await send_question(callback, state)
    else:
        total = len(data['q_indices'])
        percentage = (score / total) * 100
        
        if percentage >= 90: grade = "A'lo"
        elif percentage >= 70: grade = "Yaxshi"
        elif percentage >= 50: grade = "Qoniqarli"
        else: grade = "Qoniqarsiz"
        
        try:
            with sqlite3.connect("quiz.db") as db:
                db.execute("INSERT INTO results (user_id, score, total, percentage, grade) VALUES (?, ?, ?, ?, ?)",
                           (callback.from_user.id, score, total, percentage, grade))
                db.commit()
        except Exception:
            pass
            
        await callback.message.answer(
            f"🏁 Test yakunlandi!\n\nNatija: {score}/{total}\nFoiz: {percentage:.1f}%\nBaho: {grade}", 
            reply_markup=start_menu()
        )
        await state.clear()

@dp.message(Command("natijalarim"))
async def show_results(message: Message):
    try:
        with sqlite3.connect("quiz.db") as db:
            c = db.cursor()
            c.execute("SELECT score, total, percentage, grade FROM results WHERE user_id = ? ORDER BY id DESC LIMIT 5", (message.from_user.id,))
            rows = c.fetchall()
            
        if not rows:
            await message.answer("Sizda hali urinishlar mavjud emas.")
            return
        text = "📊 Oxirgi 5 ta urinishingiz:\n\n"
        for i, row in enumerate(rows, 1):
            text += f"{i}. Natija: {row[0]}/{row[1]} | {row[2]:.1f}% | Baho: {row[3]}\n"
        await message.answer(text)
    except Exception:
        await message.answer("Natijalarni yuklashda xatolik.")

if __name__ == "__main__":
    import asyncio
    print("Quiz bot ishga tushdi...")
    asyncio.run(dp.start_polling(bot))
