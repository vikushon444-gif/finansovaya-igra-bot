
bot-full.py
# Финансовая Игра - Telegram Bot
# Полная версия со всеми командами
# Python 3.10+

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import aiosqlite

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = "8224609039:AAH_0u2_LDxVSJ3h13bsUldsNqg4gyn6dFA"
DB_PATH = "financial_game.db"

# Логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Инициализация
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# ==================== FSM STATES ====================
class OnboardingStates(StatesGroup):
    waiting_for_debts_answer = State()
    waiting_for_debt_name = State()
    waiting_for_debt_amount = State()
    waiting_for_debt_rate = State()
    waiting_for_debt_payment = State()
    waiting_for_debt_date = State()
    waiting_for_strategy = State()
    waiting_for_income = State()
    waiting_for_account_type = State()
    waiting_for_account_name = State()
    waiting_for_account_balance = State()

class ExpenseStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_category = State()
    waiting_for_description = State()

class IncomeStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_description = State()

class AccountStates(StatesGroup):
    waiting_for_type = State()
    waiting_for_name = State()
    waiting_for_balance = State()

class DebtStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_amount = State()
    waiting_for_rate = State()
    waiting_for_payment = State()
    waiting_for_date = State()

class DebtPaymentStates(StatesGroup):
    waiting_for_debt_selection = State()
    waiting_for_amount = State()

class GoalStates(StatesGroup):
    waiting_for_type = State()
    waiting_for_name = State()
    waiting_for_amount = State()

# ==================== КОНСТАНТЫ ====================
CATEGORIES = {
    'Необходимое (50%)': ['Продукты 🛒', 'Жильё и ЖКХ 🏠', 'Транспорт 🚗', 'Медицина 💊', 'Связь 📱', 'Одежда 👕', 'Образование 📚'],
    'Желаемое (30%)': ['Рестораны 🍽️', 'Развлечения 🎬', 'Подписки 📺', 'Спорт 💪', 'Красота 💅', 'Хобби 🎨', 'Путешествия ✈️', 'Шопинг 🛍️'],
    'Сбережения (20%)': ['Подушка безопасности 💰', 'Погашение долгов 💳', 'Инвестиции 📈', 'Накопления 🎯']
}

LEVELS = [
    {"level": 1, "name": "🔴 Финансовое пробуждение", "score": 0},
    {"level": 2, "name": "🟠 Контроль и выживание", "score": 400},
    {"level": 3, "name": "🟡 Стабильность", "score": 1400},
    {"level": 4, "name": "🟢 Рост и инвестиции", "score": 3400},
    {"level": 5, "name": "🔵 Финансовая независимость", "score": 5400},
    {"level": 6, "name": "💎 Финансовая свобода", "score": 9400}
]

ACCOUNT_TYPES = ['Банковская карта 💳', 'Наличные 💵', 'Депозит 🏦', 'Актив 📊']
GOAL_TYPES = ['Погашение долга 💳', 'Подушка безопасности 💰', 'Накопления 💎', 'Инвестиции 📈']

