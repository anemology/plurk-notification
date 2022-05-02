read -p "Telegram bot token: " token
read -p "Lambda function URLs: " urls

curl "https://api.telegram.org/bot$token/setWebhook?url=$urls"
