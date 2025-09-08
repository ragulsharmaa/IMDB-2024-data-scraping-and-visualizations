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
        .str.replace('h', 'h ', regex=False)
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

# Genre filter
genres = sorted(df['Genre'].unique())
selected_genres = st.sidebar.multiselect("Select Genre(s)", genres, default=genres)

# Rating filter
min_rating, max_rating = st.sidebar.slider("Select Rating Range", 0.0, 10.0, (7.0, 10.0), 0.1)

# Voting filter
votes_range = st.sidebar.slider("Voting Count Range", 0, int(df['Voting'].max()), (1000, int(df['Voting'].max())))

# Duration filters
duration_category = st.sidebar.selectbox(
    "Select Duration Category",
    ["All", "Short (<90 min)", "Medium (90-150 min)", "Long (>150 min)"]
)
duration_range = (df['Duration'].min(), df['Duration'].max())
if duration_category == "Short (<90 min)":
    duration_range = (0, 90)
elif duration_category == "Medium (90-150 min)":
    duration_range = (90, 150)
elif duration_category == "Long (>150 min)":
    duration_range = (150, df['Duration'].max())

# Top-N movies selection
top_n = st.sidebar.slider("Top N Movies to Display", 5, 20, 10)

# ------------------------------
# 3. Apply Filters
# ------------------------------
@st.cache_data
def filter_data(df, genres, rating_min, rating_max, votes, dur_range):
    filtered = df[
        (df['Genre'].isin(genres)) &
        (df['Rating'].between(rating_min, rating_max)) &
        (df['Voting'].between(votes[0], votes[1])) &
        (df['Duration'].between(dur_range[0], dur_range[1]))
    ]
    return filtered

filtered_df = filter_data(df, selected_genres, min_rating, max_rating, votes_range, duration_range)

st.title("🎬 IMDb 2024 Movies Dashboard")

# Download filtered results
csv = filtered_df.to_csv(index=False).encode('utf-8')
st.download_button("📥 Download Filtered Movies", csv, "filtered_movies.csv", "text/csv")

# ------------------------------
# 4. Visualizations & Analytics
# ------------------------------

# 1. Top N Movies by Score
st.subheader(f"1️⃣ Top {top_n} Movies (Rating + Votes)")
top_movies = filtered_df.sort_values(by='Score', ascending=False).head(top_n)
st.write(top_movies[['Title', 'Genre', 'Rating', 'Voting']])

fig, ax = plt.subplots(figsize=(12, 6))
top_movies.plot(x='Title', y=['Rating', 'Voting'], kind='bar', ax=ax)
ax.set_title(f"Top {top_n} Movies by Rating & Voting")
plt.xticks(rotation=45)
st.pyplot(fig)

# 2. Movie Distribution by Genre
st.subheader("2️⃣ Movie Distribution by Genre")
genre_counts = filtered_df['Genre'].value_counts()
fig, ax = plt.subplots(figsize=(12, 6))
sns.barplot(x=genre_counts.index, y=genre_counts.values, palette="Set3", ax=ax)
ax.set_title("Number of Movies per Genre")
plt.xticks(rotation=45)
st.pyplot(fig)

# 3. Average Duration per Genre
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

# 6. Top-rated Movie per Genre
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
if not filtered_df.empty:
    shortest_movie = filtered_df.loc[filtered_df['Duration'].idxmin(), ['Title', 'Genre', 'Duration']]
    longest_movie = filtered_df.loc[filtered_df['Duration'].idxmax(), ['Title', 'Genre', 'Duration']]
    st.table(pd.DataFrame([shortest_movie, longest_movie]))
else:
    st.write("No movies match the filters.")

# 9. Heatmap: Average Rating per Genre
st.subheader("9️⃣ Heatmap of Average Rating by Genre")
avg_rating_per_genre = filtered_df.groupby('Genre')['Rating'].mean().to_frame()
fig, ax = plt.subplots(figsize=(10, 6))
sns.heatmap(avg_rating_per_genre, annot=True, cmap="coolwarm", linewidths=0.5, fmt=".2f", ax=ax)
st.pyplot(fig)

# 10. Scatter: Rating vs Voting
st.subheader("🔟 Scatter Plot: Rating vs Voting")
fig, ax = plt.subplots(figsize=(10, 6))
sns.scatterplot(
    data=filtered_df,
    x='Rating',
    y='Voting',
    hue='Genre',
    size='Voting',
    sizes=(20, 200),
    palette="tab10",
    ax=ax
)
ax.set_title("Relationship between Rating and Voting")
plt.grid(True)
st.pyplot(fig)