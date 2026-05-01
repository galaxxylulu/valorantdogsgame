from flask import Flask, jsonify, send_file, render_template_string, request
from werkzeug.security import generate_password_hash, check_password_hash
import random
import os
import webbrowser
import json
from datetime import datetime

app = Flask(__name__)

NGROK_DOMAIN = "certainly-ragged-unlikable.ngrok-free.dev"

AGENTS = [
    "Astra", "Breach", "Brimstone", "Chamber", "Clove", "Cypher",
    "Deadlock", "Fade", "Gekko", "Harbor", "Iso", "Jett", "KAYO",
    "Killjoy", "Miks", "Neon", "Omen", "Phoenix", "Raze", "Reyna",
    "Sage", "Skye", "Sova", "Viper", "Yoru", "Vyse",
    "Veto", "Waylay", "Tejo", "Zokdiny"
]

TOTAL_ROUNDS = 8
USERS_FILE = "users.json"
LEADERBOARD_FILE = "leaderboard.json"
MATCH_HISTORY_FILE = "match_history.json"


def current_season():
    return datetime.now().strftime("%Y-%m")


def load_json(filename, fallback):
    if not os.path.exists(filename):
        return fallback
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except:
        return fallback


def save_json(filename, data):
    with open(filename, "w") as file:
        json.dump(data, file, indent=4)


def image_base_name(agent):
    return agent.lower().replace("/", "").replace(" ", "") + "feet"


def find_image_path(agent):
    image_folder = os.path.join(app.static_folder, "images")
    base = image_base_name(agent)

    for ext in [".jpg", ".jpeg", ".png", ".webp"]:
        path = os.path.join(image_folder, base + ext)
        if os.path.exists(path):
            return path

    return None

def find_rank_icon(rank_tier):
    folder = os.path.join(app.static_folder, "ranks")

    for ext in [".png", ".jpg", ".jpeg", ".webp"]:
        path = os.path.join(folder, rank_tier + ext)
        if os.path.exists(path):
            return f"/static/ranks/{rank_tier}{ext}"

    return None




def get_rank(score, mode, seconds=None):
    if mode == "timer" and score == TOTAL_ROUNDS and seconds is not None:
        if seconds <= 15:
            return "radiant", "Radiant Dawg Reaper"
        elif seconds <= 25:
            return "immortal", "Immortal Toe Incel"
        elif seconds <= 35:
            return "ascendant", "Ascendant Feet Analyst"
        elif seconds <= 45:
            return "diamond", "Diamond Dawg Demon"
        elif seconds <= 60:
            return "platinum", "Plat Paws Professor"
        elif seconds <= 75:
            return "gold", "Gold Feet Goblin"
        elif seconds <= 90:
            return "silver", "Silver Shoe Sniffer"
        elif seconds <= 120:
            return "bronze", "Bronze Toe Observer"
        else:
            return "iron", "Iron Sock Inspector"

    if score == 8:
        return "radiant", "Radiant Dawg Reaper"
    elif score == 7:
        return "immortal", "Immortal Toe Incel"
    elif score == 6:
        return "ascendant", "Ascendant Feet Analyst"
    elif score == 5:
        return "diamond", "Diamond Dawg Demon"
    elif score == 4:
        return "platinum", "Plat Paws Professor"
    elif score == 3:
        return "gold", "Gold Feet Goblin"
    elif score == 2:
        return "silver", "Silver Shoe Sniffer"
    elif score == 1:
        return "bronze", "Bronze Toe Observer"
    else:
        return "iron", "Iron Sock Inspector"

    
@app.route("/")
def home():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<title>Valorant Dogs Guesser</title>

<style>
:root {
    --red: #ff4655;
    --dark: #0f1923;
    --panel: #1f2a36;
    --panel2: #111a24;
    --white: #ece8e1;
    --green: #50dc8c;
}

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background:
        linear-gradient(135deg, rgba(255,70,85,0.08), transparent 30%),
        radial-gradient(circle at top, #26384a, #0f1923 60%);
    color: var(--white);
    min-height: 100vh;
}

