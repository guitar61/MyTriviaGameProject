from django.db import models
from django.contrib.auth.models import User


# Track individual trivia games for authenticated users
class GameSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date_played = models.DateTimeField(auto_now_add=True)
    score = models.IntegerField()  # Correct answers count
    questions_answered = models.IntegerField()  # Total questions attempted
    correct_answers = models.IntegerField(default=0)  # Correct answers count (new field)

    def __str__(self):
        return f"{self.user.username} - {self.date_played} - {self.score}"


# Leaderboard for cumulative stats per user
class Leaderboard(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    total_score = models.IntegerField(default=0)  # Cumulative correct answers
    games_played = models.IntegerField(default=0)
    highest_score = models.FloatField(default=0.0)  # Percentage of correct answers

    def __str__(self):
        if self.user:
            return f"{self.user.username} - Highest Score: {self.highest_score} - Games Played: {self.games_played}"
        return "No User - Entry Incomplete"
