import random
import requests
from flask_migrate import Migrate
from flask import Flask, render_template, redirect, url_for, session, flash, request
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, HiddenField
from wtforms.validators import DataRequired, EqualTo, Length
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from sqlalchemy.ext.hybrid import hybrid_property

# Initialize the app and CSRF protection
app = Flask(__name__)
app.config['SECRET_KEY'] = '5029bb313de90469e9d3a9457f3b0b4521511ba085c914040249ee2e8fd6f2dc'
csrf = CSRFProtect(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trivia.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    total_score = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=0)
    date_registered = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    highest_score_value = db.Column(db.Float, default=0.0)
    average_score_value = db.Column(db.Float, default=0.0)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    @hybrid_property
    def highest_score(self):
        return self.highest_score_value

    @highest_score.setter
    def highest_score(self, value):
        self.highest_score_value = value

    @hybrid_property
    def average_score(self):
        return self.average_score_value

    @average_score.setter
    def average_score(self, value):
        self.average_score_value = value

    def update_scores(self):
        games = Game.query.filter_by(user_id=self.id).all()
        if not games:
            self.highest_score = 0.0
            self.average_score = 0.0
        else:
            self.highest_score = max(game.percentage_score for game in games)
            self.average_score = sum(game.percentage_score for game in games) / len(games)


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    correct_answers = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    date_played = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='games')

    @property
    def percentage_score(self):
        if self.total_questions == 0:
            return 0
        return (self.correct_answers / self.total_questions) * 100


# Forms
class LogoutForm(FlaskForm):
    submit = SubmitField('Log Out')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')


class QuestionForm(FlaskForm):
    csrf_token = HiddenField()


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=25)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[DataRequired(), EqualTo('password', message='Passwords must match')]
    )
    submit = SubmitField('Register')


# Routes
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user'] = user.username
            session['user_id'] = user.id
            flash("Logged in successfully!", "success")
            return redirect(url_for('profile'))
        else:
            flash("Invalid username or password.", "danger")
    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash("Username already taken. Please choose a different one.", "danger")
        else:
            new_user = User(username=form.username.data)
            new_user.set_password(form.password.data)
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/profile')
def profile():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])  # Fetch user from the database
        if user:
            return render_template('profile.html', user=user)  # Pass the user object
        else:
            flash("User not found. Please log in again.", "warning")
            return redirect(url_for('login'))
    flash("You need to log in to access the profile.", "danger")
    return redirect(url_for('login'))



@app.route('/logout', methods=['GET', 'POST'])
def logout():
    form = LogoutForm()
    if form.validate_on_submit():
        session.clear()
        flash("You have been logged out.", "info")
        return redirect(url_for('home'))
    return render_template('logout.html', form=form)


@app.route('/categories')
def categories():
    if 'user_id' not in session:
        flash("You need to log in to access categories.", "danger")
        return redirect(url_for('login'))

    response = requests.get("https://opentdb.com/api_category.php")
    if response.status_code == 200:
        data = response.json()
        categories = data.get("trivia_categories", [])
        return render_template('categories.html', categories=categories)
    flash("Failed to fetch categories. Please try again later.", "danger")
    return redirect(url_for('home'))


@app.route('/questions/<int:category_id>', methods=['GET', 'POST'])
def questions(category_id):
    form = QuestionForm()

    questions = session.get('questions', [])
    current_index = session.get('current_index', 0)
    feedback_given = session.get('feedback_given', False)

    if not questions:
        response = requests.get(f"https://opentdb.com/api.php?amount=5&category={category_id}&type=multiple")
        if response.status_code == 200:
            data = response.json()
            questions = data.get("results", [])
            if not questions:
                flash("No questions available for this category.", "warning")
                return redirect(url_for('categories'))
            session['questions'] = questions
            session['current_index'] = 0
            session['score'] = 0
        else:
            flash("Failed to fetch questions. Please try again later.", "danger")
            return redirect(url_for('categories'))

    if form.validate_on_submit() and not feedback_given:
        selected_answer = request.form.get('answer')
        correct_answer = questions[current_index]['correct_answer']

        if selected_answer == correct_answer:
            flash("Correct!", "success")
            session['score'] += 1
        else:
            flash(f"Wrong! The correct answer was: {correct_answer}", "danger")

        session['feedback_given'] = True

    if feedback_given and request.args.get('next') == 'true':
        session['feedback_given'] = False
        current_index += 1
        session['current_index'] = current_index

        if current_index >= len(questions):
            return redirect(url_for('results'))

    if current_index < len(questions):
        question_data = questions[current_index]
        answers = question_data["incorrect_answers"] + [question_data["correct_answer"]]
        random.shuffle(answers)

        return render_template(
            'question.html',
            form=form,
            question_text=question_data["question"],
            answers=answers,
            current_index=current_index + 1,
            total_questions=len(questions),
            category_id=category_id
        )

    flash("Unexpected error. Returning to categories.", "danger")
    return redirect(url_for('categories'))


@app.route('/results')
def results():
    player_name = session.get('user', 'Guest')
    score = session.get('score', 0)
    total_questions = len(session.get('questions', []))

    if total_questions == 0:
        flash("No game data found. Please play a game first.", "warning")
        return redirect(url_for('categories'))

    if 'user_id' in session:
        user = User.query.get(session['user_id'])

        if user:
            try:
                user.total_score += score
                user.total_questions += total_questions

                current_percentage = (score / total_questions) * 100
                if current_percentage > user.highest_score:
                    user.highest_score = current_percentage

                new_game = Game(
                    user_id=user.id,
                    correct_answers=score,
                    total_questions=total_questions
                )
                db.session.add(new_game)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                flash("An error occurred while saving your game data.", "danger")
                return redirect(url_for('categories'))
        else:
            flash("User not found. Please log in again.", "warning")
            return redirect(url_for('login'))

    session.pop('questions', None)
    session.pop('current_index', None)
    session.pop('score', None)

    return render_template(
        'results.html',
        player_name=player_name,
        score=score,
        total_questions=total_questions
    )


@app.route('/leaderboard')
def leaderboard():
    sort_field = request.args.get('sort', 'highest_score')
    valid_fields = {
        'highest_score': User.highest_score_value,
        'average_score': User.average_score_value,
        'total_questions': User.total_questions,
    }

    if sort_field not in valid_fields:
        sort_field = 'highest_score'

    try:
        users = User.query.filter(User.total_questions > 0).order_by(valid_fields[sort_field].desc()).all()
    except Exception as e:
        flash("An error occurred while loading the leaderboard.", "danger")
        users = []

    return render_template('leaderboard.html', leaderboard=users)


if __name__ == '__main__':
    app.run(debug=True)
