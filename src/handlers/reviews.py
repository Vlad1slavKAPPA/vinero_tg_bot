from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
from create_bot import db_connector
from keyboards.all_kb import review_kb, main_kb
from create_bot import bot
from messaging_exception.messaging import send_long_message
from aiogram.exceptions import TelegramBadRequest

reviews_router = Router()

class Reviews(StatesGroup):
    review_info = State()

@reviews_router.message(F.text == "📖 Назад в главное меню")
async def show_user_kb(message = Message):
    await message.answer(
                "Главное меню",
                reply_markup=main_kb(message.from_user.id)
            )

@reviews_router.message(F.text == "📝 Отзывы клиентов")
async def open_kb(message: Message):
    await message.answer("Выберите действие:", reply_markup=review_kb())

@reviews_router.message(F.text == "📝 Оставить отзыв")
async def start_review(message: Message, state: FSMContext):
    await message.answer("Чтобы оставить отзыв напишите его следующим сообщением.", reply_markup=None)
    await state.set_state(Reviews.review_info)

@reviews_router.message(Reviews.review_info)
async def add_review(message: Message, state: FSMContext):
    info = {
        'id_user': message.from_user.id,
        'id_chat': message.chat.id,
        'id_message': message.message_id,
        'datetime': datetime.now(),
        'title': message.text[:10] + "..."
    }
    await state.update_data(review_info = info)

    query = "INSERT INTO reviews (user_id, id_chat, id_message, datetime, title, check_in) VALUES (:id_user, :id_chat, :id_message, :datetime, :title, false)"
    try:
        await db_connector.execute_query(query, info)
        await message.answer("✅ Спасибо за ваш отзыв!", reply_markup=review_kb())
        await state.clear()
    except Exception as e:
        await state.clear()
        print(f">>>>>>>>>>>>>>>> ОШИБКА: {e}")
        try:
            await send_long_message(
                f"Exception reviews.py (line - 54) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}"
            )
        except Exception as log_err:
            print(f"‼ Ошибка при отправке в канал логов: {log_err}")
        
        # Это сообщение точно должно дойти до пользователя
        try:
            await message.answer("❌ Ошибка при отправке отзыва! Попробуйте позже.")
        except Exception as user_err:
            print(f"‼ Ошибка при ответе пользователю: {user_err}")
        

@reviews_router.message(F.text == "📁 Мои отзывы")
async def looking_reviews(message: Message):
    await send_reviews_list(message = message, user_id = message.from_user.id, page = 0)

async def send_reviews_list(message: Message | CallbackQuery, user_id: int, page: int):
    try:
        if isinstance(message, CallbackQuery):
            send_fn = message.message.edit_text
        else:
            send_fn = message.answer

        limit = 6  # берём на один больше, чтобы понять, есть ли следующая страница
        offset = page * 5
        query = """
            SELECT id, id_chat, id_message, datetime, title 
            FROM reviews 
            WHERE user_id = :id 
            ORDER BY datetime DESC
            LIMIT :limit OFFSET :offset
        """
        params = {"id": user_id, "limit": limit, "offset": offset}

        result = await db_connector.execute_query(query, params)
        rows = result.fetchall()
        reviews = rows[:5]  # показываем максимум 5
        has_next_page = len(rows) > 5

        if not reviews:
            await send_fn("Отзывы не найдены.")
            return

        builder = InlineKeyboardBuilder()
        for review in reviews:
            label = f"{review.datetime.strftime('%d.%m %H:%M')} - {review.title}"
            builder.button(text=label, callback_data=f"review_detail_{review.id}_{page}")

        # Кнопки навигации
        if has_next_page:
            builder.button(text="➡️ Далее", callback_data=f"review_page_{page+1}")
        if page > 0:
            builder.button(text="⬅️ Назад", callback_data=f"review_page_{page-1}")

        builder.adjust(1)
        await send_fn("Ваши отзывы:", reply_markup=builder.as_markup())
    
    except Exception as e:
        await send_long_message(f"Exception reviews.py ( line - 112 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")


@reviews_router.callback_query(F.data.startswith("review_page_"))
async def paginate_orders(callback: CallbackQuery):
    parts = callback.data.split("_")
    page = int(parts[2])
    await send_reviews_list(callback, callback.from_user.id, page)

@reviews_router.callback_query(F.data.startswith("review_detail_"))
async def show_order_detail(callback: CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split("_")
        # "review", "detail", "{review_id}", "{page}"
        if len(parts) < 4:
            await callback.answer("Некорректные данные кнопки.", show_alert=True)
            await send_long_message(f"Exception reviews.py ( line - 128 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}")
            return

        _, _, review_id, page = parts

        query_review = """
        SELECT
            id,
            user_id,
            id_chat,
            id_message,
            datetime,
            title
        FROM reviews
        WHERE id = :id
        """
        result = await db_connector.execute_query(query_review, {"id": int(review_id)})
        records = result.mappings().all()

        if not records:
            await callback.answer("Отзыв не найден", show_alert=True)
            return

        # Берём общую информацию из первой строки
        first = records[0]

        text = (
            f"📅 Дата: {first['datetime'].strftime('%d.%m.%Y')}\n"
            f"🕒 Время: {first['datetime'].strftime('%H:%M')}\n\n"
        )
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙Назад к отзывам", callback_data=f"review_page_{page}")

        await callback.message.edit_text(text, reply_markup=builder.as_markup())

        await bot.forward_message(
            chat_id=callback.message.chat.id,
            from_chat_id=first['id_chat'],
            message_id=first['id_message']
        )
    except Exception as e:
        await send_long_message(f"Exception reviews.py ( line - 169 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
    
@reviews_router.message(F.text == "💬 Отзывы наших клиентов")
async def link_to_all_reviews(message: Message, state: FSMContext):
    await message.answer("Тут наши клиенты оставляют свои отзывы: https://t.me/+GuM0A679aiU1YmEy", reply_markup=review_kb())

