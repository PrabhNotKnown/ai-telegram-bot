# 🤖 AI Personal Assistant Telegram Bot

A powerful and multifunctional Telegram bot that acts like your AI assistant — with website summarization, PDF tools, email extraction, crypto alerts, and voice conversion features, all built using Python.

---

## 🚀 Features

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | Show all available commands |
| `/setalert` | 📈 Set price alerts for BTC, ETH, SOL, BNB |
| `/summary` | 🌐 Summarize any webpage using Groq’s LLaMA 3 |
| `/summarizepdf` | 📄 Get a summary, full text, or audio from a PDF |
| `/pdftovoice` | 🔊 Convert any PDF or plain text to voice *(under development)* |
| `/extractemails` | 📧 Extract emails from a webpage (text + CSV output supported, CSV under development) |
| `/cancel` | ❌ Cancel any ongoing operation |

---

## 🧠 Powered by

- **Python 3.10+**
- [`python-telegram-bot`](https://github.com/python-telegram-bot/python-telegram-bot) v20+
- [`Groq API`](https://console.groq.com/) with LLaMA 3 model
- `requests` and `re` for web and regex
- `BeautifulSoup` for web scraping
- `PyMuPDF` for PDF reading
- `pyttsx3` for offline text-to-speech *(beta)*
- `dotenv` for API key security

---

## 📁 Project Structure
ai-personal-assistant-bot/
├── main.py # ✅ Main bot code
├── .env # 🔐 API keys (Git ignored)
├── requirements.txt # 📦 Python dependencies
├── .gitignore # 🧼 Prevent unwanted files in Git
├── README.md # 📘 You’re reading it!


---

## ⚙️ Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/ai-personal-assistant-bot.git
cd ai-personal-assistant-bot

2. Create Virtual Environment (Optional but Recommended)
python -m venv venv
source venv/bin/activate      # On Linux/Mac
venv\Scripts\activate         # On Windows

3. Install Dependencies
pip install -r requirements.txt

4. Add .env File
Create a .env file in the root and add your secrets:
BOT_TOKEN=your_telegram_bot_token
GROQ_API_KEY=your_groq_api_key

5. Run the Bot
python main.py

📌 Notes
Your bot only responds to users who start it.

Groq’s LLaMA 3 is fast, free, and great for summarization.

PDF → Audio is currently in beta and may cut long content.

CSV export for email extraction is still under development.

Avoid scraping very complex or JavaScript-heavy websites.

✅ Example Use Cases
🔔 Get crypto price alerts directly in Telegram

🌐 Summarize long articles using AI instantly

📄 Extract emails from any basic webpage

🧠 Turn a PDF textbook into a short summary

🔊 Convert text content to audio (beta)

👨‍💻 Author
Prabhraj Singh
Telegram bot developer | Python freelancer
💬 DM me on Telegram if you'd like to collaborate!

📄 License
This project is licensed under the MIT License — feel free to use and modify with credit.
