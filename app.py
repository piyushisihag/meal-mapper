from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

# ─────────────────────────────────────────
#  Load recipes from JSON file
# ─────────────────────────────────────────
def load_recipes():
    # Make sure recipes.json is in the same folder as app.py
    with open("recipes.json", "r") as f:
        return json.load(f)


# ─────────────────────────────────────────
#  Helper: find matching recipes
# ─────────────────────────────────────────
def find_recipes(user_ingredients):
    """
    user_ingredients : list of strings  e.g. ["egg", "milk", "flour"]
    Returns a list of recipe dicts that can be made (fully or partially).
    """
    recipes = load_recipes()
    user_ingredients = [i.strip().lower() for i in user_ingredients]

    matched = []

    for recipe in recipes:
        recipe_ingredients = [i.lower() for i in recipe["ingredients"]]

        # How many recipe ingredients does the user have?
        have = [i for i in recipe_ingredients if i in user_ingredients]
        missing = [i for i in recipe_ingredients if i not in user_ingredients]

        match_percent = int((len(have) / len(recipe_ingredients)) * 100)

        # Only suggest if user has at least 50 % of the ingredients
        if match_percent >= 50:
            matched.append({
                "name": recipe["name"],
                "match_percent": match_percent,
                "have": have,
                "missing": missing,
                "steps": recipe["steps"]
            })

    # Sort: best match first
    matched.sort(key=lambda x: x["match_percent"], reverse=True)
    return matched


# ─────────────────────────────────────────
#  Route 1 – health check
# ─────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Meal Mapper API is running!"})


# ─────────────────────────────────────────
#  Route 2 – get recipe suggestions
#  Botpress will POST here with ingredients
# ─────────────────────────────────────────
@app.route("/suggest", methods=["POST"])
def suggest():
    data = request.get_json()

    if not data or "ingredients" not in data:
        return jsonify({"error": "Please send ingredients in the request body."}), 400

    ingredients = data["ingredients"]

    # Handle string input: "egg, milk, flour" → ["egg", "milk", "flour"]
    if isinstance(ingredients, str):
        ingredients = [i.strip() for i in ingredients.split(",")]

    if not isinstance(ingredients, list) or len(ingredients) == 0:
        return jsonify({"error": "ingredients must be a non-empty list."}), 400

    results = find_recipes(ingredients)

    if not results:
        return jsonify({
            "message": "Sorry, no recipes found with those ingredients.",
            "recipes": []
        })

    return jsonify({
        "message": f"Found {len(results)} recipe(s) for you!",
        "recipes": results
    })


# ─────────────────────────────────────────
#  Route 3 – get steps for one recipe
#  Botpress sends the recipe name
# ─────────────────────────────────────────
@app.route("/steps", methods=["POST"])
def steps():
    data = request.get_json()

    if not data or "recipe_name" not in data:
        return jsonify({"error": "Please send recipe_name in the request body."}), 400

    recipe_name = data["recipe_name"].strip().lower()
    recipes = load_recipes()

    for recipe in recipes:
        if recipe["name"].lower() == recipe_name:
            return jsonify({
                "name": recipe["name"],
                "steps": recipe["steps"]
            })

    return jsonify({"error": f"Recipe '{data['recipe_name']}' not found."}), 404


# ─────────────────────────────────────────
#  Run the app
# ─────────────────────────────────────────
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))