.app {
    width: 1180px;
    margin: auto;
    padding: 26px 0;
}

.topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(236,232,225,0.15);
    padding-bottom: 14px;
}

.brand h1 {
    margin: 0;
    font-size: 42px;
    letter-spacing: 2px;
    text-transform: uppercase;
}

.brand p {
    margin: 4px 0 0;
    color: var(--red);
}

.nav {
    display: flex;
    gap: 10px;
}

.nav button,
button {
    border: 1px solid var(--red);
    background: rgba(15,25,35,0.92);
    color: var(--white);
    padding: 12px 16px;
    border-radius: 3px;
    cursor: pointer;
    font-weight: bold;
    text-transform: uppercase;
}

.nav button.active,
button:hover {
    background: var(--red);
}

.panel {
    margin-top: 22px;
    background: rgba(31,42,54,0.95);
    border: 1px solid rgba(255,70,85,0.35);
    box-shadow: 0 0 35px rgba(255,70,85,0.18);
    padding: 24px;
}

.hidden {
    display: none;
}

.auth-box {
    width: 440px;
    margin: 50px auto;
    text-align: center;
}

input {
    padding: 14px;
    width: 310px;
    margin: 8px;
    background: #0f1923;
    color: white;
    border: 1px solid var(--red);
    font-size: 16px;
}

.mode-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 18px;
}

.mode-card {
    background: #111a24;
    border: 1px solid rgba(236,232,225,0.12);
    padding: 22px;
    cursor: pointer;
    min-height: 140px;
}

.mode-card:hover {
    border-color: var(--red);
    transform: translateY(-2px);
}

.mode-card h2 {
    color: var(--red);
    margin-top: 0;
    text-transform: uppercase;
}

.scoreboard {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 18px;
    font-size: 18px;
}

.game-card {
    display: flex;
    gap: 28px;
}

.image-box {
    width: 680px;
    height: 430px;
    background: #0c131b;
    border: 2px solid rgba(255,70,85,0.55);
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
}

#gameCanvas {
    max-width: 100%;
    max-height: 100%;
}

.options {
    flex: 1;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 9px;
    max-height: 430px;
    overflow-y: auto;
}

#message {
    font-size: 22px;
    font-weight: bold;
    text-align: center;
    margin-top: 20px;
}

.rank-display {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 14px;
    margin: 12px;
}

.rank-display img {
    width: 70px;
    height: 70px;
    object-fit: contain;
}

.leader-controls {
    display: flex;
    justify-content: center;
    gap: 10px;
    margin: 18px;
}

.leader-row {
    display: grid;
    grid-template-columns: 60px 1fr 100px 110px 260px;
    gap: 10px;
    padding: 12px;
    border-bottom: 1px solid rgba(236,232,225,0.12);
    align-items: center;
}

.leader-row.header {
    color: var(--red);
    font-weight: bold;
    text-transform: uppercase;
}

.rank-icon-small {
    width: 34px;
    height: 34px;
    object-fit: contain;
    vertical-align: middle;
    margin-right: 8px;
}

.history-card {
    display: grid;
    grid-template-columns: 70px 1fr 120px 120px 290px 170px;
    gap: 10px;
    padding: 14px;
    border-bottom: 1px solid rgba(236,232,225,0.12);
    align-items: center;
}

.history-card.header {
    color: var(--red);
    font-weight: bold;
    text-transform: uppercase;
}

.history-rank-icon {
    width: 38px;
    height: 38px;
    object-fit: contain;
    vertical-align: middle;
    margin-right: 8px;
}

.small {
    opacity: 0.75;
    font-size: 14px;
}

.danger {
    color: var(--red);
}

.badge {
    color: var(--green);
    font-weight: bold;
}
</style>
</head>

