import streamlit as st
import qrcode
import json
import pandas as pd
from io import BytesIO
from pathlib import Path
from collections import Counter
from PIL import Image
import matplotlib.pyplot as plt
from streamlit_autorefresh import st_autorefresh

# -------------------------------
# FILES FOR DATA AND SETTINGS
# -------------------------------
VOTES_FILE = Path("gin_votes.json")
STATE_FILE = Path("voting_state.json")
SETTINGS_FILE = Path("settings.json")

# -------------------------------
# PUBLIC URL FOR QR CODE
# -------------------------------
public_url = "https://<your-username>-gin-voting-app-main.streamlit.app"  # Replace with your deployed URL

# -------------------------------
# AUTO REFRESH
# -------------------------------
st_autorefresh(interval=5000, key="live_refresh")  # refresh every 5s

# -------------------------------
# LOAD OR INITIALIZE VOTING STATE
# -------------------------------
if not STATE_FILE.exists():
    with open(STATE_FILE, "w") as f:
        json.dump({"open": True}, f)
with open(STATE_FILE, "r") as f:
    state_data = json.load(f)
voting_open = state_data.get("open", True)

# -------------------------------
# LOAD OR INITIALIZE SETTINGS
# -------------------------------
if SETTINGS_FILE.exists():
    with open(SETTINGS_FILE, "r") as f:
        settings = json.load(f)
else:
    settings = {"title": "Gin Judging Competition 🍸", "image": None}

# -------------------------------
# LOAD OR INITIALIZE VOTES
# -------------------------------
all_votes = {}
voters = set()
if VOTES_FILE.exists():
    try:
        with open(VOTES_FILE, "r") as f:
            data = json.load(f)
            all_votes = data.get("votes", {})
            voters = set(data.get("voters", []))
    except (json.JSONDecodeError, ValueError):
        all_votes = {}
        voters = set()

# 30 Gins
gins = [f"Gin {i}" for i in range(1, 31)]
for gin in gins:
    if gin not in all_votes:
        all_votes[gin] = []

# -------------------------------
# ADMIN CONTROLS
# -------------------------------
st.sidebar.header("Admin Controls")

# Open / Close / Reset Voting
if st.sidebar.button("Open Voting"):
    voting_open = True
    with open(STATE_FILE, "w") as f:
        json.dump({"open": True}, f)
    st.sidebar.success("Voting is now OPEN.")

if st.sidebar.button("Close Voting"):
    voting_open = False
    with open(STATE_FILE, "w") as f:
        json.dump({"open": False}, f)
    st.sidebar.warning("Voting is now CLOSED.")

if st.sidebar.button("Reset All Votes"):
    all_votes = {gin: [] for gin in gins}
    voters = set()
    with open(VOTES_FILE, "w") as f:
        json.dump({"votes": all_votes, "voters": list(voters)}, f)
    st.sidebar.warning("All votes have been reset!")

# Download CSV
if st.sidebar.button("Download All Votes as CSV"):
    df = pd.DataFrame(all_votes)
    st.sidebar.download_button("Download CSV", df.to_csv(index=False), "gin_votes.csv", "text/csv")

# -------------------------------
# ADMIN CUSTOM TITLE / IMAGE
# -------------------------------
custom_title = st.sidebar.text_input("Page Title", settings.get("title", "Gin Judging Competition 🍸"))
uploaded_file = st.sidebar.file_uploader("Upload an image for the title", type=["png", "jpg", "jpeg"])

if st.sidebar.button("Save Title and Image"):
    settings["title"] = custom_title
    if uploaded_file:
        img = Image.open(uploaded_file)
        img_path = Path("title_image.png")
        img.save(img_path)
        settings["image"] = str(img_path)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)
    st.sidebar.success("Settings saved!")

# -------------------------------
# DISPLAY TITLE AND IMAGE
# -------------------------------
title_col, img_col = st.columns([4, 1])
title_col.header(settings.get("title", "Gin Judging Competition 🍸"))
if settings.get("image") and Path(settings["image"]).exists():
    img = Image.open(settings["image"])
    img_col.image(img, use_container_width=True)  # <-- fixed deprecation warning