# ==================== DATABASE ====================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            current_level INTEGER DEFAULT 1,
            total_score INTEGER DEFAULT 0,
            monthly_income REAL DEFAULT 0,
            onboarding_completed BOOLEAN DEFAULT 0,
            debt_strategy TEXT
        )''')
        
        await db.execute('''CREATE TABLE IF NOT EXISTS accounts (
            account_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            account_type TEXT NOT NULL,
            account_name TEXT NOT NULL,
            balance REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )''')
        
        await db.execute('''CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            account_id INTEGER,
            amount REAL NOT NULL,
            transaction_type TEXT NOT NULL,
            category TEXT,
            description TEXT,
            transaction_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )''')
        
        await db.execute('''CREATE TABLE IF NOT EXISTS debts (
            debt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            debt_name TEXT NOT NULL,
            total_amount REAL NOT NULL,
            remaining_amount REAL NOT NULL,
            interest_rate REAL DEFAULT 0,
            minimum_payment REAL DEFAULT 0,
            due_date DATE,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )''')
        
        await db.execute('''CREATE TABLE IF NOT EXISTS goals (
            goal_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            goal_type TEXT NOT NULL,
            goal_name TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )''')
        
        await db.commit()
    logger.info("База данных инициализирована")

# ==================== HELPERS ====================
async def get_user(chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT * FROM users WHERE chat_id = ?', (chat_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {'user_id': row[0], 'chat_id': row[1], 'username': row[2], 'first_name': row[3],
                        'current_level': row[5], 'total_score': row[6], 'monthly_income': row[7],
                        'onboarding_completed': row[8], 'debt_strategy': row[9]}
    return None

async def create_user(chat_id: int, username: str, first_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('INSERT INTO users (chat_id, username, first_name) VALUES (?, ?, ?)',
                        (chat_id, username, first_name))
        await db.commit()

async def add_score(user_id: int, points: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE users SET total_score = total_score + ? WHERE user_id = ?', (points, user_id))
        await db.commit()
        
        async with db.execute('SELECT total_score, current_level FROM users WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                score, current_level = row[0], row[1]
                for level_data in LEVELS:
                    if level_data['level'] > current_level and score >= level_data['score']:
                        await db.execute('UPDATE users SET current_level = ? WHERE user_id = ?', (level_data['level'], user_id))
                        await db.commit()
                        return level_data
    return None

def format_money(amount: float) -> str:
    return f"{amount:,.0f}".replace(',', ' ') + " ₽"

def get_level_data(level_number: int):
    for level in LEVELS:
        if level['level'] == level_number:
            return level
    return LEVELS[0]

def create_category_keyboard():
    buttons = []
    for group, cats in CATEGORIES.items():
        for cat in cats:
            buttons.append([InlineKeyboardButton(text=cat, callback_data=f"cat_{cat}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ==================== HANDLERS ====================

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    
    if not user:
        await create_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
        await message.answer(
            "🎮 Добро пожаловать в Финансовую Игру!\n\n"
            "Я помогу вам пройти путь от долгов до финансовой свободы через 6 уровней роста.\n\n"
            "Давайте начнём с быстрой диагностики вашей ситуации."
        )
        
        keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Нет")]], resize_keyboard=True)
        await message.answer("📊 У вас сейчас есть долги или кредиты?", reply_markup=keyboard)
        await state.set_state(OnboardingStates.waiting_for_debts_answer)
    else:
        if not user['onboarding_completed']:
            await message.answer("Продолжим настройку!")
            keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Нет")]], resize_keyboard=True)
            await message.answer("📊 У вас сейчас есть долги или кредиты?", reply_markup=keyboard)
            await state.set_state(OnboardingStates.waiting_for_debts_answer)
        else:
            level_data = get_level_data(user['current_level'])
            await message.answer(
                f"С возвращением, {message.from_user.first_name}! 👋\n\n"
                f"Ваш уровень: {level_data['name']}\n"
                f"Очки: {user['total_score']}\n\n"
                f"Используйте /help для списка команд",
                reply_markup=ReplyKeyboardRemove()
            )

@router.message(OnboardingStates.waiting_for_debts_answer)
async def process_debts_answer(message: Message, state: FSMContext):
    if message.text == "Да":
        await message.answer("Добавим ваш первый долг.\n\nВведите название долга (например: Кредит в банке, Займ у друга):", reply_markup=ReplyKeyboardRemove())
        await state.set_state(OnboardingStates.waiting_for_debt_name)
    else:
        await message.answer("Отлично! У вас нет долгов. 🎉\n\nУкажите ваш средний ежемесячный доход в рублях:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(OnboardingStates.waiting_for_income)

@router.message(OnboardingStates.waiting_for_debt_name)
async def process_debt_name(message: Message, state: FSMContext):
    await state.update_data(debt_name=message.text)
    await message.answer("Какая общая сумма долга? (только цифры)")
    await state.set_state(OnboardingStates.waiting_for_debt_amount)

@router.message(OnboardingStates.waiting_for_debt_amount)
async def process_debt_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(' ', '').replace(',', '.'))
        await state.update_data(debt_amount=amount)
        await message.answer("Какая процентная ставка по долгу? (например: 15.5)")
        await state.set_state(OnboardingStates.waiting_for_debt_rate)
    except:
        await message.answer("Пожалуйста, введите корректную сумму (только цифры)")

@router.message(OnboardingStates.waiting_for_debt_rate)
async def process_debt_rate(message: Message, state: FSMContext):
    try:
        rate = float(message.text.replace(',', '.'))
        await state.update_data(debt_rate=rate)
        await message.answer("Минимальный ежемесячный платёж? (цифры)")
        await state.set_state(OnboardingStates.waiting_for_debt_payment)
    except:
        await message.answer("Введите корректную процентную ставку")

@router.message(OnboardingStates.waiting_for_debt_payment)
async def process_debt_payment(message: Message, state: FSMContext):
    try:
        payment = float(message.text.replace(' ', '').replace(',', '.'))
        await state.update_data(debt_payment=payment)
        await message.answer("Когда следующий платёж? (день месяца, например: 15)")
        await state.set_state(OnboardingStates.waiting_for_debt_date)
    except:
        await message.answer("Введите корректную сумму платежа")

@router.message(OnboardingStates.waiting_for_debt_date)
async def process_debt_date(message: Message, state: FSMContext):
    try:
        day = int(message.text)
        if 1 <= day <= 31:
            data = await state.get_data()
            user = await get_user(message.from_user.id)
            
            # Сохранить долг
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    'INSERT INTO debts (user_id, debt_name, total_amount, remaining_amount, interest_rate, minimum_payment, due_date, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (user['user_id'], data['debt_name'], data['debt_amount'], data['debt_amount'], data['debt_rate'], data['debt_payment'], day, 'active')
                )
                await db.commit()
            
            await add_score(user['user_id'], 100)
            await message.answer(f"✅ Долг добавлен: {data['debt_name']} — {format_money(data['debt_amount'])}\n\n+100 очков опыта!")
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔥 Лавина (высокие ставки)", callback_data="strategy_avalanche")],
                [InlineKeyboardButton(text="❄️ Снежный ком (маленькие долги)", callback_data="strategy_snowball")],
                [InlineKeyboardButton(text="⚡️ Гибрид", callback_data="strategy_hybrid")]
            ])
            await message.answer(
                "💡 Выберите стратегию погашения долгов:\n\n"
                "🔥 Лавина — сначала долги с высокой ставкой\n"
                "❄️ Снежный ком — сначала маленькие долги\n"
                "⚡️ Гибрид — комбинация обеих",
                reply_markup=keyboard
            )
            await state.set_state(OnboardingStates.waiting_for_strategy)
        else:
            await message.answer("Введите день от 1 до 31")
    except:
        await message.answer("Введите корректный день месяца")

@router.callback_query(OnboardingStates.waiting_for_strategy)
async def process_strategy(callback: CallbackQuery, state: FSMContext):
    strategy = callback.data.replace('strategy_', '')
    user = await get_user(callback.from_user.id)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE users SET debt_strategy = ? WHERE user_id = ?', (strategy, user['user_id']))
        await db.commit()
    
    await callback.message.edit_text(f"✅ Стратегия выбрана: {strategy}")
    await callback.message.answer("💵 Укажите ваш средний ежемесячный доход в рублях:")
    await state.set_state(OnboardingStates.waiting_for_income)

@router.message(OnboardingStates.waiting_for_income)
async def process_income(message: Message, state: FSMContext):
    try:
        income = float(message.text.replace(' ', '').replace(',', '.'))
        user = await get_user(message.from_user.id)
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('UPDATE users SET monthly_income = ? WHERE user_id = ?', (income, user['user_id']))
            await db.commit()
        
        await add_score(user['user_id'], 50)
        
        necessary = income * 0.5
        desired = income * 0.3
        savings = income * 0.2
        
        await message.answer(
            f"✅ Доход сохранён: {format_money(income)}\n\n"
            f"📊 Бюджет 50/30/20:\n"
            f"• Необходимое (50%): {format_money(necessary)}\n"
            f"• Желаемое (30%): {format_money(desired)}\n"
            f"• Сбережения (20%): {format_money(savings)}\n\n"
            f"+50 очков опыта!"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Банковская карта", callback_data="acc_card")],
            [InlineKeyboardButton(text="💵 Наличные", callback_data="acc_cash")],
            [InlineKeyboardButton(text="🏦 Депозит", callback_data="acc_deposit")]
        ])
        await message.answer("Добавьте ваш первый счёт:", reply_markup=keyboard)
        await state.set_state(OnboardingStates.waiting_for_account_type)
    except:
        await message.answer("Введите корректную сумму дохода")

@router.callback_query(OnboardingStates.waiting_for_account_type)
async def process_account_type(callback: CallbackQuery, state: FSMContext):
    acc_type = callback.data.replace('acc_', '')
    type_names = {'card': 'Банковская карта', 'cash': 'Наличные', 'deposit': 'Депозит'}
    await state.update_data(account_type=type_names.get(acc_type, 'Счёт'))
    await callback.message.edit_text(f"✅ Тип: {type_names.get(acc_type)}")
    await callback.message.answer("Введите название счёта (например: Основная карта, Зарплатная):")
    await state.set_state(OnboardingStates.waiting_for_account_name)

@router.message(OnboardingStates.waiting_for_account_name)
async def process_account_name(message: Message, state: FSMContext):
    await state.update_data(account_name=message.text)
    await message.answer("Какой текущий баланс на этом счёте? (цифры)")
    await state.set_state(OnboardingStates.waiting_for_account_balance)

@router.message(OnboardingStates.waiting_for_account_balance)
async def process_account_balance(message: Message, state: FSMContext):
    try:
        balance = float(message.text.replace(' ', '').replace(',', '.'))
        data = await state.get_data()
        user = await get_user(message.from_user.id)
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                'INSERT INTO accounts (user_id, account_type, account_name, balance) VALUES (?, ?, ?, ?)',
                (user['user_id'], data['account_type'], data['account_name'], balance)
            )
            await db.execute('UPDATE users SET onboarding_completed = 1 WHERE user_id = ?', (user['user_id'],))
            await db.commit()
        
        await add_score(user['user_id'], 50)
        
        user = await get_user(message.from_user.id)
        level_data = get_level_data(user['current_level'])
        
        await message.answer(
            f"🎯 Онбординг завершён!\n\n"
            f"Ваш уровень: {level_data['name']}\n"
            f"Очки: {user['total_score']}\n\n"
            f"Используйте /help для списка команд\n"
            f"Используйте /level для просмотра прогресса"
        )
        await state.clear()
    except:
        await message.answer("Введите корректную сумму")

@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = '''📚 Доступные команды:

