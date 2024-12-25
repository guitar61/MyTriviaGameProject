import base64  # For safe encoding/decoding of answers
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.dispatcher import FSMContext
from asgiref.sync import sync_to_async
from bot.telegram_bot.states import TriviaStates
from bot.telegram_bot.trivia import TriviaAPI
from bot.models import User
import random
import html
import logging
from django.utils.timezone import now  # Ensure timezone-aware datetime



# Initialize TriviaAPI
trivia_api = TriviaAPI()
logger = logging.getLogger(__name__)


def register_handlers(dp):
    """Register all bot handlers."""
    dp.register_message_handler(send_welcome, commands=["start"])
    dp.register_callback_query_handler(start_trivia, lambda call: call.data == "start_trivia")
    dp.register_callback_query_handler(set_category, lambda call: call.data.startswith("category_"),
                                       state=TriviaStates.waiting_for_category)
    dp.register_message_handler(set_num_questions, state=TriviaStates.waiting_for_num_questions)
    dp.register_callback_query_handler(set_difficulty, lambda call: call.data.startswith("difficulty_"),
                                       state=TriviaStates.waiting_for_difficulty)
    dp.register_callback_query_handler(handle_answer, lambda call: call.data.startswith("answer_"),
                                       state=TriviaStates.answering_question)
    dp.register_callback_query_handler(main_menu, lambda call: call.data == "main_menu")
    dp.register_callback_query_handler(show_score, lambda call: call.data == "score")
    dp.register_callback_query_handler(show_help, lambda call: call.data == "help")
    dp.register_callback_query_handler(show_profile, lambda call: call.data == "profile")
    dp.register_callback_query_handler(back_to_start, lambda call: call.data == "back_to_start")


async def send_welcome(event):
    """Send the welcome message for both Message and CallbackQuery."""
    telegram_id = None
    username = None
    full_name = None

    if isinstance(event, types.Message):
        telegram_id = event.from_user.id
        username = event.from_user.username
        full_name = event.from_user.full_name
    elif isinstance(event, types.CallbackQuery):
        await event.answer()
        telegram_id = event.from_user.id
        username = event.from_user.username
        full_name = event.from_user.full_name

    logging.info(f"User registration attempt: Telegram ID={telegram_id}, Username={username}, Full Name={full_name}")

    if telegram_id:
        await _send_welcome_message(event, telegram_id, username, full_name)
    else:
        logging.error("send_welcome: Telegram ID could not be determined.")


async def _send_welcome_message(message, telegram_id, username, full_name):
    user, created = await sync_to_async(User.objects.get_or_create)(
        telegram_id=telegram_id,
        defaults={"username": username, "full_name": full_name, "games_played": 0, "highest_score": 0}
    )
    logging.info(f"User created: {created}, Telegram ID={telegram_id}")

    greeting = f"Welcome, {full_name}! 🚀" if created else f"Welcome back, {user.full_name}! 🎉"
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("🎮 Play Trivia", callback_data="start_trivia"),
        InlineKeyboardButton("📊 Score", callback_data="score"),
        InlineKeyboardButton("👤 Profile", callback_data="profile"),
        InlineKeyboardButton("📄 Help", callback_data="help")
    )
    if isinstance(message, types.Message):
        await message.reply(greeting, reply_markup=markup)
    elif isinstance(message, types.CallbackQuery):
        await message.message.reply(greeting, reply_markup=markup)


async def start_trivia(call: CallbackQuery, state: FSMContext):
    try:
        await call.answer()
        categories = trivia_api.fetch_categories()
        for category in categories:
            if category["name"].startswith("Entertainment:"):
                category["name"] = category["name"].replace("Entertainment:", "").strip()

        markup = InlineKeyboardMarkup(row_width=2).add(
            *[InlineKeyboardButton(cat["name"], callback_data=f"category_{cat['id']}") for cat in categories]
        )

        await state.update_data(telegram_id=call.from_user.id)
        await call.message.answer("🎯 Choose a category:", reply_markup=markup)
        await TriviaStates.waiting_for_category.set()

        logging.info(f"Trivia started for Telegram ID: {call.from_user.id}")
    except Exception as e:
        logging.error(f"Error in start_trivia: {e}")
        await call.message.answer("⚠️ An error occurred. Please try again later.")


