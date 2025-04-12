# AI看圖寫文案智能體

## 專案介紹
這是一個 LINE 機器人，使用者上傳圖片後，自動產生社群貼文用的標題與文案。

## 環境需求
- Python 3.8+
- Flask
- requests
- python-dotenv
- OpenAI API Key
- LINE Messaging API

---

## 專案檔案說明
| 檔案 | 功能說明 |
|------|----------|
| app.py | 系統核心程式 |
| config.json | 動態文字設定檔 |
| users_data.json | 會員資料自動儲存 |
| users_list.txt | 簡易會員 user_id 列表 |
| logs/ | 操作紀錄自動儲存 |
| .env | 環境變數設定檔（請參考 .env.example）|
| requirements.txt | Python 套件需求 |
| AI_Operation_Guide.txt | 營運維護手冊 |

---

## .env 設定範例
LINE_CHANNEL_ACCESS_TOKEN=你的LINE_CHANNEL_ACCESS_TOKEN
LINE_CHANNEL_SECRET=你的LINE_CHANNEL_SECRET
OPENAI_API_KEY=你的OPENAI_API_KEY

COST_PER_POST=0.05
TWD_EXCHANGE_RATE=33

---

## 使用者指令
| 指令 | 功能 |
|------|------|
| 資訊 / 剩餘次數 | 查看個人狀態與次數 |
| VIP | 查看 VIP 方案 |
| 分享 | 產生個人推薦網址 |
| 我的ID | 查詢自己的 user_id |

---

## 管理者指令
| 指令 | 功能 |
|------|------|
| 管理 增加客服 user_id 次數 | 增加加入客服獎勵次數 |
| 管理 增加推薦 user_id 次數 | 增加推薦好友次數 |
| 管理 增加獎勵 user_id 次數 | 額外客服提供獎勵次數 |
| 管理 查詢 user_id | 查詢該會員完整資料 |

---

## 資料管理
- 所有資料自動寫入 json 檔案
- logs/ 資料夾每日自動產生紀錄檔
- Render / Github 重啟後自動讀取最新資料
- 請定期下載備份 users_data.json 與 logs/ 檔案

---

## 部署步驟
1. 上傳專案檔案至 GitHub
2. Render 建立 Web Service
3. 設定 .env 環境變數
4. Deploy 最新版本
5. 測試 webhook 回應
6. 開始營運！

---

## 備註
詳細營運與維護請參考 AI_Operation_Guide.txt