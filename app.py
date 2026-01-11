import streamlit as st
import json
import os
import time
import qrcode
import pandas as pd
from io import BytesIO

st.write("DEBUG FILES:", os.listdir("."))

# ----------------------------------
# CONFIG
# ----------------------------------
STATE_FILE = "state.json"
VOTES_FILE = "votes.json"
COMMENTS_FILE = "comments.json"
COCKTAILS_FILE = "cocktails.json"

PUBLIC_URL = "https://gin-voting-app-aiwp54kyxjdaxba3aaqqth.streamlit.app/"

DEFAULT_STATE = {
    "phase": "holding",   # holding | open | closed | presentation
    "num_gins": 10
}

# ----------------------------------
# SAFE STATE HANDLING
# ----------------------------------
def load_state():
    if not os.path.exists(STATE_FILE):
        return DEFAULT_STATE.copy()
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return DEFAULT_STATE.copy()

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

state = load_state()
phase = state["phase"]
num_gins = state["num_gins"]

# ----------------------------------
# SAFE DATA LOADERS
# ----------------------------------
def load_json(file, default):
    if not os.path.exists(file):
        return default
    try:
        with open(file, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default

votes = load_json(VOTES_FILE, {})
comments = load_json(COMMENTS_FILE, {})
cocktails = load_json(COCKTAILS_FILE, {})

gins = [f"Gin {i+1}" for i in range(num_gins)]
for g in gins:
    votes.setdefault(g, [])
    comments.setdefault(g, [])

# ----------------------------------
# 🔐 ADMIN SIDEBAR
# ----------------------------------
st.sidebar.title("🔐 Admin Panel")
admin_pw = st.secrets.get("ADMIN_PASSWORD", "admin123")
entered_pw = st.sidebar.text_input("Admin Password", type="password")

if entered_pw == admin_pw:
    st.sidebar.success("Admin authenticated")

    st.sidebar.subheader("Competition Setup")
    new_num = st.sidebar.number_input(
        "Number of gins",
        min_value=1,
        max_value=50,
        value=num_gins
    )
    if st.sidebar.button("Save Gin Count"):
        save_state({"phase": phase, "num_gins": new_num})
        st.rerun()

    st.sidebar.subheader("Competition Control")
    if st.sidebar.button("Open Competition"):
        save_state({"phase": "open", "num_gins": num_gins})
        st.rerun()
    if st.sidebar.button("Close Competition"):
        save_state({"phase": "closed", "num_gins": num_gins})
        st.rerun()
    if st.sidebar.button("Reveal Winner"):
        save_state({"phase": "presentation", "num_gins": num_gins})
        st.rerun()
    if st.sidebar.button("Reset Everything"):
        save_state(DEFAULT_STATE)
        json.dump({}, open(VOTES_FILE, "w"))
        json.dump({}, open(COMMENTS_FILE, "w"))
        json.dump({}, open(COCKTAILS_FILE, "w"))
        st.rerun()

    # Cocktail CSV button now available in CLOSED or PRESENTATION phases
    if phase in ["closed", "presentation"] and cocktails:
        st.sidebar.subheader("Cocktail Recipes")
        df_cocktails = pd.DataFrame([
            {
                "Participant": p,
                "Did you add ice?": data.get("ice", ""),
                "How much Gin?": data.get("gin_amount", ""),
                "Mixer?": data.get("mixer", ""),
                "Garnish?": data.get("garnish", ""),
                "Other notes": data.get("notes", ""),
                "Gin Cocktail Name": data.get("name", "")
            }
            for p, data in cocktails.items()
        ])
        st.sidebar.download_button("Download Cocktail Recipes CSV",
                                   df_cocktails.to_csv(index=False),
                                   "cocktails.csv",
                                   "text/csv")
else:
    st.sidebar.info("Enter admin password to control the competition")

st.markdown("## 🔐 Emergency Data Recovery")

if st.button("Download RAW Votes + Comments"):
    try:
        with open(VOTES_FILE, "r") as f:
            votes_data = f.read()
        with open(COMMENTS_FILE, "r") as f:
            comments_data = f.read()

        st.download_button(
            "Download votes.json",
            votes_data,
            file_name="votes.json",
            mime="application/json"
        )

        st.download_button(
            "Download comments.json",
            comments_data,
            file_name="comments.json",
            mime="application/json"
        )

    except Exception as e:
        st.error(f"Could not read data files: {e}")

# ----------------------------------
# AUTO REFRESH
# ----------------------------------
if phase in ["holding", "closed"]:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=5000, key="refresh")