<body>
<div class="app">

    <div class="topbar">
        <div class="brand">
            <h1>Valorant Dogs Guesser</h1>
            <p>Whose dogs are these uwu</p>
        </div>

        <div class="nav">
            <button id="tabPlay" onclick="showTab('play')">Play</button>
            <button id="tabLeaderboard" onclick="showTab('leaderboard')">Leaderboard</button>
            <button id="tabHistory" onclick="showTab('history')" class="hidden">Match History</button>
            <button id="tabLogout" onclick="logout()" class="hidden">Logout</button>
        </div>
    </div>

    <div id="authScreen" class="panel auth-box">
        <h2>Login / Create Account</h2>
        <input id="authUsername" maxlength="18" placeholder="username">
        <input id="authPassword" type="password" placeholder="password">
        <br>
        <button onclick="register()">Create Account</button>
        <button onclick="login()">Login</button>
        <p id="authMessage" class="danger"></p>
    </div>

    <div id="playTab" class="hidden">
        <div id="modeScreen" class="panel">
            <h2>Select Mode</h2>

            <div class="mode-grid">
                <div class="mode-card" onclick="startGame('normal')">
                    <h2>Normal</h2>
                    <p>The classic ankle investigation. 8 rounds. Score-based rank.</p>
                </div>

                <div class="mode-card" onclick="startGame('pixel')">
                    <h2>Pixel Mode</h2>
                    <p>Images get pixelated. Guess from crunchy evidence.</p>
                </div>

                <div class="mode-card" onclick="startGame('timer')">
                    <h2>Timer Mode</h2>
                    <p>Finish 8 rounds as fast as possible. Perfect scores rank by speed.</p>
                </div>
            </div>
        </div>

        <div id="gameScreen" class="panel hidden">
            <div class="scoreboard">
                <span id="playerText">Player</span>
                <span id="modeText">Mode</span>
                <span id="roundText">Round 1/8</span>
                <span id="scoreText">Score: 0</span>
                <span id="timerText">Time: N/A</span>
            </div>

            <div class="game-card">
                <div class="image-box">
                    <canvas id="gameCanvas" width="680" height="430"></canvas>
                </div>

                <div class="options">
                    {% for agent in agents %}
                        <button onclick="makeGuess('{{ agent }}')">{{ agent }}</button>
                    {% endfor %}
                </div>
            </div>

            <p id="message"></p>
        </div>

        <div id="endScreen" class="panel hidden">
            <h2>Game Over</h2>
            <p id="finalScore"></p>
            <p id="finalTime"></p>

            <div class="rank-display">
                <img id="rankIcon" src="" onerror="this.style.display='none'">
                <h2 id="rankText"></h2>
            </div>

            <button onclick="showModeScreen()">Play Again</button>
            <button onclick="showTab('leaderboard')">View Leaderboard</button>
            <button onclick="showTab('history')">View Match History</button>
        </div>
    </div>

    <div id="leaderboardTab" class="panel hidden">
        <h2>Monthly Leaderboard</h2>
        <p class="small">Resets automatically every month. Current season: <span id="seasonText"></span></p>

        <div class="leader-controls">
            <button onclick="loadLeaderboard('normal')">Normal</button>
            <button onclick="loadLeaderboard('pixel')">Pixel</button>
            <button onclick="loadLeaderboard('timer')">Timer</button>
        </div>

        <div class="leader-row header">
            <div>#</div>
            <div>Name</div>
            <div>Score</div>
            <div>Time</div>
            <div>Rank</div>
        </div>

        <div id="leaderboardRows"></div>
    </div>

    <div id="historyTab" class="panel hidden">
        <h2>Match History</h2>
        <p class="small">Your Valorant-style career archive. Sort by game mode.</p>

        <div class="rank-display">
            <img id="profileRankIcon" src="" onerror="this.style.display='none'">
            <div>
                <h2 id="profileUsername">Player</h2>
                <p id="profileRankText" class="badge">No rank yet</p>
            </div>
        </div>

        <div class="leader-controls">
            <button onclick="loadMatchHistory('all')">All</button>
            <button onclick="loadMatchHistory('normal')">Normal</button>
            <button onclick="loadMatchHistory('pixel')">Pixel</button>
            <button onclick="loadMatchHistory('timer')">Timer</button>
        </div>

        <div class="history-card header">
            <div>#</div>
            <div>Mode</div>
            <div>Score</div>
            <div>Time</div>
            <div>Rank</div>
            <div>Date</div>
        </div>

        <div id="historyRows"></div>
    </div>

