# LINE ChatGPT 圖片文案自動生成機器人

## 功能簡介
- 上傳圖片至 LINE
- 自動生成 3 種不同風格文案
- 每種文案包含：
風格類型：
標題：（15-20字內）
內容：（40-50字內）

## 專案安裝與部署
### 安裝套件
pip install -r requirements.txt

### .env 環境變數
請建立 .env 檔案，填入以下資訊：

LINE_CHANNEL_ACCESS_TOKEN=你的 Token
LINE_CHANNEL_SECRET=你的 Secret
OPENAI_API_KEY=你的 OpenAI Key

### 部署 Render
1. 上傳專案
2. 設定 Environment Variables
3. 設定 Webhook URL
4. 測試