from django.db import models


class User(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=150, null=True, blank=True)
    full_name = models.CharField(max_length=150, default="Unknown")
    date_joined = models.DateTimeField(auto_now_add=True)
    games_played = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    highest_score = models.IntegerField(default=0)
    last_played = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.full_name

    @property
    def average_score(self):
        if self.games_played > 0:
            return self.correct_answers / self.games_played
        return 0
