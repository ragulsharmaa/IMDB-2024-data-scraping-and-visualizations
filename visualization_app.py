import mysql.connector
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns

# ------------------------------
# 1. Load and Clean Data
# ------------------------------
@st.cache_data
def load_movies_data():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="imdb_genre_wise"
    )
    query = "SELECT Title, Genre, Rating, Voting, Duration FROM movies_2024;"
    df = pd.read_sql(query, conn)
    conn.close()

    # Clean Voting
    df['Voting'] = (
        df['Voting'].astype(str)
        .str.replace('K', '000', regex=False)
        .str.replace(',', '', regex=False)
        .str.extract(r'(\d+)')
    )
    df['Voting'] = pd.to_numeric(df['Voting'], errors='coerce').fillna(0)

    # Clean Rating
    df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce').fillna(0)

    # Clean Duration (extract minutes)
    df['Duration'] = (
        df['Duration'].astype(str)
        .str.replace('h', 'h ', regex=False)  # Ensure space after h
    )
    def parse_duration(d):
        import re
        match = re.findall(r'(\d+)h', d)
        hours = int(match[0]) if match else 0
        mins = re.findall(r'(\d+)m', d)
        minutes = int(mins[0]) if mins else 0
        return hours * 60 + minutes if (hours or minutes) else None

    df['Duration'] = df['Duration'].apply(parse_duration)
    df['Duration'] = df['Duration'].fillna(df['Duration'].mean())

    # Clean Genre
    df['Genre'] = df['Genre'].str.strip().str.lower()

    # Normalize Score = Rating + Voting
    df['Voting_norm'] = df['Voting'] / df['Voting'].max()
    df['Rating_norm'] = df['Rating'] / 10
    df['Score'] = (df['Rating_norm'] * 0.5) + (df['Voting_norm'] * 0.5)

    # Drop duplicates
    df = df.sort_values(by=['Voting'], ascending=False).drop_duplicates(subset=['Title'], keep='first')

    return df


df = load_movies_data()

# ------------------------------
# 2. Sidebar Filters
# ------------------------------
st.sidebar.header("🔎 Filter Movies")

genres = sorted(df['Genre'].unique())
selected_genre = st.sidebar.multiselect("Select Genre(s)", genres, default=genres)

min_rating = st.sidebar.slider("Minimum Rating", 0.0, 10.0, 7.0, 0.1)
min_votes = st.sidebar.number_input("Minimum Votes", min_value=0, value=1000, step=500)
duration_range = st.sidebar.slider("Duration (minutes)", 60, 240, (90, 180))

filtered_df = df[
    (df['Genre'].isin(selected_genre)) &
    (df['Rating'] >= min_rating) &
    (df['Voting'] >= min_votes) &
    (df['Duration'].between(duration_range[0], duration_range[1]))
]

st.title("🎬 IMDb 2024 Movies Dashboard")

# Download filtered results
csv = filtered_df.to_csv(index=False).encode('utf-8')
st.download_button("📥 Download Filtered Movies", csv, "filtered_movies.csv", "text/csv")

# ------------------------------
# 3. Analytics & Visualizations
# ------------------------------

# 1. Top 10 Movies (by Score)
st.subheader("1️⃣ Top 10 Movies (Rating + Votes)")
top_movies = filtered_df.sort_values(by='Score', ascending=False).head(10)
st.write(top_movies[['Title', 'Genre', 'Rating', 'Voting']])

fig, ax = plt.subplots(figsize=(12, 6))
top_movies.plot(x='Title', y=['Rating', 'Voting'], kind='bar', ax=ax)
ax.set_title("Top 10 Movies by Rating & Voting")
plt.xticks(rotation=45)
st.pyplot(fig)

# 2. Genre Distribution
st.subheader("2️⃣ Movie Distribution by Genre")
genre_counts = filtered_df['Genre'].value_counts()
fig, ax = plt.subplots(figsize=(12, 6))
sns.barplot(x=genre_counts.index, y=genre_counts.values, palette="Set3", ax=ax)
ax.set_title("Number of Movies per Genre")
plt.xticks(rotation=45)
st.pyplot(fig)

# 3. Average Duration by Genre
st.subheader("3️⃣ Average Movie Duration per Genre")
avg_duration_per_genre = filtered_df.groupby('Genre')['Duration'].mean().sort_values()
fig, ax = plt.subplots(figsize=(12, 6))
sns.barplot(x=avg_duration_per_genre.values, y=avg_duration_per_genre.index, palette="Greens", ax=ax)
ax.set_title("Average Duration (minutes) per Genre")
st.pyplot(fig)

# 4. Average Voting per Genre
st.subheader("4️⃣ Average Voting Counts per Genre")
avg_voting_per_genre = filtered_df.groupby('Genre')['Voting'].mean().sort_values()
fig, ax = plt.subplots(figsize=(12, 6))
sns.barplot(x=avg_voting_per_genre.index, y=avg_voting_per_genre.values, palette="Blues", ax=ax)
ax.set_title("Average Voting per Genre")
plt.xticks(rotation=45)
st.pyplot(fig)

# 5. Rating Distribution
st.subheader("5️⃣ Rating Distribution")
fig, ax = plt.subplots(figsize=(12, 6))
sns.histplot(filtered_df['Rating'], bins=20, kde=True, color='blue', ax=ax)
ax.set_title("Histogram of Ratings")
st.pyplot(fig)

fig, ax = plt.subplots(figsize=(8, 6))
sns.boxplot(y=filtered_df['Rating'], color='red', ax=ax)
ax.set_title("Boxplot of Ratings")
st.pyplot(fig)

# 6. Top-rated movie per Genre
st.subheader("6️⃣ Top-rated Movie per Genre")
top_movies_by_genre = filtered_df.loc[filtered_df.groupby('Genre')['Rating'].idxmax(), ['Genre', 'Title', 'Rating']]
st.write(top_movies_by_genre)

# 7. Genres with Highest Total Votes
st.subheader("7️⃣ Genres with Highest Total Voting")
genre_voting_totals = filtered_df.groupby('Genre')['Voting'].sum().sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(10, 6))
genre_voting_totals.plot.pie(autopct='%1.1f%%', cmap="tab20", ax=ax)
ax.set_ylabel("")
st.pyplot(fig)

# 8. Shortest & Longest Movies
st.subheader("8️⃣ Shortest and Longest Movies")
shortest_movie = filtered_df.loc[filtered_df['Duration'].idxmin(), ['Title', 'Genre', 'Duration']]
longest_movie = filtered_df.loc[filtered_df['Duration'].idxmax(), ['Title', 'Genre', 'Duration']]
st.table(pd.DataFrame([shortest_movie, longest_movie]))

# 9. Heatmap: Average Rating per Genre
st.subheader("9️⃣ Heatmap of Average Rating by Genre")
avg_rating_per_genre = filtered_df.groupby('Genre')['Rating'].mean().to_frame()
fig, ax = plt.subplots(figsize=(10, 6))
sns.heatmap(avg_rating_per_genre, annot=True, cmap="coolwarm", linewidths=0.5, fmt=".2f", ax=ax)
st.pyplot(fig)

# 10. Scatter: Rating vs Voting
st.subheader("🔟 Scatter Plot: Rating vs Voting")
fig, ax = plt.subplots(figsize=(10, 6))
sns.scatterplot(data=filtered_df, x='Rating', y='Voting', hue='Genre', size='Voting', sizes=(20, 200), palette="tab10", ax=ax)
ax.set_title("Relationship between Rating and Voting")
plt.grid(True)
st.pyplot(fig)