import streamlit as st
import qrcode
import json
import pandas as pd
import time
from io import BytesIO
from pathlib import Path
from collections import Counter
from PIL import Image
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

public_url = "https://gin-voting-app-aiwp54kyxjdaxba3aaqqth.streamlit.app/"

# -------------------------------
# AUTO REFRESH
# -------------------------------
if phase in ["holding", "closed", "presentation"]:
    st_autorefresh(interval=5000, key="refresh")
# -------------------------------
# INIT STATE
# -------------------------------
if not STATE_FILE.exists():
    with open(STATE_FILE, "w") as f:
        json.dump(
            {"phase": "holding", "num_gins": 30},
            f
        )

with open(STATE_FILE, "r") as f:
    state = json.load(f)

phase = state.get("phase", "holding")
num_gins = state.get("num_gins", 30)

# -------------------------------
# GINS
# -------------------------------
gins = [f"Gin {i}" for i in range(1, num_gins + 1)]

# -------------------------------
# LOAD VOTES
# -------------------------------
if VOTES_FILE.exists():
    with open(VOTES_FILE, "r") as f:
        data = json.load(f)
        all_votes = data.get("votes", {})
        voters = set(data.get("voters", []))
        comments = data.get("comments", {})
else:
    all_votes = {}
    voters = set()
    comments = {}

for gin in gins:
    all_votes.setdefault(gin, [])
    comments.setdefault(gin, [])

# -------------------------------
# ADMIN PANEL
# -------------------------------
col1, col2, col3, col4 = st.columns(4)

def set_phase(new_phase):
    with open(STATE_FILE, "w") as f:
        json.dump(
            {
                "phase": new_phase,
                "num_gins": num
            },
            f
        )
    st.experimental_rerun()

if col1.button("🏁 Holding"):
    set_phase("holding")

if col2.button("▶️ Open"):
    set_phase("open")

if col3.button("⏹ Close"):
    set_phase("closed")

if col4.button("🎉 Reveal Winner"):
    set_phase("presentation")

# -------------------------------
# TITLE
# -------------------------------
st.markdown("# 🍸 Gin Judging Competition")

# -------------------------------
# QR CODE FUNCTION
# -------------------------------
def show_qr():
    qr = qrcode.QRCode(box_size=5, border=2)
    qr.add_data(public_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    st.image(buf.getvalue(), caption="Scan to join")

# -------------------------------
# HOLDING PAGE
# -------------------------------
if phase == "holding":
    st.markdown("## Competition starting soon…")
    st.markdown("Please scan the QR code to get ready.")
    show_qr()
    st.stop()

# -------------------------------
# VOTING
# -------------------------------
if phase == "open":
    voter_id = st.text_input("Enter your name or email")

    if voter_id in voters:
        st.warning("You have already voted.")
        st.stop()

    user_votes = {}
    for gin in gins:
        user_votes[gin] = st.slider(gin, 1, 10, 5)

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
# CLOSED
# -------------------------------
if phase == "closed":
    st.markdown("## Voting has closed")
    st.markdown("Please wait for the final reveal.")
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

    st.markdown("## 🎉 Final Standings")
    placeholder = st.empty()

    medals = [
        ("🥉 Bronze", top_3[2]),
        ("🥈 Silver", top_3[1]),
        ("🥇 Gold", top_3[0])
    ]

    for medal, gin in medals:
        placeholder.markdown(
            f"## {medal}\n### {gin} — {avg_scores[gin]:.2f}"
        )
        time.sleep(2)

    st.balloons()

    st.markdown("## 💬 What people loved about the winner")

    for c in comments.get(top_3[0], [])[:5]:
        st.markdown(f"> *{c}*")
        time.sleep(1)

# -------------------------------
# FOOTER CLEANUP
# -------------------------------
st.markdown(
    """
    <style>
    #MainMenu {visibility:hidden;}
    footer {visibility:hidden;}
    </style>
    """,
    unsafe_allow_html=True
)
