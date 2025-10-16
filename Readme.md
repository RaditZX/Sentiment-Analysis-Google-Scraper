#🧠 Sentiment Analysis Google Scraper API

FastAPI backend for scraping Google Maps reviews (via Apify) and performing **sentiment analysis** using **GitHub Models / OpenAI-compatible API**.  
This API is designed for integration with a **React Dashboard frontend** and supports both **synchronous** and **asynchronous** scraping jobs.

---

## 🚀 Features

- 🔍 **Google Maps Review Scraper** via [Apify](https://apify.com)
- 💬 **Sentiment Analysis** using GitHub Models / OpenAI-compatible API
- 🧹 **Automatic Review Cleaning** (duplicate & invalid text removal)
- 📊 **MySQL Database Integration**
- ⚡ **Async Background Jobs** with job status tracking
- 🌐 **FastAPI REST API** (CORS-ready for React frontend)
- 🧩 **Multiple Location Scraping Support**

---

## 🏗️ Tech Stack

| Component | Technology |
|------------|-------------|
| Backend Framework | FastAPI |
| Database | MySQL |
| Scraping | Apify Client |
| Sentiment Model | GitHub Models (GPT-4o-mini) |
| Environment | Python 3.10+ |
| Frontend | React (Dashboard) |

---

## ⚙️ Installation

```bash
# 1️⃣ Clone the repository
git clone https://github.com/RaditZX/Sentiment-Analysis-Google-Scraper.git
cd Sentiment-Analysis-Google-Scraper

# 2️⃣ Create and activate a virtual environment
python -m venv venv
venv\\Scripts\\activate   # (Windows)
# source venv/bin/activate  (Linux/macOS)

# 3️⃣ Install dependencies
pip install -r requirements.txt

# 4️⃣ Setup environment variables
cp .env.example .env
