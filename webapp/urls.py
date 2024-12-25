from django.urls import path
from webapp import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('', views.home, name='home'),
    path('categories/', views.select_category, name='select_category'),
    path('play/', views.play_trivia, name='play_trivia'),
    path('question/', views.show_question, name='show_question'),
    path('check/', views.check_answer, name='check_answer'),
    path('results/', views.show_results, name='show_results'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),

    # Authentication paths
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='webapp/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='webapp/logout.html'), name='logout'),
    path('profile/', views.profile, name='profile'),


]
