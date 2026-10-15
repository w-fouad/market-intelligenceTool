
import re
import sqlite3
from pathlib import Path

import pandas as pd
from google_play_scraper import Sort, reviews, search


# -----------------------------
# Project configuration
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "competitor_intelligence.db"
REPORT_DIR = BASE_DIR / "reports"

REPORT_DIR.mkdir(exist_ok=True)


# -----------------------------
# 1. Search Google Play
# -----------------------------
def search_apps(query, limit=10, lang="ar", country="ps"):
    """Search Google Play and return matching app information."""

    if not query or not query.strip():
        return pd.DataFrame()


    results = search(
    query.strip(),
    lang=lang,
    country=country
)

    results = results[:limit]


    apps = []

    for app in results:
        apps.append({
            "app_id": app.get("appId"),
            "title": app.get("title", "Unknown"),
            "developer": app.get("developer", "Unknown"),
            "rating": app.get("score"),
            "icon": app.get("icon"),
        })

    columns = ["app_id", "title", "developer", "rating", "icon"]
    return pd.DataFrame(apps, columns=columns).drop_duplicates("app_id")


# -----------------------------
# 2. Clean review text
# -----------------------------
def clean_text(text):
    """Normalize review text while preserving Arabic and English."""

    if not isinstance(text, str):
        return ""

    text = text.lower().strip()
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s\u0600-\u06FF]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# -----------------------------
# 3. Estimate sentiment
# -----------------------------
POSITIVE_WORDS = {
    "good", "great", "excellent", "easy", "love", "fast",
    "useful", "amazing", "ممتاز", "رائع", "جيد", "جميل",
    "سهل", "مفيد", "ممتازة", "حلو", "ممتعة"
}

NEGATIVE_WORDS = {
    "bad", "poor", "terrible", "slow", "crash", "bug",
    "problem", "error", "broken", "hate", "worst",
    "سيء", "سيئ", "بطيء", "مشكلة", "مشاكل", "خطأ",
    "يتوقف", "تعليق", "فاشل", "لا يعمل", "سيئة"
}


def analyze_sentiment(text, rating=None):
    """
    Lightweight sentiment estimate.
    Ratings take priority; text keywords are a fallback.
    """

    try:
        score = float(rating)
        if score <= 2:
            return "Negative"
        if score == 3:
            return "Neutral"
        if score >= 4:
            return "Positive"
    except (TypeError, ValueError):
        pass

    words = set(clean_text(text).split())
    positive = len(words & POSITIVE_WORDS)
    negative = len(words & NEGATIVE_WORDS)

    if positive > negative:
        return "Positive"
    if negative > positive:
        return "Negative"

    return "Neutral"


# -----------------------------
# 4. Initialize SQLite database
# -----------------------------
def initialize_database():
    """Create the reviews table if it does not already exist."""

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                review_id TEXT PRIMARY KEY,
                app_id TEXT NOT NULL,
                app_title TEXT,
                developer TEXT,
                rating INTEGER,
                review_text TEXT,
                clean_text TEXT,
                sentiment TEXT,
                review_date TEXT,
                thumbs_up INTEGER DEFAULT 0,
                scraped_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


# -----------------------------
# 5. Scrape app reviews
# -----------------------------
def scrape_app_reviews(
    app_id,
    app_title,
    developer="Unknown",
    limit=200,
    lang="ar",
    country="ps"
):
    """
    Fetch recent reviews and return a cleaned DataFrame.
    Limit is intentionally restricted to 150-300.
    """

    if not 150 <= limit <= 300:
        raise ValueError("Review limit must be between 150 and 300.")

    result, _ = reviews(
        app_id,
        lang=lang,
        country=country,
        sort=Sort.NEWEST,
        count=limit
    )

    rows = []

    for item in result:
        original_text = item.get("content", "")
        rating = item.get("score")

        review_id = item.get("reviewId")
        if not review_id:
            continue

        review_date = item.get("at")

        rows.append({
            "review_id": str(review_id),
            "app_id": app_id,
            "app_title": app_title,
            "developer": developer,
            "rating": rating,
            "review_text": original_text,
            "clean_text": clean_text(original_text),
            "sentiment": analyze_sentiment(original_text, rating),
            "review_date": (
                review_date.isoformat()
                if review_date is not None else None
            ),
            "thumbs_up": item.get("thumbsUpCount", 0),
        })

    columns = [
        "review_id", "app_id", "app_title", "developer", "rating",
        "review_text", "clean_text", "sentiment", "review_date",
        "thumbs_up"
    ]

    df = pd.DataFrame(rows, columns=columns)

    if not df.empty:
        df = df.drop_duplicates("review_id")

    return df