async def set_category(call: CallbackQuery, state: FSMContext):
    await call.answer()
    logging.info(f"Telegram ID in set_category: {call.from_user.id}")
    await state.update_data(category=call.data.split("_")[1])
    await call.message.answer("🧠 How many questions do you want? (1-50)")
    await TriviaStates.waiting_for_num_questions.set()


async def set_num_questions(message: Message, state: FSMContext):
    try:
        logging.info(f"Telegram ID in set_num_questions: {message.from_user.id}")
        num_questions = int(message.text)
        if not 1 <= num_questions <= 50:
            raise ValueError
        await state.update_data(num_questions=num_questions)
        markup = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("Easy", callback_data="difficulty_easy"),
            InlineKeyboardButton("Medium", callback_data="difficulty_medium"),
            InlineKeyboardButton("Hard", callback_data="difficulty_hard")
        )
        await message.answer("🎯 Choose a difficulty:", reply_markup=markup)
        await TriviaStates.waiting_for_difficulty.set()
    except ValueError:
        await message.answer("❌ Please enter a valid number between 1 and 50.")


async def set_difficulty(call: CallbackQuery, state: FSMContext):
    await call.answer()
    logging.info(f"Telegram ID in set_difficulty: {call.from_user.id}")
    await state.update_data(difficulty=call.data.split("_")[1])
    data = await state.get_data()
    questions = trivia_api.fetch_questions(data["num_questions"], data["category"], data["difficulty"])
    await state.update_data(questions=questions, current_question=0, score=0)
    await ask_next_question(call.message, state)


async def ask_next_question(message: Message, state: FSMContext):
    """Ask the next trivia question or end the game."""
    try:
        data = await state.get_data()
        telegram_id = data.get("telegram_id", message.from_user.id)
        current_question = data.get("current_question", 0)
        questions = data.get("questions", [])
        score = data.get("score", 0)

        if current_question >= len(questions):
            # End of the game: Call handle_end_of_game
            await handle_end_of_game(
                telegram_id=telegram_id,
                correct_answers=score,
                total_questions=len(questions)  # Pass total questions
            )

            # Display end-of-game menu
            markup = InlineKeyboardMarkup(row_width=2).add(
                InlineKeyboardButton("🎮 Play Again", callback_data="start_trivia"),
                InlineKeyboardButton("🔄 Back to Start", callback_data="back_to_start")
            )
            await message.answer(f"🎉 Game Over! You scored: {score}/{len(questions)}", reply_markup=markup)
            await state.finish()
            return

        # Continue to the next question
        question = questions[current_question]
        correct_answer = html.unescape(question["correct_answer"])
        all_answers = [html.unescape(ans) for ans in question["incorrect_answers"]] + [correct_answer]
        random.shuffle(all_answers)

        markup = InlineKeyboardMarkup(row_width=2).add(
            *[InlineKeyboardButton(answer, callback_data=f"answer_{base64.urlsafe_b64encode(answer.encode()).decode()}") for answer in all_answers]
        )
        await message.answer(
            f"❓ Question {current_question + 1}/{len(questions)}:\n{html.unescape(question['question'])}",
            reply_markup=markup
        )
        await state.update_data(current_question=current_question + 1)
        await TriviaStates.answering_question.set()
    except Exception as e:
        logging.error(f"Error in ask_next_question: {e}")



