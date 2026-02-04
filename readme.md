# 🎓 College Results Dashboard

A dynamic web application built with **Flask** and **BeautifulSoup** that automates the retrieval of academic results from the college portal. It transforms a manual, one-by-one search process into a centralized leaderboard and detailed report card viewer.

## 🚀 Features
- **Automated Scraping:** Iteratively fetches results for an entire class using their Roll Numbers.
- **Leaderboard View:** Displays a sorted list of students ranked by their **SGPA**.
- **Detailed Report Cards:** Clicking a student's name opens their full subject-wise marksheet in a new browser tab.
- **Real-time Processing:** Data is fetched directly from the source portal on demand.

## 🛠️ Tech Stack
- **Backend:** Python 3.12+
- **Framework:** Flask
- **Web Scraping:** Requests, BeautifulSoup4
- **Templating:** Jinja2 (HTML/CSS)

## 📋 Prerequisites
Before running the app, ensure you have the following installed:
- **Python 3.12** or higher.
- An active internet connection to reach `vnrvjietexams.net`.

## ⚙️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Anurag-006/Result-Checker.git
   cd Result-Checker
   ```

2. **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: .venv\Scripts\activate.bat
    ```
3. **Install dependencies:**
    ```bash
    pip install -r requirements.txt    
    ```
4. **Run the application:**
    ```bash
    python app/app.py
    ```
5. **Access the Dashboard:**
    Open your browser and navigate to http://127.0.0.1:5000

## 📂 Project Structure

```
.
├── app.py              # Main Flask application & scraping logic
├── requirements.txt    # Project dependencies
├── templates/          # HTML templates (Jinja2)
│   ├── dashboard.html  # Main leaderboard view
│   └── report_card.html # Individual student marksheet
└── README.md           # Project documentation
```

## ⚠️ Important Notes

- Rate Limiting: The script includes a time.sleep() delay between requests to be respectful to the college server.

- Session Cookies: If the portal requires authentication, ensure the headers in app.py are updated with a valid session cookie from your browser's Network tab.