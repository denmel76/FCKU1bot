import os

# Токен бота берется из переменных окружения Render
TOKEN = os.environ.get("BOT_TOKEN")

# ID администратора (ваш личный Telegram ID), куда будут приходить заказы
ADMIN_ID = os.environ.get("ADMIN_ID")
