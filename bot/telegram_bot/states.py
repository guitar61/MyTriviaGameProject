from aiogram.dispatcher.filters.state import State, StatesGroup


class TriviaStates(StatesGroup):
    waiting_for_category = State()
    waiting_for_num_questions = State()
    waiting_for_difficulty = State()
    answering_question = State()