</div>

<script>
let currentUser = "";
let roundAgents = [];
let currentRound = 0;
let score = 0;
let totalRounds = {{ total_rounds }};
let currentCorrect = "";
let locked = false;
let currentMode = "normal";
let startTime = 0;
let timerInterval = null;
let elapsedSeconds = 0;

const canvas = document.getElementById("gameCanvas");
const ctx = canvas.getContext("2d");

function showTab(tab) {
    document.getElementById("playTab").classList.add("hidden");
    document.getElementById("leaderboardTab").classList.add("hidden");
    document.getElementById("historyTab").classList.add("hidden");

    document.getElementById("tabPlay").classList.remove("active");
    document.getElementById("tabLeaderboard").classList.remove("active");
    document.getElementById("tabHistory").classList.remove("active");

    if (tab === "play") {
        document.getElementById("playTab").classList.remove("hidden");
        document.getElementById("tabPlay").classList.add("active");
    } else if (tab === "leaderboard") {
        document.getElementById("leaderboardTab").classList.remove("hidden");
        document.getElementById("tabLeaderboard").classList.add("active");
        loadLeaderboard("normal");
    } else if (tab === "history") {
        document.getElementById("historyTab").classList.remove("hidden");
        document.getElementById("tabHistory").classList.add("active");
        loadMatchHistory("all");
    }
}

function enterSite(username) {
    currentUser = username;

    document.getElementById("authScreen").classList.add("hidden");
    document.getElementById("playTab").classList.remove("hidden");
    document.getElementById("tabLogout").classList.remove("hidden");
    document.getElementById("tabHistory").classList.remove("hidden");

    showTab("play");
}

async function register() {
    const username = document.getElementById("authUsername").value.trim();
    const password = document.getElementById("authPassword").value;

    const res = await fetch("/register", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({username, password})
    });

    const data = await res.json();

    if (data.success) {
        enterSite(data.username);
    } else {
        document.getElementById("authMessage").innerText = data.error;
    }
}

async function login() {
    const username = document.getElementById("authUsername").value.trim();
    const password = document.getElementById("authPassword").value;

    const res = await fetch("/login", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({username, password})
    });

    const data = await res.json();

    if (data.success) {
        enterSite(data.username);
    } else {
        document.getElementById("authMessage").innerText = data.error;
    }
}

function logout() {
    currentUser = "";

    document.getElementById("authScreen").classList.remove("hidden");
    document.getElementById("playTab").classList.add("hidden");
    document.getElementById("leaderboardTab").classList.add("hidden");
    document.getElementById("historyTab").classList.add("hidden");
    document.getElementById("tabLogout").classList.add("hidden");
    document.getElementById("tabHistory").classList.add("hidden");
}

function showModeScreen() {
    stopTimer();

    document.getElementById("modeScreen").classList.remove("hidden");
    document.getElementById("gameScreen").classList.add("hidden");
    document.getElementById("endScreen").classList.add("hidden");

    showTab("play");
}

async function startGame(mode) {
    currentMode = mode;

    const res = await fetch("/new-game");
    const data = await res.json();

    if (!data.roundAgents || data.roundAgents.length === 0) {
        alert("No images found. Check static/images folder.");
        return;
    }

    roundAgents = data.roundAgents;
    currentRound = 0;
    score = 0;
    currentCorrect = roundAgents[0];
    locked = false;
    elapsedSeconds = 0;

    document.getElementById("modeScreen").classList.add("hidden");
    document.getElementById("gameScreen").classList.remove("hidden");
    document.getElementById("endScreen").classList.add("hidden");
    document.getElementById("message").innerText = "";

    document.getElementById("playerText").innerText = `Player: ${currentUser}`;
    document.getElementById("modeText").innerText = `Mode: ${mode.toUpperCase()}`;

    loadImageToCanvas(currentCorrect);
    updateText();

    if (mode === "timer") {
        startTimer();
    } else {
        stopTimer();
    }
}

