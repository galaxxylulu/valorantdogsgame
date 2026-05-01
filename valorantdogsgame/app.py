from flask import Flask, jsonify, send_file, render_template_string, request
from werkzeug.security import generate_password_hash, check_password_hash
import random
import os
import json
from datetime import datetime, date

app = Flask(__name__)

# =========================
# CONFIG
# =========================

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
RR_FILE = "rr.json"
FRIENDS_FILE = "friends.json"
FRIEND_REQUESTS_FILE = "friend_requests.json"
DAILIES_FILE = "dailies.json"
MESSAGES_FILE = "messages.json"

RANK_ORDER = [
    "iron", "bronze", "silver", "gold", "platinum",
    "diamond", "ascendant", "immortal", "radiant"
]

RANK_NAMES = {
    "iron": "Iron Sock Inspector",
    "bronze": "Bronze Toe Observer",
    "silver": "Silver Shoe Sniffer",
    "gold": "Gold Feet Goblin",
    "platinum": "Plat Paws Professor",
    "diamond": "Diamond Dawg Demon",
    "ascendant": "Ascendant Feet Analyst",
    "immortal": "Immortal Toe Incel",
    "radiant": "Radiant Dawg Reaper"
}

HIGH_RANKS = ["diamond", "ascendant", "immortal", "radiant"]
VALID_MODES = ["normal", "pixel", "timer", "flash"]


# =========================
# BASIC HELPERS
# =========================

def current_season():
    return datetime.now().strftime("%Y-%m")


def today_key():
    return date.today().isoformat()


def load_json(filename, fallback):
    if not os.path.exists(filename):
        return fallback

    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        print(f"Could not load {filename}: {e}")
        return fallback


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def clean_username(username):
    username = str(username or "").strip()[:18]
    return username if username else "Anonymous"


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


def tier_from_rank_name(rank_name):
    text = str(rank_name or "").lower()

    if "radiant" in text:
        return "radiant"
    if "immortal" in text:
        return "immortal"
    if "ascendant" in text:
        return "ascendant"
    if "diamond" in text:
        return "diamond"
    if "plat" in text:
        return "platinum"
    if "gold" in text:
        return "gold"
    if "silver" in text:
        return "silver"
    if "bronze" in text:
        return "bronze"

    return "iron"


def get_rank(score, mode, seconds=None):
    score = int(score or 0)

    if mode == "timer" and score >= TOTAL_ROUNDS and seconds is not None:
        seconds = float(seconds)

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

    if score >= 8:
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


def is_better_score(new_entry, old_entry):
    if old_entry is None:
        return True

    new_score = int(new_entry.get("score", 0))
    old_score = int(old_entry.get("score", 0))
    mode = new_entry.get("mode", "normal")

    if mode == "timer":
        new_seconds = new_entry.get("seconds")
        old_seconds = old_entry.get("seconds")

        new_seconds = float(new_seconds) if new_seconds is not None else 999999
        old_seconds = float(old_seconds) if old_seconds is not None else 999999

        if new_score > old_score:
            return True
        if new_score == old_score and new_seconds < old_seconds:
            return True
        return False

    return new_score > old_score


def normalize_entry(entry):
    """
    Converts your OLD leaderboard format:
    {
        "username": "cepsooep",
        "score": 8,
        "rank": "Radiant Dawg Scholar",
        "time": "..."
    }

    Into the NEW format:
    {
        "username": "...",
        "mode": "normal",
        "score": 8,
        "seconds": null,
        "rank_tier": "radiant",
        "rank_name": "Radiant Dawg Scholar",
        "season": "2026-05",
        "time": "..."
    }
    """
    if not isinstance(entry, dict):
        return None

    if "username" not in entry:
        return None

    username = clean_username(entry.get("username"))
    mode = entry.get("mode", "normal")

    if mode not in VALID_MODES:
        mode = "normal"

    try:
        score = int(entry.get("score", 0))
    except:
        score = 0

    seconds = entry.get("seconds", None)
    if seconds is not None:
        try:
            seconds = float(seconds)
        except:
            seconds = None

    # IMPORTANT:
    # Old entries had no season. Use current season so they show on the current monthly leaderboard.
    season = entry.get("season", current_season())
    time = entry.get("time", datetime.now().isoformat())

    rank_tier = entry.get("rank_tier")
    rank_name = entry.get("rank_name")

    if not rank_tier or not rank_name:
        old_rank = entry.get("rank")

        if old_rank:
            rank_tier = tier_from_rank_name(old_rank)
            rank_name = old_rank
        else:
            rank_tier, rank_name = get_rank(score, mode, seconds)

    rank_tier = rank_tier if rank_tier in RANK_ORDER else tier_from_rank_name(rank_name)
    rank_name = rank_name or RANK_NAMES.get(rank_tier, "Iron Sock Inspector")

    return {
        "username": username,
        "mode": mode,
        "score": score,
        "seconds": seconds,
        "rank_tier": rank_tier,
        "rank_name": rank_name,
        "season": season,
        "time": time
    }


# =========================
# MIGRATIONS / AUTO FIX
# =========================

def migrate_old_leaderboard_to_match_history():
    leaderboard = load_json(LEADERBOARD_FILE, [])
    history = load_json(MATCH_HISTORY_FILE, [])

    if not isinstance(leaderboard, list):
        leaderboard = []

    if not isinstance(history, list):
        history = []

    history_keys = set()
    for raw in history:
        fixed = normalize_entry(raw)
        if fixed:
            history_keys.add((
                fixed["username"].lower(),
                fixed["mode"],
                fixed["score"],
                fixed["seconds"],
                fixed["time"]
            ))

    added = 0
    for raw in leaderboard:
        fixed = normalize_entry(raw)
        if not fixed:
            continue

        key = (
            fixed["username"].lower(),
            fixed["mode"],
            fixed["score"],
            fixed["seconds"],
            fixed["time"]
        )

        if key not in history_keys:
            history.append(fixed)
            history_keys.add(key)
            added += 1

    if added > 0:
        save_json(MATCH_HISTORY_FILE, history)
        print(f"Added {added} leaderboard entries into match history.")


def migrate_old_leaderboard_format():
    leaderboard = load_json(LEADERBOARD_FILE, [])
    fixed_entries = []

    valid_modes = ["normal", "pixel", "timer", "flash"]

    def rank_tier_from_name(rank_name):
        r = str(rank_name).lower()
        if "radiant" in r:
            return "radiant"
        if "immortal" in r:
            return "immortal"
        if "ascendant" in r:
            return "ascendant"
        if "diamond" in r:
            return "diamond"
        if "plat" in r:
            return "platinum"
        if "gold" in r:
            return "gold"
        if "silver" in r:
            return "silver"
        if "bronze" in r:
            return "bronze"
        return "iron"

    def is_better(new, old):
        if old is None:
            return True

        if new["mode"] == "timer":
            new_seconds = new["seconds"] if new["seconds"] is not None else 999999
            old_seconds = old["seconds"] if old["seconds"] is not None else 999999

            return (
                new["score"] > old["score"]
                or (new["score"] == old["score"] and new_seconds < old_seconds)
            )

        return new["score"] > old["score"]

    for entry in leaderboard:
        if not isinstance(entry, dict):
            continue

        username = str(entry.get("username", "")).strip()[:18]
        if username == "":
            continue

        mode = entry.get("mode", "normal")
        if mode not in valid_modes:
            mode = "normal"

        try:
            score = int(entry.get("score", 0))
        except:
            score = 0

        score = max(0, min(score, TOTAL_ROUNDS))

        seconds = entry.get("seconds", None)
        if seconds is not None:
            try:
                seconds = float(seconds)
            except:
                seconds = None

        old_rank_name = entry.get("rank_name") or entry.get("rank")

        if old_rank_name:
            rank_name = old_rank_name
            rank_tier = entry.get("rank_tier") or rank_tier_from_name(rank_name)
        else:
            rank_tier, rank_name = get_rank(score, mode, seconds)

        fixed_entries.append({
            "username": username,
            "mode": mode,
            "score": score,
            "seconds": seconds,
            "rank_tier": rank_tier,
            "rank_name": rank_name,
            "time": entry.get("time", datetime.now().isoformat())
        })

    best = {}

    for entry in fixed_entries:
        key = (entry["username"].lower(), entry["mode"])

        if is_better(entry, best.get(key)):
            best[key] = entry

    save_json(LEADERBOARD_FILE, list(best.values()))
    print("Leaderboard cleaned into all-time format.")

def migrate_old_match_history_format():
    history = load_json(MATCH_HISTORY_FILE, [])

    if not isinstance(history, list):
        history = []

    fixed_history = []

    for raw in history:
        fixed = normalize_entry(raw)
        if fixed:
            fixed_history.append(fixed)

    save_json(MATCH_HISTORY_FILE, fixed_history)
    print("Match history auto-fixed and migrated.")


