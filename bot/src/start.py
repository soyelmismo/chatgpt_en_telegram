import telegram
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    AIORateLimiter,
    filters
)
from .handlers import message, voice, ocr_image, document, timeout, error
from .handlers.commands import start, help, retry, new, cancel, chat_mode, model, api, img, lang
from .tasks import cache
from .utils import config
from .utils.proxies import bb, logger

#async def obtener_vivas():
#    from apistatus import estadosapi
#    global apis_vivas
#    apis_vivas = await estadosapi()

async def post_init(application: Application):
    bb(cache.task())
    commandos = [
        ("/new", "🌟"),
        ("/chat_mode", "💬"),
        ("/retry", "🔄"),
        ("/model", "🧠"),
        ("/api", "🔌"),
        ("/lang", "🌍"),
        ("/help", "ℹ️")
    ]  
    if config.switch_imgs == "True":
        commandos.insert(5, ("/img", "🖼️"))
    await application.bot.set_my_commands(commandos)

def run_bot() -> None:
    try:
        application = (
            ApplicationBuilder()
            .token(config.telegram_token)
            .concurrent_updates(True)
            .pool_timeout(30)
            .connect_timeout(30)
            .get_updates_write_timeout(30)
            .get_updates_read_timeout(30)
            .get_updates_pool_timeout(30)
            .get_updates_connection_pool_size(32)
            .get_updates_connect_timeout(30)
            .read_timeout(30)
            .write_timeout(30)
            .rate_limiter(AIORateLimiter(max_retries=50))
            .post_init(post_init)
            .build()
        )
        # add handlers
        if config.user_whitelist:
            usernames = []
            user_ids = []
            for user in config.user_whitelist:
                user = user.strip()
                if user.isnumeric(): user_ids.append(int(user))
                else: usernames.append(user)
            user_filter = filters.User(username=usernames) | filters.User(user_id=user_ids)
        else:
            user_filter = filters.ALL
        if config.chat_whitelist:
            chat_ids = []
            for chat in config.chat_whitelist:
                chat = chat.strip()
                if chat[0] == "-" and chat[1:].isnumeric(): chat_ids.append(int(chat))
            chat_filter = filters.Chat(chat_id=chat_ids)
        else: chat_filter = filters.ALL

        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & (user_filter | chat_filter), message.wrapper))

        if config.switch_voice == "True":
            application.add_handler(MessageHandler(filters.AUDIO & (user_filter | chat_filter), voice.wrapper))
            application.add_handler(MessageHandler(filters.VOICE & (user_filter | chat_filter), voice.wrapper))
        if config.switch_ocr == "True":
            application.add_handler(MessageHandler(filters.PHOTO & (user_filter | chat_filter), ocr_image.wrapper))
        if config.switch_docs == "True":
            docfilter = (filters.Document.FileExtension("pdf") | filters.Document.FileExtension("lrc"))
            application.add_handler(MessageHandler(docfilter & (user_filter | chat_filter), document.wrapper))
            application.add_handler(MessageHandler(filters.Document.Category('text/') & (user_filter | chat_filter), document.wrapper))

        application.add_handler(CommandHandler("start", start.handle, filters=(user_filter | chat_filter)))
        application.add_handler(CommandHandler("help", help.handle, filters=(user_filter | chat_filter)))
        application.add_handler(CommandHandler("help_group_chat", help.group, filters=(user_filter | chat_filter)))
        application.add_handler(CommandHandler("retry", retry.handle, filters=(user_filter | chat_filter)))
        application.add_handler(CommandHandler("new", new.handle, filters=(user_filter | chat_filter)))
        application.add_handler(CommandHandler("cancel", cancel.handle, filters=(user_filter | chat_filter)))
        application.add_handler(CommandHandler("chat_mode", chat_mode.handle, filters=(user_filter | chat_filter)))
        application.add_handler(CommandHandler("model", model.handle, filters=(user_filter | chat_filter)))
        application.add_handler(CommandHandler("api", api.handle, filters=(user_filter | chat_filter)))
        if config.switch_imgs == "True":
            application.add_handler(CommandHandler("img", img.wrapper, filters=(user_filter | chat_filter)))
        application.add_handler(CommandHandler("lang", lang.handle, filters=(user_filter | chat_filter)))
        application.add_handler(CallbackQueryHandler(lang.set, pattern="^set_lang"))

        application.add_handler(CallbackQueryHandler(timeout.answer, pattern="^new_dialog"))
        application.add_handler(CallbackQueryHandler(message.actions, pattern="^action"))
        mcbc = "^get_menu"
        application.add_handler(CallbackQueryHandler(chat_mode.callback, pattern=mcbc))
        application.add_handler(CallbackQueryHandler(chat_mode.set, pattern="^set_chat_mode"))
        application.add_handler(CallbackQueryHandler(model.callback, pattern=mcbc))
        application.add_handler(CallbackQueryHandler(model.set, pattern="^set_model"))
        application.add_handler(CallbackQueryHandler(api.callback, pattern=mcbc))
        application.add_handler(CallbackQueryHandler(api.set, pattern="^set_api"))

        application.add_error_handler(error)
        application.run_polling()
    except telegram.error.TimedOut:
        logger.error(f'{config.lang["errores"]["tiempoagotado"][config.pred_lang]}')
    except Exception as e:
        logger.error(f'<run_bot> {config.lang["errores"]["error"][config.pred_lang]}: {e}.')