function startTimer() {
    startTime = performance.now();

    timerInterval = setInterval(() => {
        elapsedSeconds = (performance.now() - startTime) / 1000;
        document.getElementById("timerText").innerText = `Time: ${elapsedSeconds.toFixed(2)}s`;
    }, 50);
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
    }

    timerInterval = null;
}

function updateText() {
    document.getElementById("roundText").innerText = `Round ${currentRound + 1}/${totalRounds}`;
    document.getElementById("scoreText").innerText = `Score: ${score}`;

    if (currentMode !== "timer") {
        document.getElementById("timerText").innerText = "Time: N/A";
    }
}

function loadImageToCanvas(agent) {
    const img = new Image();

    img.onload = function() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = "#0c131b";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        if (currentMode === "pixel") {
            drawPixelated(img);
        } else {
            drawNormal(img);
        }
    };

    img.src = "/image/" + encodeURIComponent(agent) + "?v=" + Date.now();
}

function drawNormal(img) {
    ctx.imageSmoothingEnabled = true;

    const scale = Math.min(canvas.width / img.width, canvas.height / img.height);
    const w = img.width * scale;
    const h = img.height * scale;
    const x = (canvas.width - w) / 2;
    const y = (canvas.height - h) / 2;

    ctx.drawImage(img, x, y, w, h);
}

function drawPixelated(img) {
    const tiny = document.createElement("canvas");
    tiny.width = 42;
    tiny.height = 27;

    const tinyCtx = tiny.getContext("2d");
    tinyCtx.imageSmoothingEnabled = true;
    tinyCtx.drawImage(img, 0, 0, tiny.width, tiny.height);

    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(tiny, 0, 0, canvas.width, canvas.height);
}

function makeGuess(guess) {
    if (locked) return;

    locked = true;

    if (guess === currentCorrect) {
        score++;
        document.getElementById("message").innerText = `Correct. It was ${currentCorrect}`;
        document.getElementById("message").style.color = "#50dc8c";
    } else {
        document.getElementById("message").innerText = `Wrong. It was ${currentCorrect}`;
        document.getElementById("message").style.color = "#ff4655";
    }

    currentRound++;
    updateText();

    setTimeout(() => {
        if (currentRound >= totalRounds) {
            endGame();
        } else {
            currentCorrect = roundAgents[currentRound];
            document.getElementById("message").innerText = "";
            loadImageToCanvas(currentCorrect);
            updateText();
            locked = false;
        }
    }, 800);
}

async function endGame() {
    stopTimer();

    const seconds = currentMode === "timer" ? Number(elapsedSeconds.toFixed(2)) : null;

    const saveRes = await fetch("/save-score", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            username: currentUser,
            mode: currentMode,
            score: score,
            seconds: seconds
        })
    });

      const data = await saveRes.json();

    document.getElementById("gameScreen").classList.add("hidden");
    document.getElementById("endScreen").classList.remove("hidden");

    document.getElementById("finalScore").innerText = `Score: ${score}/${totalRounds}`;
    document.getElementById("finalTime").innerText = seconds ? `Time: ${seconds}s` : "";
    document.getElementById("rankText").innerText = data.rank_name;

    const icon = document.getElementById("rankIcon");

    if (data.rank_icon) {
        icon.src = data.rank_icon;
        icon.style.display = "block";
    } else {
        icon.style.display = "none";
    }
}