def rebuild_rr_from_history_if_missing():
    """
    Creates rr.json from match history only if rr.json does not exist.
    This avoids overwriting people's live ranked progress.
    """
    if os.path.exists(RR_FILE):
        return

    history = load_json(MATCH_HISTORY_FILE, [])
    rr_data = {}

    sorted_history = sorted(history, key=lambda x: x.get("time", ""))

    for entry in sorted_history:
        username = clean_username(entry.get("username"))
        if username.lower() == "anonymous":
            continue
        update_rr(username, entry.get("score", 0), entry.get("mode", "normal"), save=False, rr_data=rr_data)

    save_json(RR_FILE, rr_data)
    print("RR file created from match history.")


# =========================
# RR / RANKED SYSTEM
# =========================

def rr_change_for_match(score, mode, seconds=None, combo_points=0):
    score = int(score or 0)
    combo_points = int(combo_points or 0)

    if score >= 8:
        change = 28
    elif score == 7:
        change = 22
    elif score == 6:
        change = 16
    elif score == 5:
        change = 9
    elif score == 4:
        change = 0
    elif score == 3:
        change = -8
    elif score == 2:
        change = -13
    else:
        change = -18

    if mode == "timer" and seconds is not None:
        seconds = float(seconds)
        if score >= 8 and seconds <= 35:
            change += 7
        elif score >= 8 and seconds <= 50:
            change += 4

    if mode == "flash" and score >= 6:
        change += 3

    if combo_points >= 12:
        change += 4
    elif combo_points >= 6:
        change += 2

    return max(-25, min(35, change))


def update_rr(username, score, mode="normal", seconds=None, combo_points=0, save=True, rr_data=None):
    if rr_data is None:
        rr_data = load_json(RR_FILE, {})

    key = clean_username(username).lower()

    if key not in rr_data:
        rr_data[key] = {
            "username": clean_username(username),
            "rank": "iron",
            "rr": 50,
            "peak_rank": "iron",
            "games_played": 0,
            "wins": 0,
            "losses": 0,
            "badges": []
        }

    player = rr_data[key]

    old_rank = player.get("rank", "iron")
    old_rr = int(player.get("rr", 50))

    if old_rank not in RANK_ORDER:
        old_rank = "iron"

    change = rr_change_for_match(score, mode, seconds, combo_points)

    new_rank = old_rank
    new_rr = old_rr + change
    rank_up = False
    rank_down = False

    while new_rr >= 100 and new_rank != "radiant":
        new_rr -= 100
        new_rank = RANK_ORDER[RANK_ORDER.index(new_rank) + 1]
        rank_up = True

    if new_rank == "radiant" and new_rr > 100:
        new_rr = 100

    while new_rr < 0 and new_rank != "iron":
        new_rank = RANK_ORDER[RANK_ORDER.index(new_rank) - 1]
        new_rr += 100
        rank_down = True

    if new_rank == "iron" and new_rr < 0:
        new_rr = 0

    player["rank"] = new_rank
    player["rr"] = int(new_rr)
    player["games_played"] = int(player.get("games_played", 0)) + 1

    if int(score or 0) >= 5:
        player["wins"] = int(player.get("wins", 0)) + 1
    else:
        player["losses"] = int(player.get("losses", 0)) + 1

    peak = player.get("peak_rank", "iron")
    if peak not in RANK_ORDER:
        peak = "iron"

    if RANK_ORDER.index(new_rank) > RANK_ORDER.index(peak):
        player["peak_rank"] = new_rank

    rr_data[key] = player

    if save:
        save_json(RR_FILE, rr_data)

    return {
        "username": player.get("username", username),
        "old_rank": old_rank,
        "old_rr": old_rr,
        "rank": new_rank,
        "rr": int(new_rr),
        "rr_change": change,
        "rank_up": rank_up,
        "rank_down": rank_down,
        "rank_name": RANK_NAMES.get(new_rank, "Iron Sock Inspector"),
        "rank_icon": find_rank_icon(new_rank),
        "badges": player.get("badges", [])
    }


def get_player_rr(username):
    rr_data = load_json(RR_FILE, {})
    key = clean_username(username).lower()

    if key not in rr_data:
        return {
            "username": clean_username(username),
            "rank": "iron",
            "rr": 50,
            "peak_rank": "iron",
            "games_played": 0,
            "wins": 0,
            "losses": 0,
            "badges": []
        }

    player = rr_data[key]
    rank = player.get("rank", "iron")
    if rank not in RANK_ORDER:
        rank = "iron"

    player["rank"] = rank
    player["rank_name"] = RANK_NAMES.get(rank, "Iron Sock Inspector")
    player["rank_icon"] = find_rank_icon(rank)

    return player


# =========================
# DAILY CHALLENGES
# =========================

def get_daily_challenges():
    today = today_key()
    dailies = load_json(DAILIES_FILE, {})

    if dailies.get("date") != today:
        random.seed(today)

        possible = [
            {
                "id": "perfect_normal",
                "text": "Get a perfect score in Normal mode",
                "mode": "normal",
                "target_score": 8
            },
            {
                "id": "perfect_pixel",
                "text": "Get a perfect score in Pixel mode",
                "mode": "pixel",
                "target_score": 8
            },
            {
                "id": "flash_6",
                "text": "Score 6+ in Flash Round",
                "mode": "flash",
                "target_score": 6
            },
            {
                "id": "timer_7",
                "text": "Score 7+ in Timer mode",
                "mode": "timer",
                "target_score": 7
            },
            {
                "id": "daily_grind",
                "text": "Play 3 matches today",
                "mode": "any",
                "target_games": 3
            }
        ]

        chosen = random.sample(possible, 3)

        dailies = {
            "date": today,
            "challenges": chosen,
            "completed": {}
        }

        save_json(DAILIES_FILE, dailies)

    return dailies


def update_daily_progress(username, mode, score):
    username = clean_username(username)
    key = username.lower()
    today = today_key()

    dailies = get_daily_challenges()
    completed = dailies.setdefault("completed", {})
    user_completed = completed.setdefault(key, [])

    history = load_json(MATCH_HISTORY_FILE, [])
    today_games = [
        e for e in history
        if e.get("username", "").lower() == key and str(e.get("time", "")).startswith(today)
    ]

    newly_completed = []

    for challenge in dailies.get("challenges", []):
        cid = challenge["id"]

        if cid in user_completed:
            continue

        done = False

        if "target_score" in challenge:
            target_mode = challenge.get("mode")
            if (target_mode == mode or target_mode == "any") and int(score or 0) >= int(challenge["target_score"]):
                done = True

        if "target_games" in challenge:
            if len(today_games) >= int(challenge["target_games"]):
                done = True

        if done:
            user_completed.append(cid)
            newly_completed.append(challenge)

    completed[key] = user_completed
    dailies["completed"] = completed
    save_json(DAILIES_FILE, dailies)

    badge_awarded = False

    if len(user_completed) >= len(dailies.get("challenges", [])) and len(dailies.get("challenges", [])) > 0:
        rr_data = load_json(RR_FILE, {})
        player = rr_data.setdefault(key, {
            "username": username,
            "rank": "iron",
            "rr": 50,
            "peak_rank": "iron",
            "games_played": 0,
            "wins": 0,
            "losses": 0,
            "badges": []
        })

        badges = player.setdefault("badges", [])
        badge_name = f"Feet Grinder {today}"

        if badge_name not in badges:
            badges.append(badge_name)
            badge_awarded = True

        rr_data[key] = player
        save_json(RR_FILE, rr_data)

    return {
        "dailies": dailies,
        "newly_completed": newly_completed,
        "badge_awarded": badge_awarded
    }


# =========================
# MAIN PAGE
# =========================

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
    --yellow: #ffd166;
    --blue: #7dd3fc;
    }
