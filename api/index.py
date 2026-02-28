from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import math
import random
import os

app = Flask(__name__, template_folder='../templates')
app.secret_key = "super_secret_key"

# Подключение (используем вашу рабочую ссылку)
uri = "mongodb+srv://pristinskiy7_db_user:6VqyOpCLpYisKRwL@cluster0.vuq8m7h.mongodb.net/puzzle_game?retryWrites=true&w=majority&appName=Cluster0"

try:
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = client.puzzle_game
    client.admin.command('ping')
    print("✅ База подключена. Пользователи активны.")
except Exception as e:
    print(f"❌ Ошибка базы: {e}")

# Стили для страниц входа/регистрации
FORM_STYLE = '''
<style>
    body { background: #0f172a; color: white; font-family: 'Segoe UI', sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
    .card { background: #1e293b; padding: 40px; border-radius: 20px; border-bottom: 4px solid #38bdf8; box-shadow: 0 10px 30px rgba(0,0,0,0.5); width: 320px; text-align: center; }
    input { width: 100%; padding: 12px; margin: 10px 0; border-radius: 8px; border: 1px solid #334155; background: #0f172a; color: white; box-sizing: border-box; }
    button { width: 100%; padding: 12px; background: #4ecca3; border: none; border-radius: 50px; color: #0f172a; font-weight: bold; cursor: pointer; margin-top: 10px; transition: 0.3s; }
    button:hover { background: #38bdf8; transform: translateY(-2px); }
    a { color: #94a3b8; text-decoration: none; font-size: 0.9em; margin-top: 20px; display: block; }
</style>
'''


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for('play'))
    return redirect(url_for('login'))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = db.players.find_one({"player_id": username})
        if user and check_password_hash(user['password'], password):
            session["user_id"] = username
            return redirect(url_for('play'))
        return "Ошибка входа: проверьте логин/пароль", 401
    return FORM_STYLE + '''
        <div class="card">
            <h2>ВХОД НА АРЕНУ</h2>
            <form method="post">
                <input name="username" placeholder="Никнейм" required>
                <input name="password" type="password" placeholder="Пароль" required>
                <button type="submit" style="background: #38bdf8;">ВОЙТИ</button>
            </form>
            <a href="/register">Стать новым участником</a>
        </div>
    '''


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        team = request.form.get("team", "Free")
        if db.players.find_one({"player_id": username}):
            return "Этот никнейм уже занят!", 400
        db.players.insert_one({
            "player_id": username,
            "password": generate_password_hash(password),
            "team_id": team, "total_xp": 0, "record_xp": 0
        })
        return redirect(url_for('login'))
    return FORM_STYLE + '''
        <div class="card">
            <h2>РЕГИСТРАЦИЯ</h2>
            <form method="post">
                <input name="username" placeholder="Ваш Никнейм" required>
                <input name="password" type="password" placeholder="Ваш Пароль" required>
                <input name="team" placeholder="Ваша Команда">
                <button type="submit">СОЗДАТЬ АККАУНТ</button>
            </form>
            <a href="/login">Уже есть профиль? Войти</a>
        </div>
    '''


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route("/play", methods=["GET", "POST"])
def play():
    if "user_id" not in session:
        return redirect(url_for('login'))

    player = db.players.find_one({"player_id": session["user_id"]})
    if not player: return redirect(url_for('logout'))

    # Расчет коэффициента
    coeff = round(player.get("total_xp", 0) - player.get("record_xp", 0), 1)

    width = random.randint(4, 10)
    height = random.randint(4, 10)
    is_random = True
    if request.method == "POST":
        width = int(request.form.get("width", 4))
        height = int(request.form.get("height", 4))
        is_random = False

    return render_template("play.html", width=width, height=height, is_random=is_random, coefficient=coeff)


@app.route("/save_result", methods=["POST"])
def save_result():
    if "user_id" not in session: return jsonify({"status": "error"}), 401
    data = request.json
    earned_xp = data.get('xp', 0)
    db.players.update_one(
        {"player_id": session["user_id"]},
        {"$inc": {"total_xp": earned_xp}, "$max": {"record_xp": earned_xp}}
    )
    return jsonify({"status": "success"})


@app.route("/leaderboard")
def leaderboard():
    players_cursor = db.players.find()
    leaderboard_data = []
    for p in players_cursor:
        leaderboard_data.append({
            "id": p["player_id"],
            "team": p.get("team_id", "Free"),
            "pure_xp": round(p.get("total_xp", 0) - p.get("record_xp", 0), 1)
        })
    leaderboard_data.sort(key=lambda x: x['pure_xp'], reverse=True)
    return render_template("leaderboard.html", players=leaderboard_data)


#if __name__ == "__main__":
    app.run(debug=True)