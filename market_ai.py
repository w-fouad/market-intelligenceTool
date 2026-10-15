
import os
import pandas as pd
from google import genai


def analyze_market_gaps(reviews_df):
    """
    Analyze low-rated Google Play reviews using Gemini AI.
    Identify customer complaints, missing features,
    market opportunities, and strategic recommendations.
    """

    # 1. Check whether review data is available
    if reviews_df is None or reviews_df.empty:
        return "No reviews are available for market gap analysis."

    # 2. Check required columns
    required_columns = {"review_text", "rating", "app_title"}

    if not required_columns.issubset(reviews_df.columns):
        missing = required_columns - set(reviews_df.columns)
        return f"Missing required columns: {', '.join(sorted(missing))}"

    # 3. Select one-star and two-star reviews
    ratings = pd.to_numeric(reviews_df["rating"], errors="coerce")

    low_rated = reviews_df.loc[ratings <= 2].copy()

    if low_rated.empty:
        return "No one-star or two-star reviews were found."

    # 4. Prepare review text for AI analysis
    sample = low_rated[["app_title", "rating", "review_text"]].head(100)

    review_lines = []

    for _, row in sample.iterrows():
        text = str(row["review_text"]).strip()

        if text and text.lower() != "nan":
            review_lines.append(
                f"App: {row['app_title']} | "
                f"Rating: {row['rating']} | "
                f"Review: {text[:500]}"
            )

    if not review_lines:
        return "Low-rated reviews contain no usable text."

    # 5. Get the Gemini API key
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GEMINI_API_KEY")
        except Exception:
            api_key = None

    if not api_key:
        return (
            "Gemini analysis is not configured. "
            "Set GEMINI_API_KEY in your environment or "
            "Streamlit secrets to enable AI analysis."
        )

    # 6. Build the AI prompt
    reviews_text = "\n".join(review_lines)

    prompt = f"""
You are a mobile-app market research analyst.

Analyze the following real low-rated Google Play reviews.

Identify:
1. Recurring bugs and customer complaints.
2. Missing or desired features.
3. Opportunities competitors are failing to address.
4. Three practical strategic recommendations for a new app.

Requirements:
- Use only evidence supported by the supplied reviews.
- Separate observed evidence from hypotheses.
- Do not invent review data.
- Do not claim a problem is frequent without sufficient evidence.
- Compare apps only where the available evidence supports it.
- Write in clear, professional English.
- Include a short limitations note.

LOW-RATED REVIEWS:
{reviews_text}
"""

    # 7. Send the reviews to Gemini
    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        if response.text:
            return response.text

        return "Gemini returned an empty response."

    except Exception as exc:
        return (
            "Gemini analysis failed. Check your API key, "
            "internet connection, and model availability.\n"
            f"Technical details: {exc}"
        )