.rank-glow-iron { filter: drop-shadow(0 0 6px #888); }
.rank-glow-bronze { filter: drop-shadow(0 0 8px #cd7f32); }
.rank-glow-silver { filter: drop-shadow(0 0 9px #c0c0c0); }
.rank-glow-gold { filter: drop-shadow(0 0 10px gold) drop-shadow(0 0 18px orange); }
.rank-glow-platinum { filter: drop-shadow(0 0 10px #00ffd5); }
.rank-glow-diamond { filter: drop-shadow(0 0 12px #4da6ff); }
.rank-glow-ascendant { filter: drop-shadow(0 0 13px #b84dff); }
.rank-glow-immortal { filter: drop-shadow(0 0 14px red); }

.rank-glow-radiant {
    filter: drop-shadow(0 0 15px gold) drop-shadow(0 0 28px #ff4655);
    animation: radiantPulse 1.5s infinite alternate;
}

@keyframes radiantPulse {
    from { transform: scale(1); }
    to { transform: scale(1.08); }
}

* {
    box-sizing: border-box;
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
    max-width: calc(100vw - 30px);
    margin: auto;
    padding: 26px 0;
}

.topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(236,232,225,0.15);
    padding-bottom: 14px;
    gap: 20px;
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
    flex-wrap: wrap;
    justify-content: flex-end;
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
    display: none !important;
}

.auth-box {
    width: 440px;
    max-width: 100%;
    margin: 50px auto;
    text-align: center;
}

input {
    padding: 14px;
    width: 310px;
    max-width: calc(100% - 20px);
    margin: 8px;
    background: #0f1923;
    color: white;
    border: 1px solid var(--red);
    font-size: 16px;
}

.mode-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 18px;
}

.mode-card {
    background: #111a24;
    border: 1px solid rgba(236,232,225,0.12);
    padding: 22px;
    cursor: pointer;
    min-height: 150px;
    transition: 0.18s;
}

.mode-card:hover {
    border-color: var(--red);
    transform: translateY(-2px);
    box-shadow: 0 0 22px rgba(255,70,85,0.2);
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
    flex-wrap: wrap;
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
    flex-wrap: wrap;
}

.rank-display img {
    width: 80px;
    height: 80px;
    object-fit: contain;
}

.leader-controls {
    display: flex;
    justify-content: center;
    gap: 10px;
    margin: 18px;
    flex-wrap: wrap;
}

.leader-row {
    display: grid;
    grid-template-columns: 60px 1fr 90px 90px 90px 250px;
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
    grid-template-columns: 60px 95px 100px 90px 90px 240px 160px;
    gap: 10px;
    padding: 14px;
    border-bottom: 1px solid rgba(236,232,225,0.12);
    align-items: center;
    background: rgba(15,25,35,0.35);
    margin-bottom: 6px;
}

.history-card.header {
    color: var(--red);
    font-weight: bold;
    text-transform: uppercase;
    border-left: none !important;
}

.history-card.good-game {
    border-left: 6px solid var(--green);
}

.history-card.bad-game {
    border-left: 6px solid var(--red);
}

.history-card.mid-game {
    border-left: 6px solid var(--yellow);
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

.rank-glow {
    filter: drop-shadow(0 0 10px #ffd166) drop-shadow(0 0 18px #ff4655);
    animation: glowPulse 1.5s infinite alternate;
}

@keyframes glowPulse {
    from { transform: scale(1); opacity: 0.85; }
    to { transform: scale(1.08); opacity: 1; }
}

.rankup-overlay {
    position: fixed;
    inset: 0;
    background: rgba(15,25,35,0.88);
    z-index: 100;
    display: none;
    align-items: center;
    justify-content: center;
    text-align: center;
}

.rankup-card {
    border: 2px solid var(--red);
    background: #111a24;
    padding: 42px;
    box-shadow: 0 0 60px rgba(255,70,85,0.45);
    animation: popIn 0.35s ease-out;
}

.rankup-card h1 {
    color: var(--red);
    font-size: 56px;
    margin: 0 0 10px;
}

@keyframes popIn {
    from { transform: scale(0.7); opacity: 0; }
    to { transform: scale(1); opacity: 1; }
}

.rr-bar-wrap {
    width: 260px;
    height: 18px;
    border: 1px solid rgba(236,232,225,0.25);
    background: #0f1923;
    margin: 8px auto;
    overflow: hidden;
}

.rr-bar {
    height: 100%;
    background: linear-gradient(90deg, var(--red), var(--yellow));
    width: 0%;
    transition: 0.4s;
}

.daily-grid,
.friend-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 10px;
}

.daily-card,
.friend-card {
    background: #111a24;
    border: 1px solid rgba(236,232,225,0.12);
    padding: 14px;
}

.completed {
    border-color: var(--green);
    color: var(--green);
}

.friend-card {
    display: grid;
    grid-template-columns: 1fr 140px 150px;
    align-items: center;
    gap: 10px;
}

.profile-grid {
    display: grid;
    grid-template-columns: 360px 1fr;
    gap: 20px;
}

.stat-box {
    background: #111a24;
    padding: 14px;
    border: 1px solid rgba(236,232,225,0.12);
    margin-bottom: 10px;
}

.flash-cover {
    color: var(--red);
    font-size: 28px;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 2px;
}

@media (max-width: 900px) {
    .mode-grid {
        grid-template-columns: 1fr 1fr;
    }

    .game-card {
        flex-direction: column;
    }

    .image-box {
        width: 100%;
    }

    .profile-grid {
        grid-template-columns: 1fr;
    }

    .leader-row,
    .history-card {
        grid-template-columns: 1fr;
    }
}
</style>
</head>

<body>
<div class="rankup-overlay" id="rankupOverlay" onclick="hideRankup()">
    <div class="rankup-card">
        <h1 id="rankupTitle">RANK UP</h1>
        <p id="rankupText">You ranked up.</p>
        <p class="small">Click anywhere to close.</p>
    </div>
</div>

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
            <button id="tabFriends" onclick="showTab('friends')" class="hidden">Friends</button>
            <button id="tabDaily" onclick="showTab('daily')" class="hidden">Daily</button>
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

            <div class="rank-display">
                <img id="homeRankIcon" src="" onerror="this.style.display='none'">
                <div>
                    <h2 id="homeRankText">Unranked Sock Civilian</h2>
                    <div class="rr-bar-wrap">
                        <div class="rr-bar" id="homeRRBar"></div>
                    </div>
                    <p id="homeRRText" class="small">50 / 100 RR</p>
                </div>
            </div>

            <div class="mode-grid">
                <div class="mode-card" onclick="startGame('normal')">
                    <h2>Normal</h2>
                    <p>The classic ankle investigation. 8 rounds. Ranked RR enabled.</p>
                </div>

                <div class="mode-card" onclick="startGame('pixel')">
                    <h2>Pixel Mode</h2>
                    <p>Images get pixelated. Guess from pixelated dawgs.</p>
                </div>

                <div class="mode-card" onclick="startGame('timer')">
                    <h2>Timer Mode</h2>
                    <p>Finish fast hehe. Correct streaks build combo multiplier points.</p>
                </div>

                <div class="mode-card" onclick="startGame('flash')">
                    <h2>Flash Round</h2>
                    <p>Get flashed by various dawgs for a second then dissapears.</p>
                </div>
            </div>
        </div>

        <div id="gameScreen" class="panel hidden">
            <div class="scoreboard">
                <span id="playerText">Player</span>
                <span id="modeText">Mode</span>
                <span id="roundText">Round 1/8</span>
                <span id="scoreText">Score: 0</span>
                <span id="comboText">Combo: 0</span>
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
            <p id="finalCombo"></p>

            <div class="rank-display">
                <img id="rankIcon" src="" onerror="this.style.display='none'">
                <div>
                    <h2 id="rankText"></h2>
                    <p id="rrChangeText" class="badge"></p>
                    <div class="rr-bar-wrap">
                        <div class="rr-bar" id="endRRBar"></div>
                    </div>
                    <p id="endRRText" class="small"></p>
                </div>
            </div>

            <p id="dailyResult" class="badge"></p>

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
            <button onclick="loadLeaderboard('flash')">Flash</button>
        </div>

        <div class="leader-row header">
            <div>#</div>
            <div>Name</div>
            <div>Score</div>
            <div>Time</div>
            <div>RR</div>
            <div>Rank</div>
        </div>

        <div id="leaderboardRows"></div>
    </div>

    <div id="historyTab" class="panel hidden">
        <h2>Match History</h2>
        <p class="small">Green = good game, yellow = neutral, red = the match cooked you.</p>

        <div class="rank-display">
            <img id="profileRankIcon" src="" onerror="this.style.display='none'">
            <div>
                <h2 id="profileUsername">Player</h2>
                <p id="profileRankText" class="badge">No rank yet</p>
                <div class="rr-bar-wrap">
                    <div class="rr-bar" id="profileRRBar"></div>
                </div>
                <p id="profileRRText" class="small"></p>
            </div>
        </div>

        <div class="leader-controls">
            <button onclick="loadMatchHistory('all')">All</button>
            <button onclick="loadMatchHistory('normal')">Normal</button>
            <button onclick="loadMatchHistory('pixel')">Pixel</button>
            <button onclick="loadMatchHistory('timer')">Timer</button>
            <button onclick="loadMatchHistory('flash')">Flash</button>
        </div>

        <div class="history-card header">
            <div>#</div>
            <div>Mode</div>
            <div>Score</div>
            <div>Time</div>
            <div>RR</div>
            <div>Rank</div>
            <div>Date</div>
        </div>

        <div id="historyRows"></div>
    </div>

    <div id="friendsTab" class="panel hidden">
        <h2>Friends</h2>
        <p class="small">Add friends by username</p>

        <input id="friendName" placeholder="friend username">
        <button onclick="addFriend()">Send Friend Request</button>
        <p id="friendMessage" class="badge"></p>

        <h3>Friend Requests</h3>
        <div id="friendRequestRows" class="friend-grid"></div>

        <h3>Your Friends</h3>
        <div id="friendsRows" class="friend-grid"></div>

        <div id="friendProfile" class="panel hidden">
            <h2 id="friendProfileName">Friend</h2>
            <div class="profile-grid">
                <div>
                    <div class="rank-display">
                        <img id="friendRankIcon" src="" onerror="this.style.display='none'">
                        <div>
                            <h2 id="friendRankText"></h2>
                            <div class="rr-bar-wrap">
                                <div class="rr-bar" id="friendRRBar"></div>
                            </div>
                            <p id="friendRRText" class="small"></p>
                        </div>
                    </div>
                    <div id="friendStats"></div>
                </div>
                <div>
                    <h3>Recent Matches</h3>
                    <div id="friendHistoryRows"></div>

                    <h3 id="chatTitle">Chat</h3>
                    <div id="chatBox" style="height:220px; overflow-y:auto; background:#0f1923; padding:10px; margin-top:10px; border:1px solid rgba(255,70,85,0.35);"></div>

                    <input id="chatInput" placeholder="type message..." style="width:78%;">
                    <button onclick="sendMessage()">Send</button>
                    <p id="chatStatus" class="small"></p>
                </div>
            </div>
        </div>
    </div>

    <div id="dailyTab" class="panel hidden">
        <h2>Daily Challenges</h2>
        <p class="small">Complete all dailies to earn today's Feet Grinder badge.</p>
        <div id="dailyRows" class="daily-grid"></div>
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
let combo = 0;
let maxCombo = 0;
let comboPoints = 0;
let flashTimeout = null;
let currentChatFriend = "";
let lastMessageCount = 0;
let chatInterval = null;

const canvas = document.getElementById("gameCanvas");
const ctx = canvas.getContext("2d");

function showTab(tab) {
    document.getElementById("playTab").classList.add("hidden");
    document.getElementById("leaderboardTab").classList.add("hidden");
    document.getElementById("historyTab").classList.add("hidden");
    document.getElementById("friendsTab").classList.add("hidden");
    document.getElementById("dailyTab").classList.add("hidden");

    document.getElementById("tabPlay").classList.remove("active");
    document.getElementById("tabLeaderboard").classList.remove("active");
    document.getElementById("tabHistory").classList.remove("active");
    document.getElementById("tabFriends").classList.remove("active");
    document.getElementById("tabDaily").classList.remove("active");

    if (tab === "play") {
        document.getElementById("playTab").classList.remove("hidden");
        document.getElementById("tabPlay").classList.add("active");
        loadProfileHome();
    } else if (tab === "leaderboard") {
        document.getElementById("leaderboardTab").classList.remove("hidden");
        document.getElementById("tabLeaderboard").classList.add("active");
        loadLeaderboard("normal");
    } else if (tab === "history") {
        document.getElementById("historyTab").classList.remove("hidden");
        document.getElementById("tabHistory").classList.add("active");
        loadMatchHistory("all");
    } else if (tab === "friends") {
        document.getElementById("friendsTab").classList.remove("hidden");
        document.getElementById("tabFriends").classList.add("active");
        loadFriends();
    } else if (tab === "daily") {
        document.getElementById("dailyTab").classList.remove("hidden");
        document.getElementById("tabDaily").classList.add("active");
        loadDailies();
    }
}

function enterSite(username) {
    currentUser = username;

    document.getElementById("authScreen").classList.add("hidden");
    document.getElementById("playTab").classList.remove("hidden");
    document.getElementById("tabLogout").classList.remove("hidden");
    document.getElementById("tabHistory").classList.remove("hidden");
    document.getElementById("tabFriends").classList.remove("hidden");
    document.getElementById("tabDaily").classList.remove("hidden");

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
    document.getElementById("friendsTab").classList.add("hidden");
    document.getElementById("dailyTab").classList.add("hidden");

    document.getElementById("tabLogout").classList.add("hidden");
    document.getElementById("tabHistory").classList.add("hidden");
    document.getElementById("tabFriends").classList.add("hidden");
    document.getElementById("tabDaily").classList.add("hidden");
}

function showModeScreen() {
    stopTimer();

    document.getElementById("modeScreen").classList.remove("hidden");
    document.getElementById("gameScreen").classList.add("hidden");
    document.getElementById("endScreen").classList.add("hidden");

    showTab("play");
}

async function loadProfileHome() {
    if (!currentUser) return;

    const res = await fetch("/profile/" + encodeURIComponent(currentUser));
    const data = await res.json();

    const icon = document.getElementById("homeRankIcon");
    icon.className = "";
    
    if(data.rank_tier){
    icon.classList.add("rank-glow-" + data.rank_tier);
    }
    
    icon.src = data.rank_icon || "";
    icon.style.display = data.rank_icon ? "block" : "none";

    icon.classList.toggle("rank-glow", data.high_rank);

    document.getElementById("homeRankText").innerText = `${data.rank_name}`;
    document.getElementById("homeRRText").innerText = `${data.rr} / 100 RR`;
    document.getElementById("homeRRBar").style.width = `${data.rr}%`;
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
    combo = 0;
    maxCombo = 0;
    comboPoints = 0;
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
    document.getElementById("comboText").innerText = `Combo: ${combo} | Bonus: ${comboPoints}`;

    if (currentMode !== "timer") {
        document.getElementById("timerText").innerText = "Time: N/A";
    }
}

function loadImageToCanvas(agent) {
    if (flashTimeout) clearTimeout(flashTimeout);

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

        if (currentMode === "flash") {
            flashTimeout = setTimeout(() => {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.fillStyle = "#0c131b";
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.fillStyle = "#ff4655";
                ctx.textAlign = "center";
                ctx.font = "bold 30px Arial";
                ctx.fillText("IMAGE VANISHED", canvas.width / 2, canvas.height / 2);
            }, 950);
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
        combo++;
        maxCombo = Math.max(maxCombo, combo);

        let gained = 0;

        if (currentMode === "timer") {
            gained = Math.max(0, combo - 1);
            comboPoints += gained;
        }

        document.getElementById("message").innerText =
            `Correct. It was ${currentCorrect}${currentMode === "timer" ? ` | Combo x${combo} +${gained}` : ""}`;

        document.getElementById("message").style.color = "#50dc8c";
    } else {
        combo = 0;
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
    }, 850);
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
            seconds: seconds,
            combo_points: comboPoints,
            max_combo: maxCombo
        })
    });

    const data = await saveRes.json();

    document.getElementById("gameScreen").classList.add("hidden");
    document.getElementById("endScreen").classList.remove("hidden");

    document.getElementById("finalScore").innerText = `Score: ${score}/${totalRounds}`;
    document.getElementById("finalTime").innerText = seconds ? `Time: ${seconds}s` : "";
    document.getElementById("finalCombo").innerText = `Max combo: ${maxCombo} | Combo bonus: ${comboPoints}`;

    document.getElementById("rankText").innerText = data.rr_rank_name;
    document.getElementById("rrChangeText").innerText =
        `${data.rr_change >= 0 ? "+" : ""}${data.rr_change} RR`;

    document.getElementById("endRRText").innerText = `${data.rr} / 100 RR`;
    document.getElementById("endRRBar").style.width = `${data.rr}%`;

    const icon = document.getElementById("rankIcon");

    if (data.rank_icon) {
        icon.src = data.rank_icon;
        icon.style.display = "block";
        icon.classList.toggle("rank-glow", data.high_rank);
    } else {
        icon.style.display = "none";
    }

    let dailyText = "";
    if (data.daily && data.daily.newly_completed && data.daily.newly_completed.length > 0) {
        dailyText += "Daily completed: " + data.daily.newly_completed.map(x => x.text).join(", ");
    }
    if (data.daily && data.daily.badge_awarded) {
        dailyText += dailyText ? " | " : "";
        dailyText += "Feet Grinder badge earned.";
    }
    document.getElementById("dailyResult").innerText = dailyText;

    if (data.rank_up || data.rank_down) {
        showRankup(data.rank_up, data.rr_rank_name);
    }

    loadProfileHome();
}

function showRankup(isRankUp, rankName) {
    document.getElementById("rankupTitle").innerText = isRankUp ? "RANK UP" : "RANK DOWN";
    document.getElementById("rankupText").innerText = isRankUp
        ? `You promoted to ${rankName}.`
        : `You dropped to ${rankName}.`;
    document.getElementById("rankupOverlay").style.display = "flex";
}

function hideRankup() {
    document.getElementById("rankupOverlay").style.display = "none";
}

async function loadLeaderboard(mode) {
    const res = await fetch("/leaderboard/" + mode);
    const data = await res.json();


    const rows = document.getElementById("leaderboardRows");
    rows.innerHTML = "";

    if (data.entries.length === 0) {
        rows.innerHTML = "<p>No scores yet. Be the first leaderboard gremlin.</p>";
        return;
    }

    data.entries.forEach((entry, index) => {
        const timeText = entry.seconds === null || entry.seconds === undefined ? "N/A" : entry.seconds + "s";
        const rrText = entry.rr !== undefined ? `${entry.rr}/100` : "N/A";
        
        const row = document.createElement("div");
        row.className = "leader-row";

        row.innerHTML = `
<div>${index + 1}</div>
<div>${entry.username}</div>
<div>${entry.score}/${totalRounds}</div>
<div>${timeText}</div>
<div>${rrText}</div>
<div>
    <img class="rank-icon-small rank-glow-${entry.rr_rank || entry.rank_tier}" src="/rank-icon/${entry.rr_rank || entry.rank_tier}" onerror="this.style.display='none'">
    ${entry.rr_rank_name || entry.rank_name || "Unranked Sock Civilian"}
</div>
`;

        rows.appendChild(row);
    });
}

function startChatPolling() {
    if (chatInterval) clearInterval(chatInterval);
    lastMessageCount = -1;
    loadMessages();
    chatInterval = setInterval(loadMessages, 1000);
}

async function loadMessages() {
    if (!currentUser || !currentChatFriend) return;

    const box = document.getElementById("chatBox");
    const status = document.getElementById("chatStatus");

    if (!box) return;

    try {
        const res = await fetch(`/messages/${encodeURIComponent(currentUser)}/${encodeURIComponent(currentChatFriend)}`);
        const data = await res.json();
        const messages = data.messages || [];

        if (messages.length === lastMessageCount) return;
        lastMessageCount = messages.length;

        box.innerHTML = "";

        if (messages.length === 0) {
            box.innerHTML = "<p class='small'>No messages yet. Start by typing a racial slur.</p>";
        }

        messages.forEach(msg => {
            const div = document.createElement("div");
            const mine = msg.from.toLowerCase() === currentUser.toLowerCase();

            div.style.textAlign = mine ? "right" : "left";

            div.innerHTML = `
                <span style="background:${mine ? '#ff4655' : '#1f2a36'};padding:8px 11px;border-radius:8px;display:inline-block;margin:4px;max-width:80%;word-wrap:break-word;">
                    ${escapeHTML(msg.message)}
                </span>
                <div class="small" style="opacity:0.55;">${mine ? 'You' : msg.from}</div>
            `;

            box.appendChild(div);
        });

        box.scrollTop = box.scrollHeight;
        if (status) status.innerText = `Chatting with ${currentChatFriend}`;
    } catch (err) {
        if (status) status.innerText = "Could not load chat.";
        console.error(err);
    }
}

function escapeHTML(text) {
    return String(text)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

async function sendMessage() {
    const input = document.getElementById("chatInput");
    const text = input.value.trim();
    const status = document.getElementById("chatStatus");

    if (!currentChatFriend) {
        status.innerText = "Click View on an accepted friend first.";
        return;
    }

    if (!text) {
        status.innerText = "Type a message first.";
        return;
    }

    const res = await fetch("/send-message", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            from: currentUser,
            to: currentChatFriend,
            message: text
        })
    });

    const data = await res.json();

    if (!data.success) {
        status.innerText = data.error || "Message failed to send.";
        return;
    }

    input.value = "";
    status.innerText = "Sent.";
    lastMessageCount = -1;
    loadMessages();
}

async function loadMatchHistory(mode) {
    if (!currentUser) return;

    const res = await fetch("/match-history/" + encodeURIComponent(currentUser) + "/" + mode);
    const data = await res.json();

    document.getElementById("profileUsername").innerText = currentUser;

    const profileIcon = document.getElementById("profileRankIcon");
    profileIcon.style.display = data.profile.rank_icon ? "block" : "none";
    profileIcon.src = data.profile.rank_icon || "";
    profileIcon.className = "history-rank-icon";
    profileIcon.classList.add("rank-glow-" + (data.profile.rank || data.profile.rank_tier));

    document.getElementById("profileRankText").innerText = `${data.profile.rank_name}`;
    document.getElementById("profileRRText").innerText = `${data.profile.rr} / 100 RR`;
    document.getElementById("profileRRBar").style.width = `${data.profile.rr}%`;

    const rows = document.getElementById("historyRows");
    rows.innerHTML = "";

    if (data.matches.length === 0) {
        rows.innerHTML = "<p>No matches yet. Go create some evidence.</p>";
        return;
    }

    data.matches.forEach((match, index) => {
        const timeText = match.seconds === null || match.seconds === undefined ? "N/A" : match.seconds + "s";
        const date = new Date(match.time).toLocaleString();
        const rrText = match.rr_change === undefined || match.rr_change === null
            ? "N/A"
            : `${match.rr_change >= 0 ? "+" : ""}${match.rr_change}`;

        const row = document.createElement("div");

        let gameClass = "mid-game";
        if (match.score >= 5) gameClass = "good-game";
        if (match.score <= 3) gameClass = "bad-game";

        row.className = `history-card ${gameClass}`;

        row.innerHTML = `
            <div>${index + 1}</div>
            <div>${match.mode.toUpperCase()}</div>
            <div>${match.score}/${totalRounds}</div>
            <div>${timeText}</div>
            <div>${rrText}</div>
            <div>
                <img class="history-rank-icon rank-glow-${match.rr_rank || match.rank_tier}" src="/rank-icon/${match.rr_rank || match.rank_tier}" onerror="this.style.display='none'">
                ${match.rr_rank_name || match.rank_name}
            </div>
            <div>${date}</div>
        `;

        rows.appendChild(row);
    });
}

async function loadDailies() {
    if (!currentUser) return;

    const res = await fetch("/dailies/" + encodeURIComponent(currentUser));
    const data = await res.json();

    const rows = document.getElementById("dailyRows");
    rows.innerHTML = "";

    data.challenges.forEach(challenge => {
        const div = document.createElement("div");
        div.className = "daily-card";
        if (challenge.completed) div.classList.add("completed");

        div.innerHTML = `
            <strong>${challenge.completed ? "DONE" : "TODO"}</strong>
            <p>${challenge.text}</p>
        `;

        rows.appendChild(div);
    });

    if (data.badges && data.badges.length > 0) {
        const badgeBox = document.createElement("div");
        badgeBox.className = "daily-card completed";
        badgeBox.innerHTML = `<strong>Badges</strong><p>${data.badges.join("<br>")}</p>`;
        rows.appendChild(badgeBox);
    }
}

async function addFriend() {
    const friend = document.getElementById("friendName").value.trim();

    if (!friend) {
        document.getElementById("friendMessage").innerText = "Type a username first.";
        return;
    }

    const res = await fetch("/add-friend", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({user: currentUser, friend})
    });

    const data = await res.json();

    document.getElementById("friendMessage").innerText = data.message || (data.success ? "Request sent." : "Could not send request.");
    document.getElementById("friendName").value = "";

    loadFriends();
}

async function acceptFriend(friend) {
    const res = await fetch("/accept-friend", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({user: currentUser, friend})
    });

    const data = await res.json();
    document.getElementById("friendMessage").innerText = data.message || "Friend request accepted.";
    loadFriends();
}

async function declineFriend(friend) {
    const res = await fetch("/decline-friend", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({user: currentUser, friend})
    });

    const data = await res.json();
    document.getElementById("friendMessage").innerText = data.message || "Friend request declined.";
    loadFriends();
}

async function removeFriend(friend) {
    await fetch("/remove-friend", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({user: currentUser, friend})
    });

    if (currentChatFriend && currentChatFriend.toLowerCase() === friend.toLowerCase()) {
        currentChatFriend = "";
        if (chatInterval) clearInterval(chatInterval);
        document.getElementById("friendProfile").classList.add("hidden");
    }

    loadFriends();
}

async function loadFriendRequests() {
    if (!currentUser) return;

    const res = await fetch("/friend-requests/" + encodeURIComponent(currentUser));
    const data = await res.json();

    const rows = document.getElementById("friendRequestRows");
    rows.innerHTML = "";

    const incoming = data.incoming || [];
    const outgoing = data.outgoing || [];

    if (incoming.length === 0 && outgoing.length === 0) {
        rows.innerHTML = "<p>No pending friend requests.</p>";
        return;
    }

    incoming.forEach(req => {
        const div = document.createElement("div");
        div.className = "friend-card";
        div.innerHTML = `
            <div>
                <strong>${req.username}</strong>
                <p class="small">Incoming request | ${req.rank_name} | ${req.rr}/100 RR</p>
            </div>
            <button onclick="acceptFriend('${req.username}')">Accept</button>
            <button onclick="declineFriend('${req.username}')">Decline</button>
        `;
        rows.appendChild(div);
    });

    outgoing.forEach(req => {
        const div = document.createElement("div");
        div.className = "friend-card";
        div.innerHTML = `
            <div>
                <strong>${req.username}</strong>
                <p class="small">Outgoing request | ${req.rank_name} | ${req.rr}/100 RR</p>
            </div>
            <span class="small">Pending</span>
            <button onclick="removeFriend('${req.username}')">Cancel</button>
        `;
        rows.appendChild(div);
    });
}

async function loadFriends() {
    if (!currentUser) return;

    await loadFriendRequests();

    const res = await fetch("/friends/" + encodeURIComponent(currentUser));
    const data = await res.json();

    const rows = document.getElementById("friendsRows");
    rows.innerHTML = "";

    if (!data.friends || data.friends.length === 0) {
        rows.innerHTML = "<p>No accepted friends yet. Send a request or accept one.</p>";
        return;
    }

    data.friends.forEach(friend => {
        const div = document.createElement("div");
        div.className = "friend-card";

        div.innerHTML = `
            <div>
                <strong>${friend.username}</strong>
                <p class="small">${friend.rank_name} | ${friend.rr}/100 RR</p>
            </div>
            <button onclick="viewFriend('${friend.username}')">View</button>
            <button onclick="removeFriend('${friend.username}')">Remove</button>
        `;

        rows.appendChild(div);
    });
}

async function viewFriend(username) {
    const res = await fetch("/public-profile/" + encodeURIComponent(username));
    const data = await res.json();
    currentChatFriend = username;
    lastMessageCount = -1;
    startChatPolling();
    const chatTitle = document.getElementById("chatTitle");
    const chatStatus = document.getElementById("chatStatus");
    if (chatTitle) chatTitle.innerText = `Chat with ${username}`;
    if (chatStatus) chatStatus.innerText = "Loading chat...";

    document.getElementById("friendProfile").classList.remove("hidden");
    document.getElementById("friendProfileName").innerText = data.username;

    const icon = document.getElementById("friendRankIcon");
    icon.src = data.profile.rank_icon || "";
    icon.style.display = data.profile.rank_icon ? "block" : "none";
    icon.classList.toggle("rank-glow", data.profile.high_rank);

    document.getElementById("friendRankText").innerText = data.profile.rank_name;
    document.getElementById("friendRRText").innerText = `${data.profile.rr} / 100 RR`;
    document.getElementById("friendRRBar").style.width = `${data.profile.rr}%`;

    document.getElementById("friendStats").innerHTML = `
        <div class="stat-box">Games: ${data.profile.games_played || 0}</div>
        <div class="stat-box">Wins: ${data.profile.wins || 0}</div>
        <div class="stat-box">Losses: ${data.profile.losses || 0}</div>
        <div class="stat-box">Peak: ${data.profile.peak_rank || "iron"}</div>
        <div class="stat-box">Badges:<br>${(data.profile.badges || []).join("<br>") || "None"}</div>
    `;

    const rows = document.getElementById("friendHistoryRows");
    rows.innerHTML = "";

    if (!data.matches || data.matches.length === 0) {
        rows.innerHTML = "<p>No matches yet.</p>";
        return;
    }

    data.matches.forEach((match, index) => {
        const row = document.createElement("div");

        let gameClass = "mid-game";
        if (match.score >= 5) gameClass = "good-game";
        if (match.score <= 3) gameClass = "bad-game";

        row.className = `history-card ${gameClass}`;
        row.style.gridTemplateColumns = "55px 90px 90px 1fr";

        const timeText = match.seconds === null || match.seconds === undefined ? "N/A" : match.seconds + "s";

        row.innerHTML = `
            <div>${index + 1}</div>
            <div>${match.mode.toUpperCase()}</div>
            <div>${match.score}/${totalRounds}</div>
            <div>${timeText}</div>
        `;

        rows.appendChild(row);
    });
}
</script>
</body>
</html>
    """, agents=AGENTS, total_rounds=TOTAL_ROUNDS)


# =========================
# AUTH ROUTES
# =========================

@app.route("/register", methods=["POST"])
def register():
    data = request.json or {}

    username = clean_username(data.get("username", ""))
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

    # Create RR profile immediately
    rr_data = load_json(RR_FILE, {})
    rr_data.setdefault(key, {
        "username": username,
        "rank": "iron",
        "rr": 50,
        "peak_rank": "iron",
        "games_played": 0,
        "wins": 0,
        "losses": 0,
        "badges": []
    })
    save_json(RR_FILE, rr_data)

    return jsonify({"success": True, "username": username})


@app.route("/login", methods=["POST"])
def login():
    data = request.json or {}

    username = data.get("username", "").strip()
    password = data.get("password", "")

    users = load_json(USERS_FILE, {})
    key = username.lower()

    if key not in users:
        return jsonify({"success": False, "error": "Account not found."})

    if not check_password_hash(users[key]["password_hash"], password):
        return jsonify({"success": False, "error": "Wrong password."})

    return jsonify({"success": True, "username": users[key]["username"]})


# =========================
# GAME ROUTES
# =========================

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


@app.route("/rank-icon/<tier>")
def rank_icon(tier):
    tier = str(tier or "").lower()

    if tier not in RANK_ORDER:
        tier = "iron"

    path = find_rank_icon(tier)

    if path:
        return send_file(os.path.join(app.static_folder, path.replace("/static/", "")))

    return "", 404


@app.route("/save-score", methods=["POST"])
def save_score():
    data = request.json or {}

    username = clean_username(data.get("username", "Anonymous"))
    mode = data.get("mode", "normal")
    score = int(data.get("score", 0))
    seconds = data.get("seconds", None)
    combo_points = int(data.get("combo_points", 0))
    max_combo = int(data.get("max_combo", 0))

    if seconds is not None:
        seconds = float(seconds)

    if mode not in VALID_MODES:
        mode = "normal"

    old_rank_tier, old_rank_name = get_rank(score, mode, seconds)

    rr_info = update_rr(username, score, mode, seconds, combo_points)

    season = current_season()
    now = datetime.now().isoformat()

    new_entry = {
        "username": username,
        "mode": mode,
        "score": score,
        "seconds": seconds,
        "rank_tier": old_rank_tier,
        "rank_name": old_rank_name,
        "rr_rank": rr_info["rank"],
        "rr_rank_name": rr_info["rank_name"],
        "rr": rr_info["rr"],
        "rr_change": rr_info["rr_change"],
        "combo_points": combo_points,
        "max_combo": max_combo,
        "season": season,
        "time": now
    }

    match_history = load_json(MATCH_HISTORY_FILE, [])
    if not isinstance(match_history, list):
        match_history = []
    match_history.append(new_entry)
    save_json(MATCH_HISTORY_FILE, match_history)

    leaderboard = load_json(LEADERBOARD_FILE, [])
    if not isinstance(leaderboard, list):
        leaderboard = []

    normalized = []
    for raw in leaderboard:
        fixed = normalize_entry(raw)
        if fixed:
            normalized.append(fixed)

    updated = False

    for i, entry in enumerate(normalized):
        same_player = entry.get("username", "").lower() == username.lower()
        same_mode = entry.get("mode") == mode
        same_season = entry.get("season") == season

        if same_player and same_mode and same_season:
            if is_better_score(new_entry, entry):
                normalized[i] = new_entry
            updated = True
            break

    if not updated:
        normalized.append(new_entry)

    save_json(LEADERBOARD_FILE, normalized)

    daily_info = update_daily_progress(username, mode, score)

    return jsonify({
        "success": True,
        "old_score_rank_tier": old_rank_tier,
        "old_score_rank_name": old_rank_name,
        "rr_rank": rr_info["rank"],
        "rr_rank_name": rr_info["rank_name"],
        "rank_icon": find_rank_icon(rr_info["rank"]),
        "rr": rr_info["rr"],
        "rr_change": rr_info["rr_change"],
        "rank_up": rr_info["rank_up"],
        "rank_down": rr_info["rank_down"],
        "high_rank": rr_info["rank"] in HIGH_RANKS,
        "daily": daily_info
    })


# =========================
# DATA ROUTES
# =========================

@app.route("/leaderboard/<mode>")
def leaderboard(mode):
    if mode not in ["normal", "pixel", "timer", "flash"]:
        mode = "normal"

    raw_entries = load_json(LEADERBOARD_FILE, [])

    entries = []

    for entry in raw_entries:
        if entry.get("mode", "normal") != mode:
            continue

        if "rank_name" not in entry or "rank_tier" not in entry:
            score = int(entry.get("score", 0))
            seconds = entry.get("seconds", None)
            rank_tier, rank_name = get_rank(score, mode, seconds)
            entry["rank_tier"] = rank_tier
            entry["rank_name"] = rank_name

        if "seconds" not in entry:
            entry["seconds"] = None
            
        profile = get_player_rr(entry.get("username", "Anonymous"))
            
        entry["rr"] = profile.get("rr", 50)
        entry["rr_rank"] = profile.get("rank", "iron")
        entry["rank_name"] = RANK_NAMES.get(entry["rr_rank"], "Iron Sock Inspector")
        entry["high_rank"] = entry["rr_rank"] in HIGH_RANKS    

        entries.append(entry)

    best_by_user = {}

    for entry in entries:
        username_key = entry.get("username", "").strip().lower()

        if username_key == "":
            continue

        old = best_by_user.get(username_key)

        if old is None:
            best_by_user[username_key] = entry
            continue

        if mode == "timer":
            entry_score = entry.get("score", 0)
            old_score = old.get("score", 0)
            entry_seconds = entry.get("seconds") or 999999
            old_seconds = old.get("seconds") or 999999

            if entry_score > old_score or (
                entry_score == old_score and entry_seconds < old_seconds
            ):
                best_by_user[username_key] = entry
        else:
            if entry.get("score", 0) > old.get("score", 0):
                best_by_user[username_key] = entry

    entries = list(best_by_user.values())

    if mode == "timer":
        entries = sorted(
            entries,
            key=lambda x: (
                -(x.get("score", 0)),
                x.get("seconds") or 999999
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
        "entries": entries[:20]
    })


@app.route("/match-history/<username>/<mode>")
def match_history(username, mode):
    username = clean_username(username)
    username_key = username.lower()

    all_raw = load_json(MATCH_HISTORY_FILE, [])
    if not isinstance(all_raw, list):
        all_raw = []

    all_entries = []

    for raw in all_raw:
        entry = normalize_entry(raw)
        if not entry:
            continue

        # Preserve extra history fields from newer entries
        for extra in ["rr_rank", "rr_rank_name", "rr", "rr_change", "combo_points", "max_combo"]:
            if isinstance(raw, dict) and extra in raw:
                entry[extra] = raw[extra]

        if entry.get("username", "").lower() == username_key:
            all_entries.append(entry)

    if mode == "all":
        entries = all_entries
    elif mode in VALID_MODES:
        entries = [e for e in all_entries if e.get("mode") == mode]
    else:
        entries = all_entries

    entries = sorted(entries, key=lambda x: x.get("time", ""), reverse=True)

    profile = get_player_rr(username)
    rank = profile.get("rank", "iron")

    profile_payload = {
        "username": username,
        "rank": rank,
        "rank_name": RANK_NAMES.get(rank, "Iron Sock Inspector"),
        "rank_icon": find_rank_icon(rank),
        "rr": profile.get("rr", 50),
        "peak_rank": profile.get("peak_rank", "iron"),
        "games_played": profile.get("games_played", 0),
        "wins": profile.get("wins", 0),
        "losses": profile.get("losses", 0),
        "badges": profile.get("badges", []),
        "high_rank": rank in HIGH_RANKS
    }

    for entry in entries:
        rr_rank = entry.get("rr_rank") or profile_payload["rank"]
        entry["rr_rank"] = rr_rank
        entry["rr_rank_name"] = entry.get("rr_rank_name") or RANK_NAMES.get(rr_rank, "Iron Sock Inspector")
        entry["high_rank"] = rr_rank in HIGH_RANKS

    return jsonify({
        "matches": entries[:50],
        "profile": profile_payload,
        "selected_mode": mode
    })


@app.route("/profile/<username>")
def profile(username):
    username = clean_username(username)
    profile = get_player_rr(username)

    rank = profile.get("rank", "iron")

    return jsonify({
        "username": username,
        "rank": rank,
        "rank_name": RANK_NAMES.get(rank, "Iron Sock Inspector"),
        "rank_icon": find_rank_icon(rank),
        "rr": profile.get("rr", 50),
        "peak_rank": profile.get("peak_rank", "iron"),
        "games_played": profile.get("games_played", 0),
        "wins": profile.get("wins", 0),
        "losses": profile.get("losses", 0),
        "badges": profile.get("badges", []),
        "high_rank": rank in HIGH_RANKS
    })


@app.route("/public-profile/<username>")
def public_profile(username):
    username = clean_username(username)

    profile_res = profile(username)
    profile_data = profile_res.get_json()

    all_raw = load_json(MATCH_HISTORY_FILE, [])
    matches = []

    for raw in all_raw:
        entry = normalize_entry(raw)
        if not entry:
            continue

        if entry.get("username", "").lower() == username.lower():
            matches.append(entry)

    matches = sorted(matches, key=lambda x: x.get("time", ""), reverse=True)[:10]

    return jsonify({
        "username": username,
        "profile": profile_data,
        "matches": matches
    })



# =========================
# FRIEND REQUEST HELPERS
# =========================

def user_exists(username):
    username = clean_username(username)
    key = username.lower()

    users = load_json(USERS_FILE, {})
    if key in users:
        return True

    rr_data = load_json(RR_FILE, {})
    if key in rr_data:
        return True

    history = load_json(MATCH_HISTORY_FILE, [])
    return any(
        isinstance(e, dict) and str(e.get("username", "")).lower() == key
        for e in history
    )


def display_username(username):
    username = clean_username(username)
    key = username.lower()
    users = load_json(USERS_FILE, {})
    return users.get(key, {}).get("username", username)


def load_friend_map():
    friends = load_json(FRIENDS_FILE, {})
    if not isinstance(friends, dict):
        friends = {}

    fixed = {}
    for user_key, friend_list in friends.items():
        user_key = str(user_key).lower()
        if isinstance(friend_list, list):
            fixed[user_key] = sorted(set(str(f).lower() for f in friend_list if str(f).strip()))
        else:
            fixed[user_key] = []

    return fixed


def save_friend_map(friends):
    fixed = {}
    for user_key, friend_list in friends.items():
        fixed[str(user_key).lower()] = sorted(set(str(f).lower() for f in friend_list if str(f).strip()))
    save_json(FRIENDS_FILE, fixed)


def are_friends(user, friend):
    user_key = clean_username(user).lower()
    friend_key = clean_username(friend).lower()
    friends = load_friend_map()
    return friend_key in friends.get(user_key, []) and user_key in friends.get(friend_key, [])


def make_mutual_friends(user, friend):
    user_key = clean_username(user).lower()
    friend_key = clean_username(friend).lower()
    friends = load_friend_map()
    friends.setdefault(user_key, [])
    friends.setdefault(friend_key, [])

    if friend_key not in friends[user_key]:
        friends[user_key].append(friend_key)
    if user_key not in friends[friend_key]:
        friends[friend_key].append(user_key)

    save_friend_map(friends)


def remove_mutual_friends(user, friend):
    user_key = clean_username(user).lower()
    friend_key = clean_username(friend).lower()
    friends = load_friend_map()

    if user_key in friends:
        friends[user_key] = [f for f in friends[user_key] if f.lower() != friend_key]
    if friend_key in friends:
        friends[friend_key] = [f for f in friends[friend_key] if f.lower() != user_key]

    save_friend_map(friends)


def load_friend_requests():
    requests_data = load_json(FRIEND_REQUESTS_FILE, {})
    if not isinstance(requests_data, dict):
        requests_data = {}

    fixed = {}
    for receiver_key, sender_list in requests_data.items():
        receiver_key = str(receiver_key).lower()
        if isinstance(sender_list, list):
            fixed[receiver_key] = sorted(set(str(s).lower() for s in sender_list if str(s).strip()))
        else:
            fixed[receiver_key] = []

    return fixed


def save_friend_requests(requests_data):
    fixed = {}
    for receiver_key, sender_list in requests_data.items():
        clean_list = sorted(set(str(s).lower() for s in sender_list if str(s).strip()))
        if clean_list:
            fixed[str(receiver_key).lower()] = clean_list
    save_json(FRIEND_REQUESTS_FILE, fixed)


def has_pending_request(sender, receiver):
    sender_key = clean_username(sender).lower()
    receiver_key = clean_username(receiver).lower()
    requests_data = load_friend_requests()
    return sender_key in requests_data.get(receiver_key, [])


def add_pending_request(sender, receiver):
    sender_key = clean_username(sender).lower()
    receiver_key = clean_username(receiver).lower()
    requests_data = load_friend_requests()
    requests_data.setdefault(receiver_key, [])
    if sender_key not in requests_data[receiver_key]:
        requests_data[receiver_key].append(sender_key)
    save_friend_requests(requests_data)


def remove_pending_request(sender, receiver):
    sender_key = clean_username(sender).lower()
    receiver_key = clean_username(receiver).lower()
    requests_data = load_friend_requests()
    if receiver_key in requests_data:
        requests_data[receiver_key] = [s for s in requests_data[receiver_key] if s.lower() != sender_key]
    save_friend_requests(requests_data)


def migrate_old_friends_to_request_system():
    """
    Old system allowed one-sided friend adds.
    New system requires mutual acceptance.
    - If both users had added each other already, keep them as accepted mutual friends.
    - If only one side added the other, convert that into a pending request.
    """
    friends = load_friend_map()
    requests_data = load_friend_requests()
    accepted = {}

    for user_key, friend_list in friends.items():
        for friend_key in friend_list:
            accepted.setdefault(user_key, [])
            accepted.setdefault(friend_key, [])

            if user_key in friends.get(friend_key, []):
                if friend_key not in accepted[user_key]:
                    accepted[user_key].append(friend_key)
                if user_key not in accepted[friend_key]:
                    accepted[friend_key].append(user_key)
            else:
                requests_data.setdefault(friend_key, [])
                if user_key not in requests_data[friend_key]:
                    requests_data[friend_key].append(user_key)

    save_friend_map(accepted)
    save_friend_requests(requests_data)
    print("Friends migrated to request-based system.")

# =========================
# FRIENDS ROUTES
# =========================

@app.route("/add-friend", methods=["POST"])
def add_friend():
    data = request.json or {}

    user = clean_username(data.get("user", ""))
    friend = clean_username(data.get("friend", ""))

    if user.lower() == "anonymous":
        return jsonify({"success": False, "message": "Log in first."})

    if friend.lower() == "anonymous":
        return jsonify({"success": False, "message": "Invalid friend username."})

    if user.lower() == friend.lower():
        return jsonify({"success": False, "message": "You cannot add yourself, bestie."})

    if not user_exists(friend):
        return jsonify({"success": False, "message": "Could not find that player."})

    if are_friends(user, friend):
        return jsonify({"success": True, "message": f"You and {display_username(friend)} are already friends."})

    # If they already requested you, your add accepts it instantly.
    if has_pending_request(friend, user):
        remove_pending_request(friend, user)
        make_mutual_friends(user, friend)
        return jsonify({"success": True, "message": f"Accepted {display_username(friend)}'s friend request."})

    if has_pending_request(user, friend):
        return jsonify({"success": True, "message": f"Request already sent to {display_username(friend)}."})

    add_pending_request(user, friend)
    return jsonify({"success": True, "message": f"Friend request sent to {display_username(friend)}."})


@app.route("/accept-friend", methods=["POST"])
def accept_friend():
    data = request.json or {}

    user = clean_username(data.get("user", ""))
    friend = clean_username(data.get("friend", ""))

    if user.lower() == "anonymous" or friend.lower() == "anonymous":
        return jsonify({"success": False, "message": "Invalid request."})

    if not has_pending_request(friend, user):
        return jsonify({"success": False, "message": "No request from that player."})

    remove_pending_request(friend, user)
    make_mutual_friends(user, friend)

    return jsonify({"success": True, "message": f"You are now friends with {display_username(friend)}."})


@app.route("/decline-friend", methods=["POST"])
def decline_friend():
    data = request.json or {}

    user = clean_username(data.get("user", ""))
    friend = clean_username(data.get("friend", ""))

    remove_pending_request(friend, user)

    return jsonify({"success": True, "message": f"Declined {display_username(friend)}'s request."})


@app.route("/remove-friend", methods=["POST"])
def remove_friend():
    data = request.json or {}

    user = clean_username(data.get("user", ""))
    friend = clean_username(data.get("friend", ""))

    remove_mutual_friends(user, friend)
    remove_pending_request(user, friend)
    remove_pending_request(friend, user)

    return jsonify({"success": True})


@app.route("/friends/<username>")
def friends(username):
    username = clean_username(username)
    friends_data = load_friend_map()
    friend_keys = friends_data.get(username.lower(), [])

    result = []

    for friend_key in friend_keys:
        if not are_friends(username, friend_key):
            continue

        display_name = display_username(friend_key)
        p = get_player_rr(display_name)
        rank = p.get("rank", "iron")

        result.append({
            "username": p.get("username", display_name),
            "rank": rank,
            "rank_name": RANK_NAMES.get(rank, "Iron Sock Inspector"),
            "rank_icon": find_rank_icon(rank),
            "rr": p.get("rr", 50),
            "high_rank": rank in HIGH_RANKS
        })

    return jsonify({"friends": result})


@app.route("/friend-requests/<username>")
def friend_requests(username):
    username = clean_username(username)
    user_key = username.lower()
    requests_data = load_friend_requests()

    incoming_keys = requests_data.get(user_key, [])
    outgoing_keys = []

    for receiver_key, senders in requests_data.items():
        if user_key in [s.lower() for s in senders]:
            outgoing_keys.append(receiver_key)

    incoming = []
    for sender_key in incoming_keys:
        p = get_player_rr(display_username(sender_key))
        rank = p.get("rank", "iron")
        incoming.append({
            "username": p.get("username", display_username(sender_key)),
            "rank_name": RANK_NAMES.get(rank, "Iron Sock Inspector"),
            "rr": p.get("rr", 50)
        })

    outgoing = []
    for receiver_key in outgoing_keys:
        p = get_player_rr(display_username(receiver_key))
        rank = p.get("rank", "iron")
        outgoing.append({
            "username": p.get("username", display_username(receiver_key)),
            "rank_name": RANK_NAMES.get(rank, "Iron Sock Inspector"),
            "rr": p.get("rr", 50)
        })

    return jsonify({"incoming": incoming, "outgoing": outgoing})


# =========================
# DAILY ROUTES
# =========================

@app.route("/dailies/<username>")
def dailies(username):
    username = clean_username(username)
    key = username.lower()

    d = get_daily_challenges()
    completed = d.get("completed", {}).get(key, [])

    challenges = []

    for challenge in d.get("challenges", []):
        item = dict(challenge)
        item["completed"] = item["id"] in completed
        challenges.append(item)

    p = get_player_rr(username)

    return jsonify({
        "date": d.get("date"),
        "challenges": challenges,
        "badges": p.get("badges", [])
    })


# =========================
# DEBUG / REPAIR ROUTES
# =========================

@app.route("/repair-data")
def repair_data():
    migrate_old_leaderboard_to_match_history()
    migrate_old_match_history_format()
    migrate_old_leaderboard_format()
    rebuild_rr_from_history_if_missing()

    return jsonify({
        "success": True,
        "message": "Data repaired."
    })


# =========================
# START
# =========================

@app.route("/send-message", methods=["POST"])
def send_message():
    data = request.json or {}

    sender = clean_username(data.get("from", ""))
    receiver = clean_username(data.get("to", ""))
    message = str(data.get("message", "")).strip()

    if sender.lower() == "anonymous" or receiver.lower() == "anonymous" or message == "":
        return jsonify({
            "success": False,
            "error": "Missing sender, receiver, or message."
        })

    if not user_exists(receiver):
        return jsonify({
            "success": False,
            "error": "That user does not exist."
        })

    if not are_friends(sender, receiver):
        return jsonify({
            "success": False,
            "error": "You can only message accepted friends."
        })

    messages = load_json(MESSAGES_FILE, [])
    if not isinstance(messages, list):
        messages = []

    messages.append({
        "from": sender,
        "to": receiver,
        "message": message,
        "time": datetime.now().isoformat()
    })

    save_json(MESSAGES_FILE, messages)

    return jsonify({"success": True})


@app.route("/messages/<user>/<friend>")
def get_messages(user, friend):
    user = clean_username(user)
    friend = clean_username(friend)

    if not are_friends(user, friend):
        return jsonify({"messages": []})

    messages = load_json(MESSAGES_FILE, [])
    if not isinstance(messages, list):
        messages = []

    convo = []

    for m in messages:
        sender = str(m.get("from", ""))
        receiver = str(m.get("to", ""))

        if (
            (sender.lower() == user.lower() and receiver.lower() == friend.lower())
            or
            (sender.lower() == friend.lower() and receiver.lower() == user.lower())
        ):
            convo.append(m)

    convo.sort(key=lambda x: x.get("time", ""))

    return jsonify({"messages": convo})

if __name__ == "__main__":
    migrate_old_leaderboard_to_match_history()
    migrate_old_match_history_format()
    migrate_old_leaderboard_format()
    rebuild_rr_from_history_if_missing()
    migrate_old_friends_to_request_system()

    app.run(host="0.0.0.0", port=5000, debug=False)