async function loadLeaderboard(mode) {
    const res = await fetch("/leaderboard/" + mode);
    const data = await res.json();

    document.getElementById("seasonText").innerText = data.season;

    const rows = document.getElementById("leaderboardRows");
    rows.innerHTML = "";

    if (data.entries.length === 0) {
        rows.innerHTML = "<p>No scores yet. Be the first leaderboard gremlin.</p>";
        return;
    }

    data.entries.forEach((entry, index) => {
        const timeText = entry.seconds === null || entry.seconds === undefined ? "N/A" : entry.seconds + "s";

        const row = document.createElement("div");
        row.className = "leader-row";

        row.innerHTML = `
            <div>${index + 1}</div>
            <div>${entry.username}</div>
            <div>${entry.score}/${totalRounds}</div>
            <div>${timeText}</div>
            <div>
                <img class="rank-icon-small" src="/rank-icon/${entry.rank_tier}" onerror="this.style.display='none'">
                ${entry.rank_name}
            </div>
        `;

        rows.appendChild(row);
    });
}

async function loadMatchHistory(mode) {
    if (!currentUser) return;

    const res = await fetch("/match-history/" + encodeURIComponent(currentUser) + "/" + mode);
    const data = await res.json();

    document.getElementById("profileUsername").innerText = currentUser;

    const profileIcon = document.getElementById("profileRankIcon");
    profileIcon.style.display = "block";
    profileIcon.src = data.best_rank_icon;

    let modeLabel = mode === "all" ? "Overall" : mode.toUpperCase();
document.getElementById("profileRankText").innerText = `${modeLabel} Rank: ${data.best_rank_name}`;

    const rows = document.getElementById("historyRows");
    rows.innerHTML = "";

    if (data.matches.length === 0) {
        rows.innerHTML = "<p>No matches yet. Go create some evidence.</p>";
        return;
    }

    data.matches.forEach((match, index) => {
        const timeText = match.seconds === null || match.seconds === undefined ? "N/A" : match.seconds + "s";
        const date = new Date(match.time).toLocaleDateString();

        const row = document.createElement("div");
        row.className = "history-card";

        row.innerHTML = `
            <div>${index + 1}</div>
            <div>${match.mode.toUpperCase()}</div>
            <div>${match.score}/${totalRounds}</div>
            <div>${timeText}</div>
            <div>
                <img class="history-rank-icon" src="/rank-icon/${match.rank_tier}" onerror="this.style.display='none'">
                ${match.rank_name}
            </div>
            <div>${date}</div>
        `;

        rows.appendChild(row);
    });
}
</script>
</body>
</html>
    """, agents=AGENTS, total_rounds=TOTAL_ROUNDS)


@app.route("/register", methods=["POST"])
def register():
    data = request.json

    username = data.get("username", "").strip()[:18]
    password = data.get("password", "")

    if len(username) < 2:
        return jsonify({"success": False, "error": "Username too short."})

    if len(password) < 4:
        return jsonify({"success": False, "error": "Password must be at least 4 characters."})

    users = load_json(USERS_FILE, {})
    key = username.lower()

    if key in users:
        return jsonify({"success": False, "error": "Username already exists."})

    users[key] = {
        "username": username,
        "password_hash": generate_password_hash(password),
        "created": datetime.now().isoformat()
    }

    save_json(USERS_FILE, users)

    return jsonify({"success": True, "username": username})

@app.route("/rank-icon/<tier>")
def rank_icon(tier):
    path = find_rank_icon(tier)

    if path:
        return send_file(os.path.join(app.static_folder, path.replace("/static/", "")))

    return "", 404

@app.route("/login", methods=["POST"])
def login():
    data = request.json

    username = data.get("username", "").strip()
    password = data.get("password", "")

    users = load_json(USERS_FILE, {})
    key = username.lower()

    if key not in users:
        return jsonify({"success": False, "error": "Account not found."})

    if not check_password_hash(users[key]["password_hash"], password):
        return jsonify({"success": False, "error": "Wrong password."})

    return jsonify({"success": True, "username": users[key]["username"]})


@app.route("/new-game")
def new_game():
    available_agents = [agent for agent in AGENTS if find_image_path(agent)]

    if len(available_agents) < TOTAL_ROUNDS:
        round_agents = available_agents
    else:
        round_agents = random.sample(available_agents, TOTAL_ROUNDS)

    return jsonify({"roundAgents": round_agents})


@app.route("/image/<agent>")
def image(agent):
    path = find_image_path(agent)

    if path is None:
        return "Image not found. Check static/images and filename.", 404

    return send_file(path)


@app.route("/save-score", methods=["POST"])
def save_score():
    data = request.json

    username = data.get("username", "Anonymous").strip()[:18]
    mode = data.get("mode", "normal")
    score = int(data.get("score", 0))
    seconds = data.get("seconds", None)

    if seconds is not None:
        seconds = float(seconds)

    if mode not in ["normal", "pixel", "timer"]:
        mode = "normal"

    if username == "":
        username = "Anonymous"

    rank_tier, rank_name = get_rank(score, mode, seconds)

    season = current_season()
    now = datetime.now().isoformat()

    new_entry = {
        "username": username,
        "mode": mode,
        "score": score,
        "seconds": seconds,
        "rank_tier": rank_tier,
        "rank_name": rank_name,
        "season": season,
        "time": now
    }

    # 1. ALWAYS save every match to match history
    match_history = load_json(MATCH_HISTORY_FILE, [])
    match_history.append(new_entry)
    save_json(MATCH_HISTORY_FILE, match_history)

    # 2. ONLY save best score to leaderboard
    leaderboard = load_json(LEADERBOARD_FILE, [])
    updated = False

    for i, entry in enumerate(leaderboard):
        same_player = entry.get("username", "").lower() == username.lower()
        same_mode = entry.get("mode") == mode
        same_season = entry.get("season") == season

        if same_player and same_mode and same_season:
            old_score = entry.get("score", 0)
            old_seconds = entry.get("seconds", None)

            if mode != "timer":
                is_better = score > old_score
            else:
                if score > old_score:
                    is_better = True
                elif score == old_score:
                    if old_seconds is None:
                        is_better = True
                    elif seconds is not None and seconds < old_seconds:
                        is_better = True
                    else:
                        is_better = False
                else:
                    is_better = False

            if is_better:
                leaderboard[i] = new_entry

            updated = True
            break

    if not updated:
        leaderboard.append(new_entry)

    save_json(LEADERBOARD_FILE, leaderboard)

    return jsonify({
        "success": True,
        "rank_tier": rank_tier,
        "rank_name": rank_name,
        "rank_icon": find_rank_icon(rank_tier)
    }) 


@app.route("/leaderboard/<mode>")
def leaderboard(mode):
    if mode not in ["normal", "pixel", "timer"]:
        mode = "normal"

    season = current_season()

    entries = [
        entry for entry in load_json(LEADERBOARD_FILE, [])
        if entry.get("mode") == mode and entry.get("season") == season
    ]

    best_by_user = {}

    for entry in entries:
        username_key = entry.get("username", "").lower()

        if username_key not in best_by_user:
            best_by_user[username_key] = entry
        else:
            old = best_by_user[username_key]

            if mode != "timer":
                if entry.get("score", 0) > old.get("score", 0):
                    best_by_user[username_key] = entry
            else:
                entry_score = entry.get("score", 0)
                old_score = old.get("score", 0)

                entry_seconds = entry.get("seconds")
                old_seconds = old.get("seconds")

                if entry_score > old_score:
                    best_by_user[username_key] = entry
                elif entry_score == old_score:
                    if old_seconds is None:
                        best_by_user[username_key] = entry
                    elif entry_seconds is not None and entry_seconds < old_seconds:
                        best_by_user[username_key] = entry

    entries = list(best_by_user.values())

    if mode == "timer":
        entries = sorted(
            entries,
            key=lambda x: (
                -(x.get("score", 0)),
                x.get("seconds") if x.get("seconds") is not None else 999999
            )
        )
    else:
        entries = sorted(
            entries,
            key=lambda x: (
                -(x.get("score", 0)),
                x.get("time", "")
            )
        )

    return jsonify({
        "season": season,
        "entries": entries[:20]
    })


@app.route("/match-history/<username>/<mode>")
def match_history(username, mode):
    username_key = username.strip().lower()

    all_entries = [
       entry for entry in load_json(MATCH_HISTORY_FILE, [])
        if entry.get("username", "").lower() == username_key
    ]

    # matches displayed in the table
    if mode == "all":
        entries = all_entries
    else:
        entries = [
            entry for entry in all_entries
            if entry.get("mode") == mode
        ]

    entries = sorted(
        entries,
        key=lambda x: x.get("time", ""),
        reverse=True
    )

    # rank displayed at the top
    if mode == "all":
        rank_entries = all_entries
    else:
        rank_entries = [
            entry for entry in all_entries
            if entry.get("mode") == mode
        ]

    if rank_entries:
        best_entry = sorted(
            rank_entries,
            key=lambda x: (
                x.get("score", 0),
                -float(x.get("seconds", 999999) or 999999)
            ),
            reverse=True
        )[0]

        best_rank_tier = best_entry.get("rank_tier", "iron")
        best_rank_name = best_entry.get("rank_name", "Iron Sock Inspector")
    else:
        best_rank_tier = "iron"
        best_rank_name = "Unranked Sock Civilian"

    # add icon path to each match row
    for entry in entries:
        entry["rank_icon"] = find_rank_icon(entry.get("rank_tier", "iron"))

    return jsonify({
        "matches": entries[:50],
        "best_rank_tier": best_rank_tier,
        "best_rank_name": best_rank_name,
        "best_rank_icon": find_rank_icon(best_rank_tier),
        "selected_mode": mode
    })

def migrate_old_leaderboard_to_match_history():
    old_entries = load_json(LEADERBOARD_FILE, [])
    current_history = load_json(MATCH_HISTORY_FILE, [])

    if len(current_history) == 0 and len(old_entries) > 0:
        save_json(MATCH_HISTORY_FILE, old_entries)
        print("Migrated old leaderboard entries into match_history.json")

@app.route("/ngrok-skip-browser-warning")
def skip_warning():
    return home()
def migrate_old_leaderboard_format():
    leaderboard = load_json(LEADERBOARD_FILE, [])
    fixed_entries = []

    for entry in leaderboard:
        score = int(entry.get("score", 0))
        mode = entry.get("mode", "normal")
        seconds = entry.get("seconds", None)
        season = entry.get("season", current_season())

        rank_tier = entry.get("rank_tier")
        rank_name = entry.get("rank_name")

        if not rank_tier or not rank_name:
            rank_tier, rank_name = get_rank(score, mode, seconds)

        fixed_entries.append({
            "username": entry.get("username", "Anonymous").strip()[:18],
            "mode": mode,
            "score": score,
            "seconds": seconds,
            "rank_tier": rank_tier,
            "rank_name": rank_name,
            "season": season,
            "time": entry.get("time", datetime.now().isoformat())
        })

    # remove duplicate users per mode/season
    best = {}

    for entry in fixed_entries:
        key = (
            entry["username"].lower(),
            entry["mode"],
            entry["season"]
        )

        old = best.get(key)

        if old is None:
            best[key] = entry
        else:
            if entry["mode"] != "timer":
                if entry["score"] > old["score"]:
                    best[key] = entry
            else:
                entry_time = entry["seconds"] or 999999
                old_time = old["seconds"] or 999999

                if entry["score"] > old["score"]:
                    best[key] = entry
                elif entry["score"] == old["score"] and entry_time < old_time:
                    best[key] = entry

    save_json(LEADERBOARD_FILE, list(best.values()))
    print("Leaderboard migrated and cleaned.")

migrate_old_leaderboard_to_match_history()
migrate_old_leaderboard_format()

if __name__ == "__main__":
 
    app.run(host="0.0.0.0", port=5000, debug=False)
