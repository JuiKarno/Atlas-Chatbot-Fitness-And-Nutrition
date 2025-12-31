# 🏋️ Atlas - AI Fitness & Nutrition Chatbot

An intelligent AI-powered fitness and nutrition coach that provides personalized workout recommendations, meal plans, and health guidance based on your profile and goals.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)
![Firebase](https://img.shields.io/badge/Firebase-Firestore-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

- **🤖 AI-Powered Conversations** - Natural language understanding for fitness queries
- **💪 Personalized Workouts** - Exercise recommendations based on your fitness level and goals
- **🥗 Nutrition Guidance** - Meal suggestions tailored to your dietary preferences
- **📊 BMI & Health Metrics** - Calculate and track your health statistics
- **📅 30-Day Pathway Plans** - Structured long-term workout programs
- **📆 Weekly Workout Tables** - Visual weekly schedules with real exercises
- **💬 Chat History** - Persistent conversation storage across sessions
- **🌙 Dark Mode** - Beautiful UI with light/dark theme support

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Firebase account with Firestore database
- OpenRouter API key (or Groq API key)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/JuiKarno/Atlas-Chatbot-Fitness-And-Nutrition.git
   cd Atlas-Chatbot-Fitness-And-Nutrition
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   
   Create a `.env` file in the root directory:
   ```env
   # OpenRouter API
   OPENROUTER_API_KEY=your_openrouter_api_key
   OPENROUTER_MODEL=xiaomi/mimo-v2-flash:free
   
   # Flask
   FLASK_SECRET_KEY=your_secret_key
   ```

4. **Add Firebase credentials**
   
   Place your `serviceAccountKey.json` in the root directory.

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Open in browser**
   ```
   http://localhost:5000
   ```

## 📁 Project Structure

```
atlas_chatbot_v2/
├── app.py                 # Main Flask application
├── config/
│   └── settings.py        # Configuration settings
├── core/
│   ├── nlu_engine.py      # Natural Language Understanding
│   ├── recommender.py     # Content-based recommendations
│   ├── pathway_engine.py  # 30-day plan generator
│   └── predictive_engine.py # Smart suggestions
├── templates/
│   ├── chatbot.html       # Main chat interface
│   └── auth.html          # Login page
├── static/                # CSS, JS, images
└── .env                   # Environment variables (not in repo)
```

## 🔧 Configuration

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key |
| `OPENROUTER_MODEL` | AI model to use (default: xiaomi/mimo-v2-flash:free) |
| `FLASK_SECRET_KEY` | Secret key for Flask sessions |

## 💡 Usage Examples

- **Get workout recommendations:** "Give me chest exercises"
- **Ask health questions:** "What is my BMI?"
- **Create meal plans:** "Suggest a high protein breakfast"
- **Generate schedules:** "Make me a weekly workout timetable"
- **Set preferences:** "I like running" / "I don't like burpees"

## 🛡️ Security

- API keys stored in `.env` file (not committed to repo)
- Firebase credentials excluded via `.gitignore`
- User authentication via Firebase Auth

## 📝 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- OpenRouter for AI API access
- Firebase for database and authentication
- TailwindCSS for styling

---

**Built with ❤️ for fitness enthusiasts**
