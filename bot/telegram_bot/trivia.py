import requests


class TriviaAPI:
    BASE_URL = "https://opentdb.com"

    def fetch_categories(self):
        """
        Fetches a list of trivia categories.
        Returns:
            list: A list of trivia categories or an empty list on error.
        """
        try:
            response = requests.get(f"{self.BASE_URL}/api_category.php")
            response.raise_for_status()
            return response.json().get("trivia_categories", [])
        except requests.RequestException as e:
            print(f"Error fetching categories: {e}")
            return []

    def fetch_questions(self, amount=5, category=None, difficulty=None):
        """
        Fetches trivia questions based on the specified parameters.

        Args:
            amount (int): Number of questions to fetch.
            category (int): Category ID of the questions.
            difficulty (str): Difficulty level ("easy", "medium", "hard").

        Returns:
            list: A list of trivia questions or an empty list on error.
        """
        params = {"amount": amount, "type": "multiple"}
        if category:
            params["category"] = category
        if difficulty:
            params["difficulty"] = difficulty
        try:
            response = requests.get(f"{self.BASE_URL}/api.php", params=params)
            response.raise_for_status()
            return response.json().get("results", [])
        except requests.RequestException as e:
            print(f"Error fetching questions: {e}")
            return []