async def handle_answer(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    current_question = data.get("current_question", 0)
    questions = data.get("questions", [])
    score = data.get("score", 0)

    try:
        chosen_answer = base64.urlsafe_b64decode(call.data.split("_")[1]).decode()
    except Exception as e:
        await call.message.answer("⚠️ Invalid answer data. Please try again.")
        logger.error(f"Error decoding answer: {e}")
        return

    correct_answer = html.unescape(questions[current_question - 1]["correct_answer"])
    if chosen_answer == correct_answer:
        await call.message.answer("✅ Correct!")
        score += 1
    else:
        await call.message.answer(f"❌ Wrong! The correct answer was: {correct_answer}")

    await state.update_data(score=score)
    await ask_next_question(call.message, state)


from django.utils.timezone import now  # Ensure timezone-aware datetime

async def handle_end_of_game(telegram_id, correct_answers, total_questions):
    """Update user statistics at the end of the game."""
    try:
        # Fetch the user from the database
        user = await sync_to_async(User.objects.get)(telegram_id=telegram_id)

        # Calculate the percentage score for the current game
        current_score_percentage = (correct_answers / total_questions) * 100

        # Update user statistics
        previous_highest_score = user.highest_score
        user.games_played += 1
        user.correct_answers += correct_answers
        user.highest_score = max(previous_highest_score, current_score_percentage)  # Update if the new score is higher
        user.last_played = now()  # Use timezone-aware datetime

        # Save the updated user record
        await sync_to_async(user.save)()

        # Logging updates
        logging.info(
            f"Stats Updated for Telegram ID {telegram_id}: "
            f"Games Played={user.games_played}, Total Correct Answers={user.correct_answers}, "
            f"Previous Highest Score={previous_highest_score:.2f}%, "
            f"New Highest Score={user.highest_score:.2f}%, "
            f"Last Played={user.last_played}"
        )
    except User.DoesNotExist:
        logging.error(f"User with Telegram ID {telegram_id} not found.")
    except Exception as e:
        logging.error(f"Unexpected error while updating stats for Telegram ID {telegram_id}: {e}")


async def main_menu(call: CallbackQuery):
    """Show the main menu with options."""
    await call.answer()  # Respond to the callback to remove the loading state
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("🎮 Play Trivia", callback_data="start_trivia"),
        InlineKeyboardButton("📊 Score", callback_data="score"),
        InlineKeyboardButton("👤 Profile", callback_data="profile"),
        InlineKeyboardButton("📄 Help", callback_data="help")
    )
    await call.message.edit_text("📋 Main Menu:", reply_markup=markup)


async def show_score(call: CallbackQuery):
    """Display user score."""
    await call.answer()
    try:
        user = await sync_to_async(User.objects.get)(telegram_id=call.from_user.id)
        await call.message.answer(
            f"📊 **Your Statistics**:\n"
            f"🎮 Games Played: {user.games_played}\n"
            f"🏆 Highest Score: {user.highest_score}"
        )
    except User.DoesNotExist:
        await call.message.answer("🚫 You are not registered yet! Please use /start to begin.")


async def show_help(call: CallbackQuery):
    """Display help message."""
    await call.answer()
    help_text = (
        "🤖 **Bot Commands**:\n\n"
        "/start - Start the bot and show the main menu\n"
        "🎮 **Play Trivia** - Start playing the trivia game\n"
        "📊 **Score** - View your games played and highest score\n"
        "👤 **Profile** - View your profile details\n"
        "📄 **Help** - Show this help message\n\n"
        "Enjoy the game! 🎉"
    )
    await call.message.answer(help_text, parse_mode="Markdown")

async def show_profile(call: CallbackQuery):
    """Display user profile."""
    await call.answer()
    try:
        user = await sync_to_async(User.objects.get)(telegram_id=call.from_user.id)
        await call.message.answer(
            f"👤 **Profile**:\n"
            f"📛 Full Name: {user.full_name}\n"
            f"🆔 Username: @{user.username}\n"
            f"🎮 Games Played: {user.games_played}\n"
            f"🏆 Highest Score: {user.highest_score:.2f}%\n"  # Add the % symbol here
            f"🕒 Last Played: {user.last_played.strftime('%Y-%m-%d %H:%M:%S') if user.last_played else 'Never'}"
        )
    except User.DoesNotExist:
        await call.message.answer("🚫 You are not registered yet! Use /start to register yourself.")


# Define the handler function
async def back_to_start(call: CallbackQuery, state: FSMContext):
    """Handle 'Back to Start' action."""
    await call.answer()  # Acknowledge the callback to remove loading state
    await state.finish()  # Reset any ongoing state
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("🎮 Play Trivia", callback_data="start_trivia"),
        InlineKeyboardButton("📊 Score", callback_data="score"),
        InlineKeyboardButton("👤 Profile", callback_data="profile"),
        InlineKeyboardButton("📄 Help", callback_data="help")
    )
    await call.message.edit_text("📋 Main Menu:", reply_markup=markup)