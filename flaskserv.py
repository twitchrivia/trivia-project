from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import threading
import time
import random
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

app = Flask(__name__)
CORS(app)

# Mock data structure for the overlay
DATA = {
    "announcements": "<h1>Welcome to Twitchrivia!</h1>",
    "current_question": {"question": "What is the capital of France?", "options": ["Paris", "London", "Berlin", "Madrid"]},
    "leaderboard": [
        {"name": "User1", "score": 0, "badges": []},
        {"name": "User2", "score": 0, "badges": []},
        {"name": "User3", "score": 0, "badges": []},
        {"name": "User4", "score": 0, "badges": []},
        {"name": "User5", "score": 0, "badges": []},
        {"name": "User6", "score": 0, "badges": []},
        {"name": "User7", "score": 0, "badges": []},
        {"name": "User8", "score": 0, "badges": []},
        {"name": "User9", "score": 0, "badges": []},
    ],
    "top_streakers": [{"name": "No current streaks", "streak": 0, "badges": []}]
}

current_streaks = {user["name"]: 0 for user in DATA["leaderboard"]}  # Initialize streaks

# Update streaks and badges
def update_streaks_and_top_streakers(scoring_user_name, incorrect_user_name=None):
    global DATA

    # Increment streak for the scoring user
    current_streaks[scoring_user_name] += 1

    # Log the updated streak
    logging.info(f"{scoring_user_name}'s streak updated to {current_streaks[scoring_user_name]}.")

    # Reset streak only for users who gave an incorrect answer
    if incorrect_user_name and incorrect_user_name in current_streaks:
        logging.info(f"Streak broken for {incorrect_user_name} at {current_streaks[incorrect_user_name]}")
        current_streaks[incorrect_user_name] = 0

    # Find the maximum streak
    max_streak = max(current_streaks.values(), default=0)

    # Identify all users with the highest streak
    top_streakers = [
        {
            "name": ", ".join([name for name, streak in current_streaks.items() if streak == max_streak and streak > 0]),
            "streak": max_streak,
            "badges": []
        }
    ] if max_streak > 0 else [{"name": "No current streaks", "streak": 0, "badges": []}]

    # Assign badges to top streakers
    for streaker in top_streakers:
        streak = streaker["streak"]
        if streak >= 5:
            streaker["badges"] = (
                ["⭐"] if streak < 10 else
                ["✨"] if streak < 15 else
                ["👑"] if streak < 20 else ["💎"]
            )

    # Update global DATA with top streakers
    DATA["top_streakers"] = top_streakers
    logging.info(f"Top streakers: {DATA['top_streakers']}")

def update_leaderboard():
    global DATA

    # Sort leaderboard by score
    DATA["leaderboard"] = sorted(DATA["leaderboard"], key=lambda x: x["score"], reverse=True)

    # Find the maximum score
    max_score = max([user["score"] for user in DATA["leaderboard"]], default=0)

    # Assign 'top scorer' badge to all users with the maximum score
    for user in DATA["leaderboard"]:
        badges = []
        if user["score"] == max_score and max_score > 0:
            badges.append("🥇")  # Top scorer badge

        # Add streak badge if applicable
        streak = current_streaks.get(user["name"], 0)
        if streak >= 5:
            badges.append(
                "⭐" if streak < 10 else
                "✨" if streak < 15 else
                "👑" if streak < 20 else "💎"
            )

        user["badges"] = badges

    logging.info("Leaderboard updated:")
    for user in DATA["leaderboard"]:
        logging.info(f"{user['name']} - {user['score']} points - Badges: {user['badges']}")
def update_question():
    questions = [
        {"question": "What is the capital of France?", "options": ["Paris", "London", "Berlin", "Madrid"]},
        {"question": "Who wrote 'To Kill a Mockingbird'?", "options": ["Harper Lee", "Mark Twain", "Ernest Hemingway", "F. Scott Fitzgerald"]},
        {"question": "What is the square root of 64?", "options": ["6", "7", "8", "9"]}
    ]
    DATA["current_question"] = random.choice(questions)
    logging.info(f"New question: {DATA['current_question']}")


# Bot simulation
def bot_simulation():
    while True:
        scoring_user = random.choice(DATA["leaderboard"])
        scoring_user["score"] += 1
        update_streaks_and_top_streakers(scoring_user["name"])
        update_leaderboard()
        update_question()

        # Update announcements
        DATA["announcements"] = f"<h1>{scoring_user['name']} scored a point!</h1>"
        logging.info(f"Announcement: {DATA['announcements']}")
        time.sleep(30)

@app.route("/")
def overlay():
    return render_template("overlay.html")

@app.route("/data")
def data():
    return jsonify(DATA)

@app.route("/update", methods=["POST"])
def update():
    global DATA
    data = request.get_json()
    if "announcements" in data:
        DATA["announcements"] = data["announcements"]
        logging.info(f"Updated announcements: {DATA['announcements']}")
    if "leaderboard" in data:
        DATA["leaderboard"] = data["leaderboard"]
        logging.info(f"Updated leaderboard: {DATA['leaderboard']}")
    if "top_streakers" in data:
        DATA["top_streakers"] = data["top_streakers"]
        logging.info(f"Updated top streakers: {DATA['top_streakers']}")
    if "current_question" in data:
        DATA["current_question"] = data["current_question"]
        logging.info(f"Updated question: {DATA['current_question']}")
    return jsonify({"status": "success"})

if __name__ == "__main__":
    # Start the bot simulation in a separate thread
    threading.Thread(target=bot_simulation, daemon=True).start()

    logging.info("Starting Flask server...")
    app.run(debug=True, use_reloader=True)