# -------------------------------
# COMPUTE AVERAGES
# -------------------------------
avg_scores = {}
for gin, scores in all_votes.items():
    numeric_scores = [int(s) for s in scores if str(s).isdigit()]
    avg_scores[gin] = sum(numeric_scores)/len(numeric_scores) if numeric_scores else 0

# -------------------------------
# LEADERBOARD
# -------------------------------
st.subheader("🏅 Live Leaderboard")
leaderboard_df = pd.DataFrame({
    "Gin": gins,
    "Average Score": [avg_scores[gin] for gin in gins],
    "Number of Votes": [len(all_votes[gin]) for gin in gins]
})
leaderboard_df = leaderboard_df.sort_values(by="Average Score", ascending=False).reset_index(drop=True)

def highlight_top(row):
    if row.name == 0:
        return ["background-color: gold"]*3
    elif row.name == 1:
        return ["background-color: silver"]*3
    elif row.name == 2:
        return ["background-color: #CD7F32"]*3
    else:
        return [""]*3

st.dataframe(leaderboard_df.style.apply(highlight_top, axis=1), use_container_width=True)

# -------------------------------
# VOTING SECTION
# -------------------------------
if voting_open:
    voter_id = st.text_input("Enter your name or email to vote:")

    if voter_id and voter_id in voters:
        st.warning("You have already voted. Thank you!")
    elif voter_id:
        user_votes = {}
        for gin in gins:
            score = st.slider(f"Score for {gin}", 1, 10, 5)
            user_votes[gin] = score

        if st.button("Submit Votes"):
            for gin, score in user_votes.items():
                all_votes[gin].append(int(score))
            voters.add(voter_id)
            with open(VOTES_FILE, "w") as f:
                json.dump({"votes": all_votes, "voters": list(voters)}, f)
            pd.DataFrame({"Gin": list(user_votes.keys()), "Score": list(user_votes.values())}).set_index("Gin").to_csv(f"user_{voter_id}_votes.csv")
            st.success("Thank you for voting! Your votes have been added.")
else:
    st.warning("Voting is currently CLOSED. Results are final.")

# -------------------------------
# WINNER SUMMARY IF VOTING CLOSED
# -------------------------------
if not voting_open and avg_scores:
    st.subheader("Top 3 Gins Vote Distribution")
    top_colors = ["#FFD700", "#C0C0C0", "#CD7F32"]
    sorted_gins = sorted(avg_scores, key=avg_scores.get, reverse=True)[:3]

    for i, gin in enumerate(sorted_gins):
        st.markdown(f"### {gin} ({avg_scores[gin]:.2f} average, {len(all_votes[gin])} votes)")
        scores_counter = Counter(all_votes[gin])
        scores_list = [scores_counter.get(j, 0) for j in range(10, 0, -1)]
        fig, ax = plt.subplots(figsize=(6,4))
        ax.barh(range(10, 0, -1), scores_list, color=top_colors[i], edgecolor='black')
        ax.set_yticks(range(10, 0, -1))
        ax.set_yticklabels(range(10, 0, -1))
        ax.set_xlabel("Number of Votes")
        ax.set_ylabel("Score")
        ax.set_title(f"Vote Distribution for {gin}")
        st.pyplot(fig)

# -------------------------------
# QR CODE
# -------------------------------
st.subheader("Share this app via QR code")
qr = qrcode.QRCode(box_size=6, border=2)
qr.add_data(public_url)
qr.make(fit=True)
img = qr.make_image(fill_color="black", back_color="white")
buf = BytesIO()
img.save(buf, format="PNG")
buf.seek(0)
st.image(buf.getvalue(), caption=f"Scan to open: {public_url}")

# -------------------------------
# HIDE STREAMLIT FOOTER / MENU
# -------------------------------
hide_st_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)
