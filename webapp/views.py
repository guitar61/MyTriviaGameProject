from django.shortcuts import render, redirect
from bot.telegram_bot.trivia import TriviaAPI  # Import your TriviaAPI to fetch categories
from webapp.models import Leaderboard, GameSession
import random
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import logging

trivia_api = TriviaAPI()


# Home view
def home(request):
    return render(request, 'webapp/home.html')


# Category selection view
@login_required
def select_category(request):
    categories = trivia_api.fetch_categories()  # Fetch categories from the API
    return render(request, 'webapp/categories.html', {
        "categories": categories,
        "player_name": request.user.username,  # Use the logged-in user's username
    })


# Play trivia view
@login_required
def play_trivia(request):
    # Get parameters from the URL
    category_id = request.GET.get("category")
    player_name = request.GET.get("player_name", request.user.username)
    num_questions = int(request.GET.get("num_questions", 5))
    difficulty = request.GET.get("difficulty", "easy")

    # Validate inputs
    if not category_id or not difficulty:
        messages.error(request, "Invalid category or difficulty selected.")
        return redirect('select_category')

    # Fetch trivia questions
    questions = trivia_api.fetch_questions(num_questions, category_id, difficulty)
    if not questions:
        messages.error(request, "No questions found for the selected category and difficulty.")
        return redirect('select_category')

    # Store game session details
    request.session["questions"] = questions
    request.session["current_score"] = 0
    request.session["current_question"] = 0
    return redirect('show_question')


# Show question view
@login_required
def show_question(request):
    current_question = request.session.get("current_question", 0)
    questions = request.session.get("questions", [])
    total_questions = len(questions)

    if current_question >= total_questions:
        return redirect('show_results')

    question = questions[current_question]
    question_text = question.get("question", "No question available")
    correct_answer = question.get("correct_answer", "")
    answers = question.get("incorrect_answers", [] + [correct_answer])
    random.shuffle(answers)

    # Pass data to the template
    return render(request, 'webapp/question.html', {
        "question_text": question_text,
        "answers": answers,
        "current_index": current_question + 1,
        "total_questions": total_questions
    })


# Check answer view
@login_required
def check_answer(request):
    if request.method == "POST":
        user_answer = request.POST.get("answer")
        questions = request.session.get("questions", [])
        current_index = request.session.get("current_question", 0)
        score = request.session.get("current_score", 0)

        # Validate inputs
        if not user_answer or current_index >= len(questions):
            messages.error(request, "Invalid answer or question index.")
            return redirect('show_results')

        correct_answer = questions[current_index]["correct_answer"]
        if user_answer == correct_answer:
            score += 1

        # Update session state
        request.session["current_score"] = score
        request.session["current_question"] = current_index + 1
        return redirect('show_question')


# Show results view
@login_required
def show_results(request):
    score = request.session.get("current_score", 0)
    total_questions = len(request.session.get("questions", []))
    user = request.user

    try:
        # Create a GameSession entry
        GameSession.objects.create(
            user=user,
            score=score,
            questions_answered=total_questions,
            correct_answers=score
        )

        # Update or create Leaderboard entry
        leaderboard, created = Leaderboard.objects.get_or_create(user=user)
        leaderboard.total_score += score
        leaderboard.games_played += 1

        # Calculate the current game's percentage score
        current_game_percentage = (score / total_questions * 100) if total_questions > 0 else 0
        leaderboard.highest_score = max(leaderboard.highest_score, current_game_percentage)
        leaderboard.save()

    except Exception as e:
        logging.error(f"Error saving game session or updating leaderboard: {e}")

    # Clear session data
    request.session.pop("questions", None)
    request.session.pop("current_score", None)
    request.session.pop("current_question", None)

    return render(request, 'webapp/results.html', {
        "score": score,
        "total_questions": total_questions,
        "player_name": user.username
    })


# Leaderboard view
@login_required
def leaderboard(request):
    # Fetch leaderboard entries sorted by highest score
    leaderboard_entries = Leaderboard.objects.order_by('-highest_score', '-total_score')[:10]

    leaderboard_data = []
    for entry in leaderboard_entries:
        total_questions = entry.games_played * 5
        total_score_percentage = (entry.total_score / total_questions * 100) if total_questions > 0 else 0
        highest_score_percentage = entry.highest_score if entry.highest_score > 0 else 0

        leaderboard_data.append({
            'player': entry.user.username,
            'total_score': round(total_score_percentage, 2),
            'games_played': entry.games_played,
            'highest_score': round(highest_score_percentage, 2)
        })

    return render(request, 'webapp/leaderboard.html', {'leaderboard': leaderboard_data})


# Register view
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f"Account created for {username}. Please log in.")
            return redirect('login')
        else:
            logging.error(f"Form errors: {form.errors}")
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserCreationForm()
    return render(request, 'webapp/register.html', {'form': form})


# Profile view
@login_required
def profile(request):
    user = request.user
    game_sessions = GameSession.objects.filter(user=user).order_by('-date_played')

    total_games = game_sessions.count()
    total_score = sum([session.score for session in game_sessions])
    total_questions = sum([session.questions_answered for session in game_sessions])
    average_accuracy = (total_score / total_questions * 100) if total_questions > 0 else 0

    leaderboard = Leaderboard.objects.filter(user=user).first()

    return render(request, 'webapp/profile.html', {
        'game_sessions': game_sessions,
        'leaderboard': leaderboard,
        'total_games': total_games,
        'total_questions': total_questions,
        'average_accuracy': round(average_accuracy, 2),
    })
