import os
import logging
import threading
from http.server import ThreadingHTTPServer
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from telegram import MenuButtonWebApp, WebAppInfo
from backend.core.config import BOT_TOKEN, ADMIN_IDS
from backend.api.server_handler import SecurityHTTPHandler, get_clean_webapp_url
from backend.api.bot_handlers import (
    start_command, kho_command, me_command, nap_command, ds_command, top_command,
    admin_command, themsp_command, nhapkey_command, xoasp_command, dssp_command, khokey_command,
    setvip_command, congtien_command, trutien_command, thanhvien_command, themdanhmuc_command,
    xoadanhmuc_command, dsdanhmuc_command, caidat_command, addmusic_command, taolink_command,
    thongbao_command, themdanhmucmuaacc_command, handle_incoming_media, handle_callback_query
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("MihQuanStore")

def start_background_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = ThreadingHTTPServer(("0.0.0.0", port), SecurityHTTPHandler)
    logger.info(f"✅ Web server Mih Quân Mini App đã mở trên cổng {port}!")
    server.serve_forever()

async def post_init(application):
    try:
        clean_url = get_clean_webapp_url()
        await application.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="🚀 Mở Cửa Hàng", web_app=WebAppInfo(url=clean_url))
        )
        logger.info(f"✅ Đã thiết lập Telegram Menu Button tự động: {clean_url}")
    except Exception as e:
        logger.warning(f"Không thể thiết lập Telegram Menu Button: {e}")

def main():
    print("==================================================")
    print("⚡ MIH QUÂN STORE ")
    print(f"👉 Admin IDs: {ADMIN_IDS}")
    print("==================================================")

    web_thread = threading.Thread(target=start_background_web_server, daemon=True)
    web_thread.start()

    if not BOT_TOKEN:
        logger.error("❌ Chưa thiết lập BOT_TOKEN trong biến môi trường!")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("kho", kho_command))
    app.add_handler(CommandHandler("me", me_command))
    app.add_handler(CommandHandler("nap", nap_command))
    app.add_handler(CommandHandler("ds", ds_command))
    app.add_handler(CommandHandler("top", top_command))

    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("themsp", themsp_command))
    app.add_handler(CommandHandler("nhapkey", nhapkey_command))
    app.add_handler(CommandHandler("xoasp", xoasp_command))
    app.add_handler(CommandHandler("dssp", dssp_command))
    app.add_handler(CommandHandler("khokey", khokey_command))
    app.add_handler(CommandHandler("setvip", setvip_command))
    app.add_handler(CommandHandler("congtien", congtien_command))
    app.add_handler(CommandHandler("trutien", trutien_command))
    app.add_handler(CommandHandler("thanhvien", thanhvien_command))
    app.add_handler(CommandHandler("themdanhmuc", themdanhmuc_command))
    app.add_handler(CommandHandler("themdanhmucmuaacc", themdanhmucmuaacc_command))
    app.add_handler(CommandHandler("xoadanhmuc", xoadanhmuc_command))
    app.add_handler(CommandHandler("dsdanhmuc", dsdanhmuc_command))
    app.add_handler(CommandHandler("caidat", caidat_command))
    app.add_handler(CommandHandler("addmusic", addmusic_command))
    app.add_handler(CommandHandler("taolink", taolink_command))
    app.add_handler(CommandHandler("thongbao", thongbao_command))

    media_filter = filters.PHOTO | filters.AUDIO | filters.VOICE | filters.Document.ALL
    app.add_handler(MessageHandler(media_filter, handle_incoming_media))
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