# -----------------------------
# 6. Save reviews to SQLite
# -----------------------------
def save_reviews(df):
    """Insert or update reviews without creating duplicate IDs."""

    if df is None or df.empty:
        return 0

    initialize_database()

    columns = [
        "review_id", "app_id", "app_title", "developer", "rating",
        "review_text", "clean_text", "sentiment", "review_date",
        "thumbs_up"
    ]

    with sqlite3.connect(DB_PATH) as conn:
        df[columns].to_sql(
            "incoming_reviews",
            conn,
            if_exists="replace",
            index=False
        )

        conn.execute("""
            INSERT OR REPLACE INTO reviews (
                review_id, app_id, app_title, developer, rating,
                review_text, clean_text, sentiment, review_date,
                thumbs_up
            )
            SELECT
                review_id, app_id, app_title, developer, rating,
                review_text, clean_text, sentiment, review_date,
                thumbs_up
            FROM incoming_reviews
        """)

        conn.execute("DROP TABLE incoming_reviews")
        conn.commit()

    return len(df)


# -----------------------------
# 7. Read saved reviews
# -----------------------------
def load_reviews(app_ids=None):
    """Load saved reviews, optionally filtered by app IDs."""

    initialize_database()

    with sqlite3.connect(DB_PATH) as conn:
        if app_ids:
            placeholders = ",".join("?" for _ in app_ids)
            query = (
                "SELECT * FROM reviews WHERE app_id IN "
                f"({placeholders}) ORDER BY review_date DESC"
            )
            return pd.read_sql_query(query, conn, params=list(app_ids))

        return pd.read_sql_query(
            "SELECT * FROM reviews ORDER BY review_date DESC",
            conn
        )


# -----------------------------
# 8. Generate multi-sheet Excel
# -----------------------------
def export_excel(df, filename="competitor_intelligence_report.xlsx"):
    """Export reviews and summary statistics to a multi-sheet workbook."""

    if df is None or df.empty:
        raise ValueError("No reviews available to export.")

    output_path = REPORT_DIR / filename

    app_summary = (
        df.groupby(["app_title", "app_id"], dropna=False)
        .agg(
            review_count=("review_id", "count"),
            average_rating=("rating", "mean"),
            positive=("sentiment", lambda s: (s == "Positive").sum()),
            neutral=("sentiment", lambda s: (s == "Neutral").sum()),
            negative=("sentiment", lambda s: (s == "Negative").sum()),
        )
        .reset_index()
    )

    sentiment_summary = (
        df.groupby(["app_title", "sentiment"], dropna=False)
        .size()
        .reset_index(name="review_count")
    )

    low_ratings = df[df["rating"].fillna(5) <= 2].copy()

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        app_summary.to_excel(
            writer, sheet_name="App_Comparison", index=False
        )
        sentiment_summary.to_excel(
            writer, sheet_name="Sentiment_Summary", index=False
        )
        df.to_excel(writer, sheet_name="All_Reviews", index=False)
        low_ratings.to_excel(
            writer, sheet_name="Low_Rating_Pain_Points", index=False
        )

    return output_path


def get_database_summary():
    """Return basic statistics about the saved review database."""

    initialize_database()

    with sqlite3.connect(DB_PATH) as conn:
        total_reviews = conn.execute(
            "SELECT COUNT(*) FROM reviews"
        ).fetchone()[0]

        total_apps = conn.execute(
            "SELECT COUNT(DISTINCT app_id) FROM reviews"
        ).fetchone()[0]

        summary = pd.read_sql_query(
            """
            SELECT
                app_title,
                COUNT(*) AS review_count,
                ROUND(AVG(rating), 2) AS average_rating
            FROM reviews
            GROUP BY app_id, app_title
            ORDER BY review_count DESC
            """,
            conn,
        )

    return {
        "total_reviews": total_reviews,
        "total_apps": total_apps,
        "summary": summary,
    }