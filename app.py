from streamlit_autorefresh import st_autorefresh
import streamlit as st
import qrcode
import json
import pandas as pd
from io import BytesIO
from pathlib import Path
from collections import Counter
import time
import matplotlib.pyplot as plt

# --- Files to store data ---
VOTES_FILE = Path("gin_votes.json")
STATE_FILE = Path("voting_state.json")

# --- Streamlit Cloud Public URL ---
public_url = "https://<your-username>-gin-voting-app-main.streamlit.app"  # <-- replace with your deployed URL

# --- Initialize voting state ---
if not STATE_FILE.exists():
    with open(STATE_FILE, "w") as f:
        json.dump({"open": True}, f)

with open(STATE_FILE, "r") as f:
    state_data = json.load(f)
voting_open = state_data.get("open", True)

# --- Auto-refresh ---
AUTO_REFRESH_INTERVAL = 5  # seconds
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
elif time.time() - st.session_state.last_refresh > AUTO_REFRESH_INTERVAL:
    st.session_state.last_refresh = time.time()
    st.experimental_rerun()

# --- Load existing votes ---
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

# --- List of 30 gins ---
gins = [f"Gin {i}" for i in range(1, 31)]
for gin in gins:
    if gin not in all_votes:
        all_votes[gin] = []

# --- App title ---
st.title("Gin Judging Competition 🍸")
st.write("Please score each gin between 1 (poor) and 10 (excellent).")

# --- Admin Controls ---
st.sidebar.header("Admin Controls")
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

if st.sidebar.button("Reset All Votes (Admin Only)"):
    all_votes = {gin: [] for gin in gins}
    voters = set()
    with open(VOTES_FILE, "w") as f:
        json.dump({"votes": all_votes, "voters": list(voters)}, f)
    st.sidebar.warning("All votes have been reset!")

if st.sidebar.button("Download All Votes as CSV"):
    df = pd.DataFrame(all_votes)
    st.sidebar.download_button("Download CSV", df.to_csv(index=False), "gin_votes.csv", "text/csv")

# --- Compute averages ---
avg_scores = {}
for gin, scores in all_votes.items():
    numeric_scores = [int(s) for s in scores if str(s).isdigit()]
    avg_scores[gin] = sum(numeric_scores)/len(numeric_scores) if numeric_scores else 0

# --- Live Leaderboard ---
st.subheader("🏅 Live Leaderboard")
leaderboard_df = pd.DataFrame({
    "Gin": gins,
    "Average Score": [avg_scores[gin] for gin in gins],
    "Number of Votes": [len(all_votes[gin]) for gin in gins]
})
leaderboard_df = leaderboard_df.sort_values(by="Average Score", ascending=False).reset_index(drop=True)

# Highlight top 3
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

# --- Voting Section ---
if voting_open:
    voter_id = st.text_input("Enter your name or email to vote:")

    if voter_id and voter_id in voters:
        st.warning("You have already voted. Thank you!")
        try:
            user_votes = pd.read_csv(f"user_{voter_id}_votes.csv", index_col=0).to_dict()['Score']
            comparison_df = pd.DataFrame({
                "Gin": gins,
                "Your Score": [user_votes.get(gin, None) for gin in gins],
                "Average Score": [avg_scores[gin] for gin in gins]
            })
            comparison_df["Difference"] = comparison_df["Your Score"] - comparison_df["Average Score"]
            st.subheader("Your Votes vs Average")
            st.dataframe(comparison_df.style.highlight_max(subset=["Your Score"], color="lightgreen"), use_container_width=True)
        except FileNotFoundError:
            st.info("Your previous votes cannot be displayed.")
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

# --- Winner summary if voting closed ---
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

# --- QR code for sharing ---
st.subheader("Share this app via QR code")
qr = qrcode.QRCode(box_size=6, border=2)
qr.add_data(public_url)
qr.make(fit=True)
img = qr.make_image(fill_color="black", back_color="white")
buf = BytesIO()
img.save(buf, format="PNG")
buf.seek(0)
st.image(buf.getvalue(), caption=f"Scan to open: {public_url}")

# --- Hide Streamlit footer/menu ---
hide_st_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)
