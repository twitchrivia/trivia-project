from twitchio.ext import commands
import asyncio
import requests
from random import shuffle
import html
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def fetch_trivia_question():
    try:
        url = "https://opentdb.com/api.php?amount=1&type=multiple"
        response = requests.get(url)
        data = response.json()

        if data.get("response_code") != 0:
            return None

        question_data = data["results"][0]
        question = html.unescape(question_data["question"])  # Decode HTML entities
        correct_answer = html.unescape(question_data["correct_answer"])
        incorrect_answers = [html.unescape(ans) for ans in question_data["incorrect_answers"]]

        all_answers = [correct_answer] + incorrect_answers
        shuffle(all_answers)

        return {
            "question": question,
            "correct_answer": correct_answer,
            "all_answers": all_answers,
        }
    except Exception as e:
        logging.error(f"Error in fetch_trivia_question: {e}")
        return None

class Bot(commands.Bot):

    def __init__(self):
        super().__init__(
            token="q2zormdv8jwc5s8fnqmeolkyjwnfxc",
            prefix="!",
            initial_channels=["twitchrivia"]
        )
        self.current_question = None
        self.correct_answer = None
        self.scores = {}
        self.question_active = False
        self.task_running = False
        self.lock = asyncio.Lock()  # For synchronizing access to shared state
        self.previous_top_scorer = None  # Keep track of previous top scorer

    async def event_ready(self):
        logging.info(f"Logged in as {self.nick}")
        logging.info(f"Connected to channel(s): {self.connected_channels}")
        if not self.task_running:  # Ensure only one trivia cycle runs
            self.task_running = True
            asyncio.create_task(self.trivia_cycle())

    async def trivia_cycle(self):
        logging.info("Starting trivia cycle...")
        while True:
            async with self.lock:
                if not self.question_active:
                    channel = self.get_channel("twitchrivia")
                    if not channel:
                        logging.info("Channel not found, retrying...")
                        await asyncio.sleep(10)
                        continue

                    try:
                        await self.ask_question(channel)
                        await asyncio.sleep(30)  # Wait for answers
                        if self.question_active:  # Time's up if no correct answer
                            await channel.send("Time's up! No correct answers. Another question coming up!")
                            self.question_active = False
                    except Exception as e:
                        logging.error(f"Error in trivia_cycle: {e}")
                    finally:
                        logging.info("Waiting 15 seconds before the next question...")
                        await asyncio.sleep(15)  # Cooldown before the next question
                else:
                    logging.info("Question already active. Throttling checks...")
            await asyncio.sleep(5)  # Short delay to avoid frequent checks

    async def ask_question(self, channel):
        trivia = fetch_trivia_question()
        if trivia:
            self.current_question = trivia["question"]
            self.correct_answer = trivia["correct_answer"].strip().lower()
            self.question_active = True
            logging.info(f"Question Fetched: {self.current_question}")
            await channel.send("Trivia Time!")
            await channel.send(self.current_question)
            await channel.send(f"Options: {', '.join(trivia['all_answers'])}")
        else:
            logging.info("No trivia question fetched.")
            await channel.send("Unable to fetch a trivia question. Trying again soon.")

    async def event_message(self, message):
        try:
            if not message or not message.author or not message.content:
                return
            if message.author.name.lower() == self.nick.lower():
                return

            username = message.author.name.lower()
            user_input = message.content.strip().lower()
            correct_answer = self.correct_answer.strip().lower() if self.correct_answer else None

            if self.question_active and user_input == correct_answer:
                self.question_active = False
                if username not in self.scores:
                    self.scores[username] = {"points": 0, "streak": 0, "streaks_count": 0, "longest_streak": 0}

                # Update scores and streaks
                self.scores[username]["points"] += 1
                self.scores[username]["streak"] += 1
                self.scores[username]["streaks_count"] += 1
                self.scores[username]["longest_streak"] = max(
                    self.scores[username]["longest_streak"], self.scores[username]["streak"]
                )

                # Determine streak icons
                icons = []
                streak = self.scores[username]["streak"]

                if streak >= 20:
                    icons.append("💎")
                elif streak >= 15:
                    icons.append("👑")
                elif streak >= 10:
                    icons.append("✨")
                elif streak >= 5:
                    icons.append("⭐")

                # Add gold medal for the top scorer
                top_scorer = max(self.scores.items(), key=lambda x: x[1]["points"])[0]
                if username == top_scorer:
                    icons.append("🥇")

                icon_str = " ".join(icons)
                points = self.scores[username]["points"]

                # Send confirmation message
                await message.channel.send(f"{icon_str} {username}: Correct! You now have {points} points!")

                # Custom messages for streak milestones
                if streak == 5:
                    await message.channel.send(f"Wow! {username} has achieved a streak of 5 correct answers in a row!")
                elif streak == 10:
                    await message.channel.send(f"You're on FIRE! {username} has achieved a streak of 10 correct answers in a row!")
                elif streak == 15:
                    await message.channel.send(f"BOOM SHAKA LAKA!! {username} has achieved a streak of 15 correct answers in a row!")
                elif streak == 20:
                    await message.channel.send(f"GOD LIKE! {username} has achieved a streak of 20 correct answers in a row!")

                # Top scorer message
                if username == top_scorer and username != self.previous_top_scorer:
                    if self.previous_top_scorer:
                        await message.channel.send(
                            f"Congratulations {username}, you've taken the top scoring spot from {self.previous_top_scorer}!"
                        )
                    else:
                        await message.channel.send(f"Congratulations {username}, you're the top scorer!")
                    self.previous_top_scorer = username

            elif self.question_active and user_input != correct_answer:
                if username in self.scores and self.scores[username]["streak"] > 0:
                    streak_lost = self.scores[username]["streak"]
                    await message.channel.send(f"Oh no! {username} has given an incorrect answer and ended their {streak_lost} answer streak!")
                    self.scores[username]["streak"] = 0  # Reset streak

        except Exception as e:
            logging.error(f"An error occurred in event_message: {e}")

if __name__ == "__main__":
    logging.info("Starting the bot...")
    bot = Bot()
    bot.run()
