from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
from create_bot import db_connector
from create_bot import bot
from keyboards.all_kb import main_kb, admin_kb
from aiogram.exceptions import DetailedAiogramError
from messaging_exception.messaging import send_long_message

apanel_router = Router()

class Admin_Panel(StatesGroup): 
    info = State()

    phone_new_emp = State()
    start_time_new_emp = State()
    end_time_new_emp = State()
    name_new_emp = State()
    role_new_emp = State()

    confirming_data_new_emp = State()

    full_data_emp = State()
    
    confirming_add_emp = State()

    name_edit_old = State()
    role_edit_old = State()
    start_time_edit_old = State()
    end_time_edit_old = State()

    full_data_serv = State()

    sname_add = State()
    sprice_add = State()
    sduration_add = State()
    data_full_add = State()

    sname_edit_old = State()
    sprice_edit_old = State()
    sduration_edit_old = State()
    ssex_edit_old = State()

    rname = State()
    rdate = State()

@apanel_router.message(F.text == "Открыть меню пользователей")
async def show_user_kb(message: Message):
    await message.answer(
                f"Здравствуйте!\n"
                "Вас приветствует студия красоты Barbero!\n"
                "Что желаете сделать?",
                reply_markup=main_kb(message.from_user.id)
            )
    
@apanel_router.message(F.text == "🛠 Выдать права администратора")
async def add_status_admin(message: Message):
    user_id = message.from_user.id
    #check_status = await db_connector.execute_query("SELECT admin_status FROM users WHERE id = :id", {"id": int(user_id)})
    if user_id in db_connector.admins_cache: 
        try:
            query = "UPDATE users SET admin_status = :admin_status WHERE id = :id"
            await db_connector.execute_query(query, {"id": int(user_id), "admin_status": False})
            await db_connector.load_admins()
        except DetailedAiogramError as e:
            await send_long_message(f"Excpetion admin_panel.py 67 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
            await message.answer("❌ При снятии прав пользователя произошла ошибка!")
            return
        await message.answer(f"✅ Права администратора сняты!", reply_markup=main_kb(message.from_user.id))
    else:
        try:
            query = "UPDATE users SET admin_status = :admin_status WHERE id = :id"
            await db_connector.execute_query(query, {"id": int(user_id), "admin_status": True})
            await db_connector.load_admins()
        except DetailedAiogramError as e:
            await send_long_message(f"Excpetion admin_panel.py 67 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
            await message.answer("❌ При выдаче прав администратора произошла ошибка!")
            return
        await message.answer(f"✅ Вы теперь администратор!", reply_markup=main_kb(message.from_user.id))

    
@apanel_router.message(F.text == "⚙️ Админ-панель")
async def show_user_kb(message: Message):
    await message.answer("Здравствуйте администратор!\n", reply_markup=admin_kb(message.from_user.id))

@apanel_router.message(F.text == "Сотрудники")
async def show_list_emp(message: Message, state: FSMContext):
    await list_emp(message, page = 0, state = state)
    
async def list_emp(message: Message | CallbackQuery, page: int, state: FSMContext):
    if isinstance(message, CallbackQuery):
        send_fn = message.message.edit_text
    else:
        send_fn = message.answer

    query = """
        SELECT 
        e.user_id AS id, 
        e.name, 
        r.name AS role_name,
        u.phone
        FROM employees e
        JOIN users u ON e.user_id = u.id
        JOIN roles r ON e.role_id = r.id
        LIMIT 6 OFFSET :offset
    """
    params = {"offset": page * 5}

    result = await db_connector.execute_query(query, params)
    rows = result.mappings().all()
    employees = rows[:5]
    await state.update_data(full_data_emp = employees)
    has_next_page = len(rows) > 5
    
    if not employees:
        builder.button(text="➕ Добавить сотрудника", callback_data=f"employee_add")
        await message.answer("Сотрудники не найдены.", reply_markup=builder.as_markup())
        return
    
    builder = InlineKeyboardBuilder()
    for employee in employees:
        label = f"{employee['name']} - {employee['phone']} - {employee['role_name']}"
        builder.button(text=label, callback_data=f"employee_detail_{employee['id']}_{page}")
        

    builder.button(text="➕ Добавить сотрудника", callback_data=f"employee_add")

    if page > 0:
        builder.button(text="⬅️ Назад", callback_data=f"employee_page_{page-1}")
    if has_next_page:
        builder.button(text="➡️ Далее", callback_data=f"employee_page_{page+1}")
    
    builder.adjust(1)

    await send_fn("Список сотрудников:", reply_markup=builder.as_markup())

@apanel_router.callback_query(F.data.startswith("employee_page_"))
async def paginate_emp(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    page = int(parts[2])
    await list_emp(callback, page, state)

@apanel_router.callback_query(F.text == "👨‍🔧 Выдать права сотрудника")
async def start_add_employee_text(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(text="Отправьте номер телефона от аккаунта будущего сотрудника.\n\nЭтот аккаунт сотрудника должен быть зарегистрирован в боте!\n\nПример: +79528129191")
    await state.set_state(Admin_Panel.phone_new_emp)

@apanel_router.callback_query(F.data.startswith("employee_add"))
async def start_add_employee(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(text="Отправьте номер телефона от аккаунта будущего сотрудника.\n\nЭтот аккаунт сотрудника должен быть зарегистрирован в боте!\n\nПример: +79528129191")
    await state.set_state(Admin_Panel.phone_new_emp)

@apanel_router.message(Admin_Panel.phone_new_emp)
async def find_user(message: Message, state: FSMContext):
    phone = message.text.strip()
    if phone[1:].isdigit() and 10 <= len(phone) <= 15:
        if phone.startswith("+"): phone = phone[1:]
        print(f"номер телефона в запросе{phone}")
        request = await db_connector.execute_query('SELECT id, name, gender, phone FROM users WHERE phone = :phone', {'phone': phone})
        result = request.mappings().fetchone()
        print(result)
        if result is not None and result['phone'] == phone:
            request = await db_connector.execute_query("SELECT user_id, name FROM employees WHERE user_id = :id", {"id": result["id"]})
            result_check_old_emp = request.mappings().fetchone()
            if not result_check_old_emp:
                await state.update_data({"full_data_emp": dict(result)})
                await state.update_data(phone_new_emp = phone)
                await message.answer("Напишите имя мастера которое будет видно пользователям.")
                await state.set_state(Admin_Panel.name_new_emp)
            else:
                await message.answer("❗ К данному аккаунту уже привязан сотрудник. \n\nПопробуйте еще раз.")
        else:
            await message.answer("❗ Пользователь в базе данных не найден, введите номер телефона уже зарегистированного пользователя. \n\nПопробуйте еще раз.")
    else:
        await message.answer("❗ Введите корректный номер телефона. Пример: +79528125252\n\nПопробуйте еще раз.")

    
    

@apanel_router.message(Admin_Panel.name_new_emp)
async def name_new_employee(message: Message, state: FSMContext):
    await state.update_data(name_new_emp = message.text)
    await message.answer("Напишите во сколько будет начинаться смена у этого сотрудника. Пример: 10:00")
    await state.set_state(Admin_Panel.start_time_new_emp)

@apanel_router.message(Admin_Panel.start_time_new_emp)
async def name_new_employee(message: Message, state: FSMContext):
    user_input = message.text.strip()
    try:
        # Парсим в datetime и получаем объект time
        parsed_time = datetime.strptime(user_input, "%H:%M").time()
        # Например: сохраняем в state или сразу в БД
        await state.update_data(start_time_new_emp = parsed_time)

    except DetailedAiogramError as e:
        await send_long_message(f"Excpetion admin_panel.py 168 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        await message.answer("❌ Неверный формат времени. Введите, например: 10:00")

    await message.answer("Напишите во сколько будет заканчиваться смена у этого сотрудника. Пример: 19:00")
    await state.set_state(Admin_Panel.end_time_new_emp)

@apanel_router.message(Admin_Panel.end_time_new_emp)
async def name_new_employee(message: Message, state: FSMContext):
    user_input = message.text.strip()
    try:
        # Парсим в datetime и получаем объект time
        parsed_time = datetime.strptime(user_input, "%H:%M").time()
        # Например: сохраняем в state или сразу в БД
        await state.update_data(end_time_new_emp = parsed_time)
    except DetailedAiogramError as e:
        await send_long_message(f"Excpetion admin_panel.py 183 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        await message.answer("❌ Неверный формат времени. Введите, например: 10:00")

    query = "SELECT id, name FROM roles"
    result = await db_connector.execute_query(query)
    roles = result.fetchall()

    builder = InlineKeyboardBuilder()
    for role in roles:
        builder.button(text=role.name, callback_data=f"employee_role_{role.id}_{role.name}")
    builder.adjust(1)

    await message.answer("Выберите роль сотрудника", reply_markup=builder.as_markup())

@apanel_router.callback_query(F.data.startswith("employee_role_"))
async def role_new_employee(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    parts = callback.data.split("_")
    await state.update_data({"role_new_emp": {'id': parts[2], 'r_name': parts[3]}})
    await show_summary(state, callback.message)
    
async def show_summary(state: FSMContext, message: Message):
    data = await state.get_data()

    new_name = data.get("name_new_emp")
    new_phone = data.get("phone_new_emp")
    new_start_time = data.get("start_time_new_emp")
    new_end_time = data.get("end_time_new_emp")
    user_data = data.get("full_data_emp")
    new_role_emp = data.get("role_new_emp")  # ожидается кортеж (id, name)

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_add_emp")
    builder.button(text="❌ Отменить", callback_data="cancel_add_emp")
    builder.adjust(1)


    await message.answer(
    text=(
        f"Имя, указанное при регистрации: {user_data['name']}\n"
        f"Номер телефона: +{new_phone}\n\n"
        f"<a href='tg://user?id={user_data['id']}'>Перейти к пользователю</a>\n\n"
        f"Имя для пользователей: {new_name}\n"
        f"Должность: {new_role_emp['r_name']}\n"
        f"Начало смены: {new_start_time.strftime('%H:%M')}\n"
        f"Конец смены: {new_end_time.strftime('%H:%M')}"
    ),
    parse_mode="HTML",
    reply_markup=builder.as_markup()
)

    await state.update_data({
        "confirming_add_emp": {
            'phone': new_phone,
            'id_role': new_role_emp['id'],
            'name': new_name,
            'start_time': new_start_time,
            'end_time': new_end_time,
            'user_id': user_data['id']
        }
    })

@apanel_router.callback_query(F.data.startswith("cancel_add_emp"))
async def cancel_new_emp(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(text="❌ Сотрудник  не создан.")

@apanel_router.callback_query(F.data.startswith("confirm_add_emp"))
async def save_new_emp(callback: CallbackQuery, state: FSMContext):
    query = """
    INSERT INTO employees (start_time, end_time, name, role_id, user_id)
    VALUES (:start_time, :end_time, :name, :role_id, :user_id)
    """
    data = await state.get_data()
    confirming = data.get("confirming_add_emp")
    try:
        await db_connector.execute_query(query,{'role_id': int(confirming['id_role']), 'name': confirming['name'], 'start_time': confirming['start_time'], 'end_time': confirming['end_time'], 'user_id': confirming['user_id']})
        
        await callback.answer()
        
    except DetailedAiogramError as e:
        await callback.answer()
        await callback.message.answer(f"❗ Произошла ошибка при сохранении.")
        await send_long_message(f"Excpetion admin_panel.py 266 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
    await bot.send_message(chat_id = confirming['user_id'], text=f"✅ Ваш аккаунт был прикреплен к сотруднику с именем {confirming['name']}.")
    print(f"Ваш аккаунт был прикреплен к сотруднику с именем {confirming['name']}")
    await callback.message.answer(text="✅ Сотрудник создан.")
    await db_connector.load_employees()
    await state.clear()
    await list_emp(callback, 0, state)

@apanel_router.callback_query(F.data.startswith("employee_detail_"))
async def show_employee_detail(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    # "employee", "detail", "{user_id}", "{page}"
    if len(parts) < 4:
        await callback.answer("Некорректные данные кнопки.", show_alert=True)
        return
    
    employee_id = parts[2]
    page = parts[3]

    query = """
    SELECT  
        e.name,
        e.start_time,
        e.end_time,
        e.user_id,
        r.name AS role_name,
        r.id AS role_id,
        u.phone
    FROM employees e
    JOIN roles r ON e.role_id = r.id
    JOIN users u ON e.user_id = u.id
    WHERE e.user_id = :employee_id
    """
    params = {"employee_id": int(employee_id)}
    result = await db_connector.execute_query(query, params) 

    request = result.mappings().all()

    if not request:
        await callback.answer("Сотрудник не найден!", show_alert=True)
        
    employees = request[0]

    detail_text = (
        f"💇‍♂️ Имя мастера: {employees['name']}\n"
        f"Должность мастера: {employees['role_name']}\n\n"
        f"🕒 Начало рабочего дня: {employees['start_time'].strftime('%H:%M')}\n"
        f"🕒 Конец рабочего дня: {employees['end_time'].strftime('%H:%M')}\n\n"
        f"📋 Номер телефона:\n+{employees['phone']}\n\n"
        f"<a href='tg://user?id={employee_id}'>Перейти к пользователю</a>\n\n"
    )
    
    await state.update_data({
        "info": {
            'name': employees['name'],
            'role_id': employees['role_id'],
            'role_name': employees['role_name'],
            'start_time': employees['start_time'],
            'end_time': employees['end_time'],
            'phone': employees['phone'],
            'user_id': employee_id
        }
    })

    builder = InlineKeyboardBuilder()
    builder.button(
        text="✏ Изменить сотрудника",
        callback_data=f"edit_employee_{employee_id}_{page}"
    )
    builder.button(
        text="❌ Удалить сотрудника",
        callback_data=f"delete_employee_{employee_id}_{employees['name']}"
    )
    builder.button(
        text="🔙 Назад к сотрудникам",
        callback_data=f"employee_page_{page}"
    )
    builder.adjust(2)

    await callback.message.edit_text(detail_text, reply_markup=builder.as_markup(), parse_mode="HTML")


@apanel_router.callback_query(F.data.startswith("delete_employee_"))
async def delete_employee(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    user_id = parts[2]
    name = parts[3]
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Подтвердить удаление",
        callback_data=f"complete_delete_{user_id}"
    )
    builder.button(
        text="❌ Отменить удаление",
        callback_data=f"employee_detail_{user_id}_{0}"
    )

    await callback.message.edit_text(f"Вы уверены что хотите удалить сотрудника с именем \"{name}\"?", reply_markup=builder.as_markup())

@apanel_router.callback_query(F.data.startswith("complete_delete_"))
async def comfirm_delete_employee(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    user_id = int(parts[2])

    try:
        query = "DELETE FROM employees WHERE user_id = :user_id"
        await db_connector.execute_query(query, {"user_id": user_id})
        await callback.message.edit_text("✅ Сотрудник успешно удален!")
        await db_connector.load_employees()
    except DetailedAiogramError as e:
        print(f"Ошибка при удалении сотрудника: {e}")
        await callback.message.edit_text("❌ При удалении данных произошла ошибка в БД!")
        await send_long_message(f"Excpetion admin_panel.py 377 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        return
    

    await show_list_emp(callback.message, state)

@apanel_router.callback_query(F.data.startswith("edit_employee_"))
async def show_employee_edit(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    user_id = parts[2]
    page = parts[3]

    data = await state.get_data()
    employees = data.get("info", {})
    # Получаем информацию
    if not employees:
        await callback.answer("❌ Сотрудник не найден.", show_alert=True)
        return

    detail_text = (
        f"💇‍♂️ Имя мастера: {employees['name']}\n"
        f"Должность мастера: {employees['role_name']}\n\n"
        f"🕒 Начало рабочего дня: {employees['start_time'].strftime('%H:%M')}\n"
        f"🕒 Конец рабочего дня: {employees['end_time'].strftime('%H:%M')}\n\n"
        f"📋 Номер телефона:\n+{employees['phone']}\n\n"
        f"<a href='tg://user?id={data['user_id']}'>Перейти к пользователю</a>\n\n"
    )

    # Клавиатура
    builder = InlineKeyboardBuilder()
    builder.button(text="✏ Изменить имя", callback_data=f"edit_name_{user_id}")
    builder.button(text="🛠 Изменить роль", callback_data=f"edit_role_{user_id}")
    builder.button(text="✏ Изменить начало рабочего дня", callback_data=f"edit_start_time_{user_id}")
    builder.button(text="🛠 Изменить конец рабочего дня", callback_data=f"edit_end_time_{user_id}")
    builder.button(text="🔙 Назад", callback_data=f"employee_detail_{employees['user_id']}_{page}")
    builder.adjust(2)

    # Безопасное редактирование текста
    try:
        await callback.message.edit_text(detail_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except DetailedAiogramError as e:
        await send_long_message(f"Excpetion admin_panel.py 418 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        if "message is not modified" not in str(e):
            raise


# Хендлер изменения имени
@apanel_router.callback_query(F.data.startswith("edit_name_"))
async def edit_employee_name(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    user_id = parts[2]
    await callback.message.answer(f"Введите новое имя которое будет видно для пользователем.")
    await callback.answer()
    await state.set_state(Admin_Panel.name_edit_old)

@apanel_router.message(Admin_Panel.name_edit_old)
async def save_editing_name(message: Message, state: FSMContext):
    new_name = message.text.strip()
    info =  await state.get_data()
    data = info.get("info", {})
    user_id = data["user_id"]
    data["name"] = new_name
    await state.update_data(info=data)

    try:
        query = "UPDATE employees SET name = :name WHERE user_id = :user_id"
        await db_connector.execute_query(query, {"name": new_name, "user_id": int(user_id)})
    except DetailedAiogramError as e:
        #ошибка при редактировании
        await send_long_message(f"Excpetion admin_panel.py 446 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        await message.answer("❌ При сохранении данные произошла ошибка в БД!")
        return
    await message.answer(f"✅ Имя пользователя успешно изменено. Новое имя пользователя: {new_name}")

    detail_text = (
        f"💇‍♂️ Имя мастера: {data['name']}\n"
        f"Должность мастера: {data['role_name']}\n\n"
        f"🕒 Начало рабочего дня: {data['start_time'].strftime('%H:%M')}\n"
        f"🕒 Конец рабочего дня: {data['end_time'].strftime('%H:%M')}\n\n"
        f"📋 Номер телефона:\n+{data['phone']}\n\n"
        f"<a href='tg://user?id={data['user_id']}'>Перейти к пользователю</a>\n\n"
    )

    # Клавиатура
    builder = InlineKeyboardBuilder()
    builder.button(text="✏ Изменить имя", callback_data=f"edit_name_{user_id}")
    builder.button(text="🛠 Изменить роль", callback_data=f"edit_role_{user_id}")
    builder.button(text="✏ Изменить начало рабочего дня", callback_data=f"edit_start_time_{user_id}")
    builder.button(text="🛠 Изменить конец рабочего дня", callback_data=f"edit_end_time_{user_id}")
    builder.button(text="🔙 Назад", callback_data=f"employee_detail_{data['user_id']}_{0}")
    builder.adjust(2)

    try:
        await message.answer(detail_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except DetailedAiogramError as e:
        await send_long_message(f"Excpetion admin_panel.py 472 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        if "message is not modified" not in str(e):
            raise



# Хендлер изменения роли
@apanel_router.callback_query(F.data.startswith("edit_role_"))
async def edit_employee_role(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    user_id = parts[2]
    print(f"user_id:{user_id}")
    query = "SELECT id, name FROM roles"
    result = await db_connector.execute_query(query)
    roles = result.fetchall()

    builder = InlineKeyboardBuilder()
    for role in roles:
        builder.button(text=role.name, callback_data=f"save_employee_role_{role.id}_{user_id}_{role.name}")
    builder.adjust(1)

    await callback.message.answer(f"Выберите новую должность для сотрудника с ID {user_id}", reply_markup=builder.as_markup())
    await callback.answer()

@apanel_router.callback_query(F.data.startswith("save_employee_role_"))
async def role_new_employee(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    parts = callback.data.split("_")
    role_id = int(parts[3])
    user_id = int(parts[4])
    role_name = parts[5]
    info = await state.get_data()
    data = info.get("info", {})
    
    
    try:
        query = "UPDATE employees SET role_id = :role_id WHERE user_id = :user_id"
        await db_connector.execute_query(query, {"role_id":role_id, "user_id": user_id})
        data["role_name"] = role_name
        data["role_id"] = role_id
        await state.update_data(info=data)
    except DetailedAiogramError as e:
        await send_long_message(f"Excpetion admin_panel.py 514 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        print(f"Ошибка при редактировании имени у сотрудика: {e}")
        await callback.message.answer("❌ При сохранении данные произршла ошибка в БД!")
        return
    await callback.message.answer(f"✅ Должность пользователя успешно изменено.")

    detail_text = (
        f"💇‍♂️ Имя мастера: {data['name']}\n"
        f"Должность мастера: {data['role_name']}\n\n"
        f"🕒 Начало рабочего дня: {data['start_time'].strftime('%H:%M')}\n"
        f"🕒 Конец рабочего дня: {data['end_time'].strftime('%H:%M')}\n\n"
        f"📋 Номер телефона:\n+{data['phone']}\n\n"
        f"<a href='tg://user?id={data['user_id']}'>Перейти к пользователю</a>\n\n"
    )

    # Клавиатура
    builder = InlineKeyboardBuilder()
    builder.button(text="✏ Изменить имя", callback_data=f"edit_name_{user_id}")
    builder.button(text="🛠 Изменить роль", callback_data=f"edit_role_{user_id}")
    builder.button(text="✏ Изменить начало рабочего дня", callback_data=f"edit_start_time_{user_id}")
    builder.button(text="🛠 Изменить конец рабочего дня", callback_data=f"edit_end_time_{user_id}")
    builder.button(text="🔙 Назад", callback_data=f"employee_detail_{data['user_id']}_{0}")
    builder.adjust(2)
    try:
        await callback.message.answer(detail_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except DetailedAiogramError as e:
        await send_long_message(f"Excpetion admin_panel.py 540 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        if "message is not modified" not in str(e):
            raise



@apanel_router.callback_query(F.data.startswith("edit_start_time_"))
async def edit_employee_start_time(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    user_id = parts[3]
    await callback.message.answer(f"Введите во сколько будет начинаться рабочий день.")
    await callback.answer()
    await state.set_state(Admin_Panel.start_time_edit_old)

@apanel_router.message(Admin_Panel.start_time_edit_old)
async def save_editing_start_time(message: Message, state: FSMContext):
    new_time = message.text.strip()
    info =  await state.get_data()
    data = info.get("info", {})
    user_id = data["user_id"]
    data["start_time"] = new_time
    await state.update_data(info=data)


    try:
        # Парсим в datetime и получаем объект time
        parsed_time = datetime.strptime(new_time, "%H:%M").time()
        # Например: сохраняем в state или сразу в БД
        data["start_time"] = parsed_time
        await state.update_data(info=data)
        query = "UPDATE employees SET start_time = :time WHERE user_id = :user_id"
        if not await db_connector.execute_query(query, {"time": parsed_time, "user_id": int(user_id)}): await message.answer("❌ При сохранении данные произршла ошибка в БД!")

    except DetailedAiogramError as e:
        await send_long_message(f"Excpetion admin_panel.py 574 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        await message.answer("❌ Неверный формат времени. Введите, например: 10:00")
    await message.answer(f"✅ Начало рабочего дня измено.")




    detail_text = (
        f"💇‍♂️ Имя мастера: {data['name']}\n"
        f"Должность мастера: {data['role_name']}\n\n"
        f"🕒 Начало рабочего дня: {parsed_time}\n"
        f"🕒 Конец рабочего дня: {data['end_time'].strftime('%H:%M')}\n\n"
        f"📋 Номер телефона:\n+{data['phone']}\n\n"
        f"<a href='tg://user?id={data['user_id']}'>Перейти к пользователю</a>\n\n"
    )

    # Клавиатура
    builder = InlineKeyboardBuilder()
    builder.button(text="✏ Изменить имя", callback_data=f"edit_name_{user_id}")
    builder.button(text="🛠 Изменить роль", callback_data=f"edit_role_{user_id}")
    builder.button(text="✏ Изменить начало рабочего дня", callback_data=f"edit_start_time_{user_id}")
    builder.button(text="🛠 Изменить конец рабочего дня", callback_data=f"edit_end_time_{user_id}")
    builder.button(text="🔙 Назад", callback_data=f"employee_detail_{data['user_id']}_{0}")
    builder.adjust(2)

    try:
        await message.answer(detail_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except DetailedAiogramError as e:
        await send_long_message(f"Excpetion admin_panel.py 602 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        if "message is not modified" not in str(e):
            raise


@apanel_router.callback_query(F.data.startswith("edit_end_time_"))
async def edit_employee_start_time(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    user_id = parts[3]
    await callback.message.answer(f"Введите во сколько будет заканчиваться рабочий день.")
    await callback.answer()
    await state.set_state(Admin_Panel.end_time_edit_old)

@apanel_router.message(Admin_Panel.end_time_edit_old)
async def save_editing_start_time(message: Message, state: FSMContext):
    new_time = message.text.strip()
    info =  await state.get_data()
    data = info.get("info", {})
    user_id = data["user_id"]
    await state.update_data(info=data)


    try:
        # Парсим в datetime и получаем объект time
        parsed_time = datetime.strptime(new_time, "%H:%M").time()
        # Например: сохраняем в state или сразу в БД
        data["end_time"] = parsed_time
        await state.update_data(info=data)
        query = "UPDATE employees SET end_time = :time WHERE user_id = :user_id"
        if not await db_connector.execute_query(query, {"time": parsed_time, "user_id": int(user_id)}): await message.answer("❌ При сохранении данные произошла ошибка в БД!")

    except DetailedAiogramError as e:
        await send_long_message(f"Excpetion admin_panel.py 634 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        await message.answer("❌ Неверный формат времени. Введите, например: 10:00")
    await message.answer(f"✅ Конец рабочего дня изменен.")
    



    detail_text = (
        f"💇‍♂️ Имя мастера: {data['name']}\n"
        f"Должность мастера: {data['role_name']}\n\n"
        f"🕒 Начало рабочего дня: {parsed_time}\n"
        f"🕒 Конец рабочего дня: {data['end_time'].strftime('%H:%M')}\n\n"
        f"📋 Номер телефона:\n+{data['phone']}\n\n"
        f"<a href='tg://user?id={data['user_id']}'>Перейти к пользователю</a>\n\n"
    )

    # Клавиатура
    builder = InlineKeyboardBuilder()
    builder.button(text="✏ Изменить имя", callback_data=f"edit_name_{user_id}")
    builder.button(text="🛠 Изменить роль", callback_data=f"edit_role_{user_id}")
    builder.button(text="✏  Изменить начало рабочего дня", callback_data=f"edit_start_time_{user_id}")
    builder.button(text="🛠 Изменить конец рабочего дня", callback_data=f"edit_end_time_{user_id}")
    builder.button(text="🔙 Назад", callback_data=f"employee_detail_{data['user_id']}_{0}")
    builder.adjust(2)

    try:
        await message.answer(detail_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except DetailedAiogramError as e:
        await send_long_message(f"Excpetion admin_panel.py 662 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        if "message is not modified" not in str(e):
            raise


async def show_list_services(message: Message | CallbackQuery, page: int, state: FSMContext):
    if isinstance(message, CallbackQuery):
        send_fn = message.message.edit_text
    else:
        send_fn = message.answer

    query = """
        SELECT
        id, 
        name,
        price,
        duration,
        sex
        FROM services
        ORDER BY id
        LIMIT 6 OFFSET :offset
    """

    params = {"offset": page * 5}

    result = await db_connector.execute_query(query, params)
    rows = result.mappings().all()
    services = [dict(r) for r in rows[:5]]
    await state.update_data(full_data_serv = services)
    has_next_page = len(rows) > 5

    if not services:
        await send_fn("Услуги не найдены.")
        return
    
    builder = InlineKeyboardBuilder()
    for service in services:
        name = service['name'].split("_")
        label = f"{name[-1] if len(name) == 1 else name[-2] + ' - ' + name[-1]}"
        
        builder.button(text=label, callback_data=f"apanel_service_detail_{int(service['id'])}_{page}")
        print(">>>", service['id'], type(service['id']), page, type(page))
        print("callback_data:", f"apanel_service_detail_{service['id']}_{page}")

        

    if has_next_page:
        builder.button(text="➡️ Далее", callback_data=f"apanel_service_page_{page+1}")
    if page > 0:
        builder.button(text="⬅️ Назад", callback_data=f"apanel_service_page_{page-1}")

    builder.button(text="➕ Добавить услугу", callback_data="apanel_service_add")

    
    builder.adjust(1)

    await send_fn("Список услуг:", reply_markup=builder.as_markup())


@apanel_router.message(F.text == "Услуги")
async def edit_employee_start_time(message: Message, state: FSMContext):
    await show_list_services(message, 0, state)

@apanel_router.callback_query(F.data.startswith("apanel_service_page_"))
async def paginate_emp(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split("_")[-1])
    await show_list_services(callback, page, state)


async def show_service_detail(service_id: int, page: int, send_fn, state: FSMContext):
    data = await state.get_data()
    all_services = data.get("full_data_serv", [])
    service_data = next((s for s in all_services if s["id"] == service_id), None)

    if not service_data:
        await send_fn("❌ Услуга не найдена.")
        return

    sex = "Для всех"
    if service_data['sex'] == 2:
        sex = "Мужской"
    else:
        sex = "Женский"
    h, m = divmod(service_data['duration'], 60)
    duration = f"{f'{h} ч ' if h else ''}{m} мин" if m or h == 0 else f"{h} ч"
    detail_text = (
        f"Название услуги: {service_data['name']}\n\n"
        f"Цена усулги: {service_data['price']} руб.\n"
        f"Длительность услуги: {duration}мин\n\n"
        f"Пол: {sex}"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="✏ Изменить название", callback_data=f"apanel_service_edit_name_{service_data['id']}")
    builder.button(text="✏ Изменить стоимость", callback_data=f"apanel_service_edit_price_{service_data['id']}")
    builder.button(text="✏ Изменить длительность", callback_data=f"apanel_service_edit_duration_{service_data['id']}")
    builder.button(text="✏ Изменить пол услуги", callback_data=f"apanel_service_edit_sex_{service_data['id']}")
    builder.button(
        text="❌ Удалить услугу",
        callback_data=f"apanel_service_delete_{service_data['id']}_{page}"
    )
    builder.button(text="⬅️ Назад к услугам", callback_data=f"apanel_service_page_{page}")
    builder.adjust(2)

    await send_fn(detail_text, reply_markup=builder.as_markup())


async def update_service_in_state(state: FSMContext, service_id: int, **kwargs):
    """
    Обновляет данные конкретной услуги в state по её id.
    kwargs — это поля, которые нужно изменить, например name="Новое имя"
    """
    data = await state.get_data()
    services = data.get("full_data_serv", [])

    for service in services:
        if service["id"] == service_id:
            service.update(kwargs)  # обновляем поля
            break

    # сохраняем обратно
    await state.update_data(full_data_serv=services)

@apanel_router.callback_query(F.data.startswith("apanel_service_detail_"))
async def service_detail_callback(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    service_id = int(parts[3])
    page = int(parts[4])
    await show_service_detail(service_id, page, callback.message.edit_text, state)

@apanel_router.callback_query(F.data.startswith("apanel_service_delete_"))
async def delete_employee(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    service_id = parts[3]
    page = int(parts[4])
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Подтвердить удаление",
        callback_data=f"apanel_complete_service_delete_{service_id}_{page}"
    )
    builder.button(
        text="❌ Отменить удаление",
        callback_data=f"apanel_service_detail_{service_id}_{page}"
    )
    await callback.message.edit_text(
        f"Вы уверены что хотите удалить услугу?", 
        reply_markup=builder.as_markup()
    )

@apanel_router.callback_query(F.data.startswith("apanel_complete_service_delete_"))
async def complete_delete(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    service_id = int(parts[4])
    page = int(parts[5])
    try:
        query = "DELETE FROM services WHERE id = :id"
        await db_connector.execute_query(query, {"id": service_id})
    except DetailedAiogramError as e:
        # при удалении
        await send_long_message(f"Excpetion admin_panel.py 820 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        await callback.message.edit_text("❌ При удалении данных произошла ошибка!")
        return
    await callback.message.edit_text("✅ Услуга успешно удалена!")
    await show_list_services(callback, page, state)


@apanel_router.callback_query(F.data.startswith("apanel_service_edit_name_"))
async def edit_name(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("_")[-1])
    await callback.message.answer("Введите новое название для услуги.")
    await state.update_data(sname_edit_old=service_id)
    await state.set_state(Admin_Panel.sname_edit_old)


@apanel_router.message(Admin_Panel.sname_edit_old)
async def paginate_emp(message: Message, state: FSMContext):
    input_text = str(message.text.strip())
    info =  await state.get_data()
    id = info.get("sname_edit_old")

    try:
        query = "UPDATE services SET name = :name WHERE id = :id"
        await db_connector.execute_query(query, {"name": input_text, "id": int(id)})
        await update_service_in_state(state, id, name=input_text)
    except DetailedAiogramError as e:
        await send_long_message(f"Excpetion admin_panel.py 846 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        await message.answer("❌ При сохранении данные произошла ошибка в БД!")
        return
    await message.answer(f"✅ Название услуги изменено.")

    await show_service_detail(id, 0, message.answer, state)


@apanel_router.callback_query(F.data.startswith("apanel_service_edit_price_"))
async def edit_price(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("_")[-1])
    await callback.message.answer("Введите новую цену для услуги.")
    await state.update_data(sprice_edit_old=service_id)
    await state.set_state(Admin_Panel.sprice_edit_old)


@apanel_router.message(Admin_Panel.sprice_edit_old)
async def paginate_emp(message: Message, state: FSMContext):
    input_text = int(message.text.strip())
    info =  await state.get_data()
    id = info.get("sprice_edit_old")

    try:
        query = "UPDATE services SET price = :price WHERE id = :id"
        await db_connector.execute_query(query, {"price": input_text, "id": int(id)})
        await update_service_in_state(state, id, price=input_text)
    except DetailedAiogramError as e:
        await send_long_message(f"Excpetion admin_panel.py 873 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        await message.answer("❌ При сохранении данные произошла ошибка в БД!")
        return
    await message.answer(f"✅ Цена услуги изменена.")

    await show_service_detail(id, 0, message.answer, state)


@apanel_router.callback_query(F.data.startswith("apanel_service_edit_duration_"))
async def edit_duration(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("_")[-1])
    await callback.message.answer("Введите новую длительность услуги.")
    await state.update_data(sduration_edit_old=service_id)
    await state.set_state(Admin_Panel.sduration_edit_old)


@apanel_router.message(Admin_Panel.sduration_edit_old)
async def paginate_emp(message: Message, state: FSMContext):
    input_text = int(message.text.strip())
    info =  await state.get_data()
    id = info.get("sduration_edit_old")

    try:
        query = "UPDATE services SET duration = :duration WHERE id = :id"
        await db_connector.execute_query(query, {"duration": input_text, "id": int(id)})
        await update_service_in_state(state, id, duration=input_text)
    except DetailedAiogramError as e:
        await send_long_message(f"Excpetion admin_panel.py 900 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        await message.answer("❌ При сохранении данные произошла ошибка в БД!")
        return
    await message.answer(f"✅ Длительность услуги изменена.")

    await show_service_detail(id, 0, message.answer, state)


@apanel_router.callback_query(F.data.startswith("apanel_service_edit_sex_"))
async def edit_sex(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("_")[-1])
    builder = InlineKeyboardBuilder()
    builder.button(text="Мужской", callback_data=f"apanel_edit_sex_{2}")
    builder.button(text="Женский", callback_data=f"apanel_edit_sex_{3}")
    builder.button(text="Общий", callback_data=f"apanel_edit_sex_{1}")
    builder.adjust(2)
    await callback.message.answer("Выберите новый пол для услуги", reply_markup=builder.as_markup())
    await state.update_data(ssex_edit_old=service_id)


@apanel_router.callback_query(F.data.startswith("apanel_edit_sex_"))
async def confirm_edit_sex(callback: CallbackQuery, state: FSMContext):
    sex = int(callback.data.split("_")[-1])
    info = await state.get_data()
    service_id = info.get("ssex_edit_old")
    try:
        query = "UPDATE services SET sex = :sex WHERE id = :id"
        await db_connector.execute_query(query, {"sex": sex, "id": service_id})
        await update_service_in_state(state, service_id, sex=sex)
    except DetailedAiogramError as e:
        await send_long_message(f"Excpetion admin_panel.py 930 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        await callback.message.answer("❌ Ошибка при обновлении пола услуги.")
        return
    await callback.message.answer("✅ Пол услуги изменён.")
    await show_service_detail(service_id, 0, callback.message.answer, state)


@apanel_router.callback_query(F.data == "apanel_service_add")
async def add_services(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название для новой услуги.")
    await state.set_state(Admin_Panel.sname_add)

@apanel_router.message(Admin_Panel.sname_add)
async def collect_name_serv(message: Message, state: FSMContext):
    input_text = message.text.strip()
    if len(input_text) < 50:
        await state.update_data(sname_add = input_text)
    else:
        await message.answer("❌ Произошла ошибка! Название слишком длинное, ограничене 50 символов")
    await message.answer("Введите цену в рублях для новой усулги. Пример: 400")
    await state.set_state(Admin_Panel.sprice_add)

@apanel_router.message(Admin_Panel.sprice_add)
async def collect_price_serv(message: Message, state: FSMContext):
    input_text = message.text.strip()
    if int(input_text) > 0:
        await state.update_data(sprice_add = input_text)
    else:
        message.answer("❌ Произошла ошибка! Введите цену корректно. Пример: 400.")
    await message.answer("Введите длительность в минутах для новой усулги.")
    await state.set_state(Admin_Panel.sduration_add)

@apanel_router.message(Admin_Panel.sduration_add)
async def collect_duration_serv(message: Message, state: FSMContext):
    input_text = message.text.strip()
    if int(input_text) > 0:
        await state.update_data(sduration_add = input_text)
    else:
        message.answer("❌ Произошла ошибка! Введите длительность корректно. Пример: 30.")
    builder = InlineKeyboardBuilder()
    builder.button(text="Мужской", callback_data=f"add_sex_{2}")
    builder.button(text="Женский", callback_data=f"add_sex_{3}")
    builder.button(text="Общий", callback_data=f"add_sex_{1}")
    builder.adjust(2)
    await message.answer("Выберите пол для новой услуги", reply_markup=builder.as_markup())

@apanel_router.callback_query(F.data.startswith("add_sex_"))
async def confirm_add_serv(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    data = await state.get_data()
    name = data.get("sname_add")
    price = int(data.get("sprice_add"))
    duration = int(data.get("sduration_add"))
    sex = int(parts[2])
    print(f"пол при создании: {sex}")
    output_sex = "Общий"

    await state.update_data({
        "data_full_add":{
            'name': name,
            'price': price,
            'duration': duration,
            'sex': sex
        }
    })
    if sex == 2:
        output_sex = "Mужской"
    elif sex == 3:
        output_sex = "Женский"

    detail_text = (
        "Информация о новой услуге\n\n"
        f"Название: {name}\n\n"
        f"Цена услуги: {price}\n"
        f"Длительность услуги: {duration}\n\n"
        f"Пол услуги: {output_sex}"
    )
    bulider = InlineKeyboardBuilder()
    bulider.button(text="✅ Подтвердить создание", callback_data="apanel_confirm_add_serv")
    bulider.button(text="❌ Отменить создание", callback_data="apanel_сancel_add_serv")
    await callback.message.answer(text=detail_text, reply_markup=bulider.as_markup())

@apanel_router.callback_query(F.data == "apanel_сancel_add_serv")
async def canceling_add_serv(callback: CallbackQuery, state: FSMContext):
    callback.message.edit_text("❌ Создание новой услуги отменено.")
    await show_list_services(callback, 0, state)

@apanel_router.callback_query(F.data == "apanel_confirm_add_serv")
async def canceling_add_serv(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    service = data.get("data_full_add")
    query = "INSERT INTO services (name, price, duration, sex) VALUES (:name, :price, :duration, :sex)"
    try:
        await db_connector.execute_query(query, {"name": service["name"], "price": service["price"], "duration": service["duration"], "sex": service["sex"]})
    except DetailedAiogramError as e:
        await callback.message.edit_text("❌ При сохранении данных в БД произошла ошибка! Попробуйте еще раз.")
        await send_long_message(f"Excpetion admin_panel.py 1026 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        return
    await callback.message.edit_text("✅ Услуга успешно создана.")
    await show_list_services(callback, 0, state)


async def show_review(message: Message, state: FSMContext):
    try:
        query = "SELECT r.id, r.id_chat, r.id_message, r.datetime, u.name FROM reviews r JOIN users u ON u.id = r.id_chat WHERE check_in = 'false' LIMIT 1"
        request = await db_connector.execute_query(query)
        result = request.fetchone()
    except DetailedAiogramError as e:
        await message.answer(text="❌ При получении данных из БД произошла ошибка!")
        await send_long_message(f"Excpetion admin_panel.py 1039 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        return
    
    if not result:
        await message.answer(text="✅Отзывов для обработки нет.")
        return
    await state.update_data(rname = result.name, rdata = result.datetime)
    await message.answer(f"📅 Дата: {result.datetime.strftime('%d.%m.%Y')}\n"
                        f"🕒 Время: {result.datetime.strftime('%H:%M')}\n\n"
                        f"💇‍♂️ <a href='tg://user?id={result.id_chat}'>Перейти к пользователю</a>",
                        parse_mode="HTML")
    
    await bot.forward_message(
        chat_id=message.chat.id,
        from_chat_id=result.id_chat,
        message_id=result.id_message
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Опубликовать отзыв.", callback_data=f"review_publish_{result.id}_{result.id_chat}_{result.id_message}")
    builder.button(text="❌ Удалить отзыв.", callback_data=f"review_delete_{result.id}")
    builder.button(text="⬅️ Назад к админ-панели.", callback_data=f"review_close")
    builder.adjust(2)
    await message.answer(text="Выберите действие:", reply_markup=builder.as_markup())
        

@apanel_router.message(F.text == "Публикация отзывов")
async def check_review(message: Message, state: FSMContext):
    await show_review(message, state)

@apanel_router.callback_query(F.data.startswith("review_publish_"))
async def publish_review(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    review_id = parts[2]
    id_chat = parts[3]
    id_message = parts[4]
    data = await state.get_data()
    name = data.get("rname")
    date = data.get("rdata")
    try:
        query = "UPDATE reviews SET check_in = \'true\' WHERE id = :id"
        if await db_connector.execute_query(query, {"id": int(review_id)}):
            await callback.message.edit_text(text="✅ Отзыв опубликован.")
            await bot.send_message(chat_id=-4937110209, text=f"📋 Отзыв от нашего клиента {name.capitalize()}.\n\n📅 Дата: {date.strftime('%d.%m.%Y')}")
            await bot.forward_message(chat_id=-4937110209, from_chat_id=id_chat, message_id=id_message)
            return await show_review(callback.message, state)
    except DetailedAiogramError as e:
        await send_long_message(f"Excpetion admin_panel.py 1085 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        await callback.message.edit_text(text="❌ При публикации отзыва возникла ошибка.")

@apanel_router.callback_query(F.data.startswith("review_delete_"))
async def publish_review(callback: CallbackQuery):
    parts = callback.data.split("_")
    review_id = parts[2]
    try:
        query = "DELETE FROM reviews WHERE id = :id"
        if await db_connector.execute_query(query, {"id": int(review_id)}):
            await callback.message.edit_text(text="✅ Отзыв удален.")
            return await show_review(callback.message)
    except DetailedAiogramError as e: 
        await callback.message.edit_text(text="❌ При удалении отзывавозникла ошибка.")
        await send_long_message(f"Excpetion admin_panel.py 1099 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 

@apanel_router.callback_query(F.data.startswith("review_close"))
async def publish_review(callback: CallbackQuery):
    await callback.message.answer("Здравствуйте администратор!\n", reply_markup=admin_kb(callback.from_user.id))