💰 Финансы:
/add_expense - Добавить расход
/add_income - Добавить доход
/add_account - Добавить счёт
/accounts - Мои счета
/budget - Бюджет 50/30/20

💳 Долги:
/add_debt - Добавить долг
/debts - Список долгов
/pay_debt - Внести платёж

🎯 Цели и уровни:
/goals - Мои цели
/add_goal - Создать цель
/level - Текущий уровень
/progress - Мой прогресс

📊 Отчёты:
/summary - Сводка за период
/stats - Статистика

💡 Прочее:
/motivation - Получить совет
/help - Эта справка'''
    
    await message.answer(help_text)

@router.message(Command("add_expense"))
async def cmd_add_expense(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user or not user['onboarding_completed']:
        await message.answer("Сначала завершите настройку: /start")
        return
    
    await message.answer("💸 Введите сумму расхода (только цифры):")
    await state.set_state(ExpenseStates.waiting_for_amount)

@router.message(ExpenseStates.waiting_for_amount)
async def process_expense_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(' ', '').replace(',', '.'))
        await state.update_data(amount=amount)
        await message.answer("Выберите категорию:", reply_markup=create_category_keyboard())
        await state.set_state(ExpenseStates.waiting_for_category)
    except:
        await message.answer("Введите корректную сумму")

@router.callback_query(ExpenseStates.waiting_for_category)
async def process_expense_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.replace('cat_', '')
    await state.update_data(category=category)
    await callback.message.edit_text(f"✅ Категория: {category}")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Добавить описание", callback_data="desc_yes")],
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="desc_no")]
    ])
    await callback.message.answer("Добавить описание?", reply_markup=keyboard)
    await state.set_state(ExpenseStates.waiting_for_description)

@router.callback_query(ExpenseStates.waiting_for_description)
async def process_expense_description_choice(callback: CallbackQuery, state: FSMContext):
    if callback.data == "desc_no":
        await save_expense(callback.message, state, "")
    else:
        await callback.message.edit_text("Введите описание расхода:")
        await state.set_state(ExpenseStates.waiting_for_description)

@router.message(ExpenseStates.waiting_for_description)
async def process_expense_description_text(message: Message, state: FSMContext):
    await save_expense(message, state, message.text)

async def save_expense(message: Message, state: FSMContext, description: str):
    data = await state.get_data()
    user = await get_user(message.from_user.id if hasattr(message, 'from_user') else message.chat.id)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO transactions (user_id, amount, transaction_type, category, description, transaction_date) VALUES (?, ?, ?, ?, ?, ?)',
            (user['user_id'], data['amount'], 'expense', data['category'], description, datetime.now().date())
        )
        await db.commit()
    
    new_level = await add_score(user['user_id'], 10)
    
    response = f"✅ Расход добавлен: {format_money(data['amount'])}\nКатегория: {data['category']}\n\n+10 очков!"
    
    if new_level:
        response += f"\n\n🎉 НОВЫЙ УРОВЕНЬ!\nВы достигли: {new_level['name']}!"
    
    await message.answer(response)
    await state.clear()

@router.message(Command("add_income"))
async def cmd_add_income(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user or not user['onboarding_completed']:
        await message.answer("Сначала завершите настройку: /start")
        return
    
    await message.answer("💰 Введите сумму дохода:")
    await state.set_state(IncomeStates.waiting_for_amount)

@router.message(IncomeStates.waiting_for_amount)
async def process_income_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(' ', '').replace(',', '.'))
        await state.update_data(amount=amount)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Добавить описание", callback_data="inc_desc_yes")],
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="inc_desc_no")]
        ])
        await message.answer("Добавить описание?", reply_markup=keyboard)
        await state.set_state(IncomeStates.waiting_for_description)
    except:
        await message.answer("Введите корректную сумму")

@router.callback_query(IncomeStates.waiting_for_description)
async def process_income_description_choice(callback: CallbackQuery, state: FSMContext):
    if callback.data == "inc_desc_no":
        await save_income(callback.message, state, "")
    else:
        await callback.message.edit_text("Введите описание дохода:")

@router.message(IncomeStates.waiting_for_description)
async def process_income_description_text(message: Message, state: FSMContext):
    await save_income(message, state, message.text)

async def save_income(message: Message, state: FSMContext, description: str):
    data = await state.get_data()
    user = await get_user(message.from_user.id if hasattr(message, 'from_user') else message.chat.id)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO transactions (user_id, amount, transaction_type, category, description, transaction_date) VALUES (?, ?, ?, ?, ?, ?)',
            (user['user_id'], data['amount'], 'income', 'Доход', description, datetime.now().date())
        )
        await db.commit()
    
    new_level = await add_score(user['user_id'], 10)
    
    response = f"✅ Доход добавлен: {format_money(data['amount'])}\n\n+10 очков!"
    
    if new_level:
        response += f"\n\n🎉 НОВЫЙ УРОВЕНЬ!\nВы достигли: {new_level['name']}!"
    
    await message.answer(response)
    await state.clear()

@router.message(Command("accounts"))
async def cmd_accounts(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Используйте /start")
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT account_type, account_name, balance FROM accounts WHERE user_id = ?', (user['user_id'],)) as cursor:
            accounts = await cursor.fetchall()
    
    if not accounts:
        await message.answer("У вас пока нет счетов.\nДобавьте первый: /add_account")
        return
    
    total = sum(acc[2] for acc in accounts)
    response = "💳 Ваши счета:\n\n"
    for acc in accounts:
        response += f"{acc[0]}: {acc[1]}\nБаланс: {format_money(acc[2])}\n\n"
    response += f"📊 Общий баланс: {format_money(total)}"
    
    await message.answer(response)

@router.message(Command("debts"))
async def cmd_debts(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Используйте /start")
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT debt_name, total_amount, remaining_amount, interest_rate, minimum_payment, due_date FROM debts WHERE user_id = ? AND status = ?',
            (user['user_id'], 'active')
        ) as cursor:
            debts = await cursor.fetchall()
    
    if not debts:
        await message.answer("🎉 У вас нет активных долгов!\n\nОтличная работа! Продолжайте в том же духе!")
        return
    
    total_debt = sum(d[2] for d in debts)
    response = "💳 Ваши долги:\n\n"
    
    for debt in debts:
        progress = ((debt[1] - debt[2]) / debt[1]) * 100
        response += f"📍 {debt[0]}\n"
        response += f"Осталось: {format_money(debt[2])} из {format_money(debt[1])}\n"
        response += f"Прогресс: {progress:.1f}%\n"
        response += f"Ставка: {debt[3]}%\n"
        response += f"Мин. платёж: {format_money(debt[4])}\n"
        response += f"Следующий платёж: {debt[5]} числа\n\n"
    
    response += f"📊 Всего долгов: {format_money(total_debt)}\n\n"
    response += "Используйте /pay_debt для внесения платежа"
    
    await message.answer(response)

@router.message(Command("goals"))
async def cmd_goals(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Используйте /start")
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT goal_type, goal_name, target_amount, current_amount FROM goals WHERE user_id = ? AND status = ?',
            (user['user_id'], 'active')
        ) as cursor:
            goals = await cursor.fetchall()
    
    if not goals:
        await message.answer("У вас пока нет активных целей.\nСоздайте первую: /add_goal")
        return
    
    response = "🎯 Ваши цели:\n\n"
    
    for goal in goals:
        progress = (goal[3] / goal[2]) * 100
        remaining = goal[2] - goal[3]
        response += f"{goal[0]}\n"
        response += f"📌 {goal[1]}\n"
        response += f"Цель: {format_money(goal[2])}\n"
        response += f"Накоплено: {format_money(goal[3])} ({progress:.1f}%)\n"
        response += f"Осталось: {format_money(remaining)}\n\n"
    
    await message.answer(response)

@router.message(Command("level"))
async def cmd_level(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Используйте /start")
        return
    
    level_data = get_level_data(user['current_level'])
    next_level = None
    if user['current_level'] < len(LEVELS):
        next_level = LEVELS[user['current_level']]
    
    response = f"{level_data['name']}\n\n"
    response += f"💎 Ваши очки: {user['total_score']}"
    
    if next_level:
        needed = next_level['score'] - user['total_score']
        progress = (user['total_score'] / next_level['score']) * 100
        response += f" / {next_level['score']}\n"
        response += f"До следующего уровня: {needed} очков ({progress:.1f}%)\n\n"
        response += f"Следующий уровень: {next_level['name']}"
    else:
        response += "\n\n🏆 Максимальный уровень достигнут!\nПоздравляем с финансовой свободой!"
    
    await message.answer(response)

@router.message(Command("budget"))
async def cmd_budget(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Используйте /start")
        return
    
    if user['monthly_income'] == 0:
        await message.answer("Укажите ваш месячный доход в настройках")
        return
    
    income = user['monthly_income']
    necessary = income * 0.5
    desired = income * 0.3
    savings = income * 0.2
    
    # Получить расходы за текущий месяц
    async with aiosqlite.connect(DB_PATH) as db:
        start_of_month = datetime.now().replace(day=1).date()
        async with db.execute(
            'SELECT category, SUM(amount) FROM transactions WHERE user_id = ? AND transaction_type = ? AND transaction_date >= ? GROUP BY category',
            (user['user_id'], 'expense', start_of_month)
        ) as cursor:
            expenses = await cursor.fetchall()
    
    spent_necessary = 0
    spent_desired = 0
    spent_savings = 0
    
    for cat, amount in expenses:
        if any(c in cat for c in CATEGORIES['Необходимое (50%)']):
            spent_necessary += amount
        elif any(c in cat for c in CATEGORIES['Желаемое (30%)']):
            spent_desired += amount
        elif any(c in cat for c in CATEGORIES['Сбережения (20%)']):
            spent_savings += amount
    
    response = f"📊 Бюджет 50/30/20\nДоход: {format_money(income)}\n\n"
    
    response += f"🏠 Необходимое (50%)\n"
    response += f"Лимит: {format_money(necessary)}\n"
    response += f"Потрачено: {format_money(spent_necessary)}\n"
    response += f"Остаток: {format_money(necessary - spent_necessary)}\n\n"
    
    response += f"🎬 Желаемое (30%)\n"
    response += f"Лимит: {format_money(desired)}\n"
    response += f"Потрачено: {format_money(spent_desired)}\n"
    response += f"Остаток: {format_money(desired - spent_desired)}\n\n"
    
    response += f"💰 Сбережения (20%)\n"
    response += f"Цель: {format_money(savings)}\n"
    response += f"Накоплено: {format_money(spent_savings)}\n"
    response += f"Осталось: {format_money(savings - spent_savings)}"
    
    await message.answer(response)

@router.message(Command("summary"))
async def cmd_summary(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Используйте /start")
        return
    
    # Статистика за текущий месяц
    async with aiosqlite.connect(DB_PATH) as db:
        start_of_month = datetime.now().replace(day=1).date()
        
        async with db.execute(
            'SELECT SUM(amount) FROM transactions WHERE user_id = ? AND transaction_type = ? AND transaction_date >= ?',
            (user['user_id'], 'income', start_of_month)
        ) as cursor:
            income_row = await cursor.fetchone()
            total_income = income_row[0] if income_row[0] else 0
        
        async with db.execute(
            'SELECT SUM(amount) FROM transactions WHERE user_id = ? AND transaction_type = ? AND transaction_date >= ?',
            (user['user_id'], 'expense', start_of_month)
        ) as cursor:
            expense_row = await cursor.fetchone()
            total_expense = expense_row[0] if expense_row[0] else 0
    
    balance = total_income - total_expense
    
    response = f"📊 Сводка за {datetime.now().strftime('%B %Y')}\n\n"
    response += f"💰 Доходы: {format_money(total_income)}\n"
    response += f"💸 Расходы: {format_money(total_expense)}\n"
    response += f"{'📈' if balance >= 0 else '📉'} Баланс: {format_money(balance)}\n\n"
    
    if balance >= 0:
        response += "✅ Отличная работа! Вы в плюсе!"
    else:
        response += "⚠️ Расходы превысили доходы. Проверьте бюджет: /budget"
    
    await message.answer(response)

@router.message(Command("motivation"))
async def cmd_motivation(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Используйте /start")
        return
    
    motivations = {
        1: ["💡 Осознание проблемы — это уже 50% пути к её решению!", "🌟 Вы сделали первый шаг — это самое сложное!"],
        2: ["💪 Вы уже на уровне выше! Продолжайте!", "🎯 Каждый закрытый долг — это ваша победа!"],
        3: ["🎉 Долги тают на глазах! Осталось совсем немного!", "💰 Ваша подушка растёт — это ваша защита!"],
        4: ["🚀 Вы перешли от выживания к росту!", "📈 Ваши деньги теперь работают, пока вы спите!"],
        5: ["👑 Вы в топ-5% по финансовой грамотности!", "💰 Пассивный доход растёт — скоро полная свобода!"],
        6: ["👑 ВЫ СДЕЛАЛИ ЭТО! Полная финансовая свобода!", "🌟 Ваш путь — вдохновение для тысяч!"]
    }
    
    import random
    level = user['current_level']
    motivation = random.choice(motivations.get(level, motivations[1]))
    
    await message.answer(motivation)

@router.message(Command("progress"))
async def cmd_progress(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Используйте /start")
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT COUNT(*) FROM transactions WHERE user_id = ?', (user['user_id'],)) as cursor:
            trans_count = (await cursor.fetchone())[0]
        
        async with db.execute('SELECT COUNT(*) FROM debts WHERE user_id = ? AND status = ?', (user['user_id'], 'active')) as cursor:
            debts_count = (await cursor.fetchone())[0]
        
        async with db.execute('SELECT COUNT(*) FROM goals WHERE user_id = ? AND status = ?', (user['user_id'], 'active')) as cursor:
            goals_count = (await cursor.fetchone())[0]
    
    level_data = get_level_data(user['current_level'])
    
    response = f"📊 Ваш прогресс\n\n"
    response += f"Уровень: {level_data['name']}\n"
    response += f"Очки опыта: {user['total_score']}\n\n"
    response += f"📝 Транзакций: {trans_count}\n"
    response += f"💳 Активных долгов: {debts_count}\n"
    response += f"🎯 Активных целей: {goals_count}\n\n"
    response += "Продолжайте в том же духе! 💪"
    
    await message.answer(response)

# ==================== MAIN ====================
async def main():
    await init_db()
    dp.include_router(router)
    logger.info("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
