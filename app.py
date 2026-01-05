import streamlit as st
import qrcode
import json
import pandas as pd
import time
from io import BytesIO
from pathlib import Path
from collections import Counter
from PIL import Image
import matplotlib.pyplot as plt
from streamlit_autorefresh import st_autorefresh

# -------------------------------
# PAGE CONFIG
# -------------------------------
st.set_page_config(layout="wide")

# -------------------------------
# FILES
# -------------------------------
VOTES_FILE = Path("gin_votes.json")
STATE_FILE = Path("voting_state.json")
SETTINGS_FILE = Path("settings.json")
THUMBNAILS_DIR = Path("gin_thumbnails")

public_url = "https://gin-voting-app-aiwp54kyxjdaxba3aaqqth.streamlit.app/"

# -------------------------------
# AUTO REFRESH
# -------------------------------
st_autorefresh(interval=5000, key="refresh")

# -------------------------------
# INIT STATE
# -------------------------------
if not STATE_FILE.exists():
    with open(STATE_FILE, "w") as f:
        json.dump({"phase": "holding"}, f)

with open(STATE_FILE, "r") as f:
    phase = json.load(f).get("phase", "holding")

# -------------------------------
# SETTINGS
# -------------------------------
if SETTINGS_FILE.exists():
    with open(SETTINGS_FILE, "r") as f:
        settings = json.load(f)
else:
    settings = {"title": "Gin Judging Competition 🍸"}

# -------------------------------
# VOTES
# -------------------------------
gins = [f"Gin {i}" for i in range(1, 31)]

if VOTES_FILE.exists():
    with open(VOTES_FILE, "r") as f:
        data = json.load(f)
        all_votes = data.get("votes", {})
        voters = set(data.get("voters", []))
        comments = data.get("comments", {})
else:
    all_votes = {g: [] for g in gins}
    voters = set()
    comments = {}

for gin in gins:
    all_votes.setdefault(gin, [])
    comments.setdefault(gin, [])

# -------------------------------
# ADMIN PANEL
# -------------------------------
with st.expander("🔐 Admin Controls"):
    admin_password = st.secrets.get("ADMIN_PASSWORD", "admin123")
    entered_pw = st.text_input("Admin password", type="password")
    is_admin = entered_pw == admin_password

    if is_admin:
        col1, col2, col3, col4 = st.columns(4)

        if col1.button("🏁 Holding Page"):
            phase = "holding"

        if col2.button("▶️ Open Competition"):
            phase = "open"

        if col3.button("⏹ Close Competition"):
            phase = "closed"

        if col4.button("🎉 Reveal Winner"):
            phase = "presentation"

        with open(STATE_FILE, "w") as f:
            json.dump({"phase": phase}, f)

        if st.button("♻ Reset Everything"):
            all_votes = {g: [] for g in gins}
            voters = set()
            comments = {g: [] for g in gins}
            with open(VOTES_FILE, "w") as f:
                json.dump(
                    {"votes": all_votes, "voters": [], "comments": comments}, f
                )
            st.warning("All data reset")

# -------------------------------
# TITLE
# -------------------------------
st.markdown(f"# {settings['title']}")

# -------------------------------
# HOLDING PAGE
# -------------------------------
if phase == "holding":
    st.image("https://images.unsplash.com/photo-1582571352032-dc68d1ef8e6b", use_container_width=True)
    st.markdown("## 🍸 Competition starting soon…")
    st.markdown("Please take a seat and prepare your palate.")
    st.stop()

# -------------------------------
# VOTING PAGE
# -------------------------------
if phase == "open":
    voter_id = st.text_input("Enter your name or email to vote:")

    if voter_id in voters:
        st.warning("You have already voted.")
        st.stop()

    user_votes = {}
    for gin in gins:
        st.markdown(f"### {gin}")
        user_votes[gin] = st.slider("", 1, 10, 5, key=gin)

    top_gin = max(user_votes, key=user_votes.get)
    comment = st.text_area(
        f"What did you love about {top_gin}?",
        max_chars=300
    )

    if st.button("Submit Votes"):
        for gin, score in user_votes.items():
            all_votes[gin].append(score)
        if comment:
            comments[top_gin].append(comment)
        voters.add(voter_id)

        with open(VOTES_FILE, "w") as f:
            json.dump(
                {
                    "votes": all_votes,
                    "voters": list(voters),
                    "comments": comments
                },
                f
            )
        st.success("Thank you for voting!")
        st.balloons()

# -------------------------------
# CLOSED PAGE
# -------------------------------
if phase == "closed":
    st.markdown("## 🕰 Voting has closed")
    st.markdown("Please wait for the final presentation.")
    st.stop()

# -------------------------------
# FINAL PRESENTATION
# -------------------------------
if phase == "presentation":

    avg_scores = {
        gin: sum(v)/len(v) if v else 0
        for gin, v in all_votes.items()
    }

    top_3 = sorted(avg_scores, key=avg_scores.get, reverse=True)[:3]
    medals = ["🥉 Bronze", "🥈 Silver", "🥇 Gold"]

    st.markdown("## 🎉 Final Standings")
    time.sleep(2)

    for medal, gin in zip(medals, reversed(top_3)):
        st.markdown(f"## {medal}")
        st.markdown(f"### {gin} — {avg_scores[gin]:.2f}")
        time.sleep(2)

    st.balloons()

    gold = top_3[0]
    st.markdown("## 💬 What people loved about the winner")

    for c in comments[gold][:5]:
        st.markdown(f"> *{c}*")
        time.sleep(1)

# -------------------------------
# QR CODE
# -------------------------------
st.markdown("---")
st.markdown("### Share this app")

qr = qrcode.QRCode(box_size=5, border=2)
qr.add_data(public_url)
qr.make(fit=True)
img = qr.make_image(fill_color="black", back_color="white")
buf = BytesIO()
img.save(buf, format="PNG")
st.image(buf.getvalue())

