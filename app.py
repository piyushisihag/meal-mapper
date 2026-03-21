from flask import Flask, request, jsonify
import json
import os
import google.generativeai as genai

app = Flask(__name__)

# ─────────────────────────────────────────
#  Configure Gemini
# ─────────────────────────────────────────
genai.configure(api_key="AIzaSyDj9SRugEU0dnUrDGK05UY08DZRU-_iUMA")

# ─────────────────────────────────────────
#  Load recipes from JSON file
# ─────────────────────────────────────────
def load_recipes():
    with open("recipes.json", "r") as f:
        return json.load(f)


# ─────────────────────────────────────────
#  Helper: find matching recipes
# ─────────────────────────────────────────
def find_recipes(user_ingredients):
    recipes = load_recipes()
    user_ingredients = [i.strip().lower() for i in user_ingredients]

    pairings = {
        "maggi masala": ["Lemonade", "Masala Chai", "Cold Coffee"],
        "omelette": ["Butter Toast", "Masala Chai", "Orange Juice"],
        "dal tadka": ["Jeera Rice", "Naan", "Raita"],
        "pasta arrabbiata": ["Garlic Bread", "Lemonade", "Caesar Salad"],
        "aloo paratha": ["Raita", "Masala Chai", "Green Chutney"],
        "poha": ["Masala Chai", "Banana Milkshake"],
        "bread pakora": ["Green Chutney", "Masala Chai"],
        "vada pav": ["Masala Chai", "Tamarind Chutney"],
        "egg fried rice": ["Manchurian", "Spring Roll", "Cold Coffee"],
        "chow mein": ["Manchurian", "Lemonade"],
        "pancake": ["Cold Coffee", "Banana Milkshake"],
        "veg burger": ["French Fries", "Cold Coffee", "Lemonade"],
        "pizza": ["Garlic Bread", "Cold Coffee", "Caesar Salad"],
        "samosa": ["Green Chutney", "Masala Chai", "Tamarind Chutney"],
        "pav bhaji": ["Masala Chai", "Nimbu Pani"],
        "chole bhature": ["Masala Chai", "Lassi"],
        "rajma chawal": ["Raita", "Papad", "Masala Chai"],
        "butter chicken": ["Naan", "Jeera Rice", "Lassi"],
        "chicken biryani": ["Raita", "Salan", "Nimbu Pani"],
        "garlic bread": ["Tomato Soup", "Cold Coffee"],
        "french fries": ["Ketchup", "Cold Coffee", "Lemonade"],
        "cheese sandwich": ["Masala Chai", "Cold Coffee"],
    }

    matched = []

    for recipe in recipes:
        recipe_ingredients = [i.lower() for i in recipe["ingredients"]]
        have = [i for i in recipe_ingredients if i in user_ingredients]
        missing = [i for i in recipe_ingredients if i not in user_ingredients]
        match_percent = int((len(have) / len(recipe_ingredients)) * 100)

        if match_percent >= 20:
            key = recipe["name"].lower()
            matched.append({
                "name": recipe["name"],
                "match_percent": match_percent,
                "have": have,
                "missing": missing,
                "steps": recipe["steps"],
                "pair_with": pairings.get(key, ["Masala Chai", "Lemonade"])
            })

    matched.sort(key=lambda x: x["match_percent"], reverse=True)
    return matched


# ─────────────────────────────────────────
#  Route 1 - health check
# ─────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Meal Mapper API is running!"})


# ─────────────────────────────────────────
#  Route 2 - get recipe suggestions
# ─────────────────────────────────────────
@app.route("/suggest", methods=["POST"])
def suggest():
    data = request.get_json()

    if not data or "ingredients" not in data:
        return jsonify({"error": "Please send ingredients in the request body."}), 400

    ingredients = data["ingredients"]

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
#  Route 3 - get steps for one recipe
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
#  Route 4 - add new recipe
# ─────────────────────────────────────────
@app.route("/add_recipe", methods=["POST"])
def add_recipe():
    data = request.get_json()

    if not data or "name" not in data or "ingredients" not in data or "steps" not in data:
        return jsonify({"error": "Please send name, ingredients and steps."}), 400

    new_recipe = {
        "name": data["name"].strip(),
        "ingredients": [i.strip().lower() for i in data["ingredients"]],
        "steps": data["steps"]
    }

    recipes = load_recipes()

    for r in recipes:
        if r["name"].lower() == new_recipe["name"].lower():
            return jsonify({"error": "Recipe already exists!"}), 409

    recipes.append(new_recipe)
    with open("recipes.json", "w") as f:
        json.dump(recipes, f, indent=2)

    return jsonify({"message": f"Recipe '{new_recipe['name']}' added successfully!"}), 201


# ─────────────────────────────────────────
#  Route 5 - Gemini AI chat
# ─────────────────────────────────────────
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")
    recipe_context = data.get("recipe_context", "")

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""
        You are a friendly and helpful cooking assistant for Meal Mapper, an Indian food app.
        The user is cooking: {recipe_context}
        User question: {user_message}
        Give a short, friendly, practical cooking tip or answer in 2-3 lines max.
        Use simple language. Add a food emoji at the end.
        """
        response = model.generate_content(prompt)
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"reply": f"Sorry I could not answer that! Error: {str(e)}"}), 500


# ─────────────────────────────────────────
#  Route 6 - Get ingredient substitutions
# ─────────────────────────────────────────
@app.route("/substitutes", methods=["POST"])
def substitutes():
    data = request.get_json()
    missing_ingredients = data.get("missing", [])
    recipe_name = data.get("recipe_name", "")

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""
        The user is making {recipe_name} but is missing these ingredients: {', '.join(missing_ingredients)}
        For each missing ingredient suggest 1-2 easy substitutes commonly available in an Indian kitchen.
        Keep it short and practical.
        Format like:
        🔄 ingredient → substitute
        Add a helpful tip at the end.
        """
        response = model.generate_content(prompt)
        return jsonify({"substitutes": response.text})
    except Exception as e:
        return jsonify({"substitutes": f"Could not find substitutes! Error: {str(e)}"}), 500


# ─────────────────────────────────────────
#  Run the app
# ─────────────────────────────────────────
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))