# ----------------------------------
# QR CODE
# ----------------------------------
def show_qr():
    qr = qrcode.make(PUBLIC_URL)
    buf = BytesIO()
    qr.save(buf)
    st.image(buf.getvalue(), caption="Scan to join")

# ----------------------------------
# HOLDING PAGE
# ----------------------------------
if phase == "holding":
    st.title("🍸 Gin Judging Competition")
    st.subheader("Please stand by…")
    st.write("Voting will open shortly. Scan the QR code to be ready.")
    show_qr()

# ----------------------------------
# VOTING PAGE
# ----------------------------------
elif phase == "open":
    st.title("🍸 Cast Your Votes")
    voter = st.text_input("Your name or email")

    if voter:
        scores = {}
        top_gin = None
        top_score = -1

        for idx, gin in enumerate(gins):
            score = st.slider(gin, 1, 10, 5, key=f"{voter}_{gin}")
            scores[gin] = score
            if score > top_score:
                top_score = score
                top_gin = gin

        comment = st.text_area(
            f"Why did you like {top_gin}?",
            placeholder="Optional comment"
        )

        # After last gin, show cocktail recipe form
        if len(gins) > 0:
            with st.expander("🍹 Gin Cocktail Recipe (optional)"):
                with st.form(f"cocktail_form_{voter}"):
                    ice = st.radio("Did you add ice?", ["Yes", "No"])
                    gin_amount = st.text_input("How much Gin?")
                    mixer = st.text_input("Mixer?")
                    garnish = st.text_input("Garnish?")
                    notes = st.text_input("Any other notes - e.g., Add 3 splashes of Angostura, or muddle some mint in there!")
                    cocktail_name = st.text_input("Gin Cocktail Name")
                    submit_cocktail = st.form_submit_button("Submit Cocktail")
                    if submit_cocktail:
                        cocktails[voter] = {
                            "ice": ice,
                            "gin_amount": gin_amount,
                            "mixer": mixer,
                            "garnish": garnish,
                            "notes": notes,
                            "name": cocktail_name
                        }
                        json.dump(cocktails, open(COCKTAILS_FILE, "w"))
                        st.success("Your cocktail has been saved!")

        # Submit votes + comment
        if st.button("Submit Vote"):
            for gin, s in scores.items():
                votes.setdefault(gin, []).append(s)
            if comment:
                comments.setdefault(top_gin, []).append({"name": voter, "comment": comment})

            json.dump(votes, open(VOTES_FILE, "w"))
            json.dump(comments, open(COMMENTS_FILE, "w"))

            st.success("Thank you for voting!")

# ----------------------------------
# CLOSED PAGE
# ----------------------------------
elif phase == "closed":
    st.title("⏳ Voting Closed")
    st.write("Results are being prepared…")
    show_qr()

# ----------------------------------
# PRESENTATION PAGE
# ----------------------------------
elif phase == "presentation":
    st.title("🏆 Final Standings 🎉")

    averages = {gin: sum(v)/len(v) if v else 0 for gin, v in votes.items()}
    ranked = sorted(averages.items(), key=lambda x: x[1], reverse=True)

    podium = [
        ("🥉 BRONZE", ranked[2] if len(ranked) > 2 else None),
        ("🥈 SILVER", ranked[1] if len(ranked) > 1 else None),
        ("🥇 GOLD", ranked[0] if len(ranked) > 0 else None),
    ]

    containers = [st.container() for _ in podium]

    for i, (medal, data) in enumerate(podium):
        if data is None:
            continue
        gin, avg = data
        container = containers[i]

        medal_slot = container.empty()
        shifts = list(range(0, 21, 3)) + list(range(20, -1, -3))
        for _ in range(2):
            for shift in shifts:
                medal_slot.markdown(
                    f"<h1 style='text-align:center; font-size:{45 + i*15}px; margin-left:{shift}px'>{medal} — {gin}</h1>",
                    unsafe_allow_html=True
                )
                time.sleep(0.1)

        container.write(f"{medal} — Average score: **{avg:.2f}**")
        if comments.get(gin):
            for c in comments[gin][:5]:
                name = c.get("name", "Someone")
                text = c.get("comment", "")
                container.write(f"💬 {name} said: \"{text}\"")

        if medal == "🥇 GOLD":
            st.balloons()
            time.sleep(1)

# ----------------------------------
# UI CLEANUP
# ----------------------------------
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)
