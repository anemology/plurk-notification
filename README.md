# Plurk Notification

檢查噗浪使用者是否有新噗

## Telegram

- 找 `@botfather` 建立新 bot 並取得 token
- 設定 webhook, 執行 [webhook.sh](/webhook.sh)

## AWS

### Lambda

- Runtime: Python 3.8 or higher
- Layer: 包含 requirements.txt 內的 package
- function URLs: 啟用並設定 `AuthType` 為 `None`

### CloudWatch Event

每 10 分鐘執行一次

- EventBridge Schedule expression: `cron(0/10 * * * ? *)`

## TOOD

- [ ] 自動抓取 uid
- [ ] 抓取新回覆
- [ ] 整理相關 function 跟 [plurkdl](https://github.com/anemology/plurkdl) 整合在一起

## Reference

[Schedule Expressions for Rules - Amazon CloudWatch Events](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html)
