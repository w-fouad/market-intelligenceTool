
import streamlit as st
import pandas as pd
import plotly.express as px

from market_engine import (
    search_apps,
    scrape_app_reviews,
    save_reviews,
    load_reviews,
    export_excel,
    get_database_summary,
    DB_PATH,
    REPORT_DIR,
)
from market_ai import analyze_market_gaps


st.set_page_config(
    page_title="Market Intelligence Tool",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Market Intelligence & Competitor Analysis")
st.write(
    "Discover Google Play competitors, analyze customer reviews, "
    "and identify potential market gaps."
)

# -----------------------------
# Sidebar settings
# -----------------------------
st.sidebar.header("Analysis Settings")

language = st.sidebar.selectbox(
    "Review language",
    options=["ar", "en"],
    index=0,
)

country = st.sidebar.selectbox(
    "Google Play country",
    options=["ps", "us", "gb", "sa", "ae"],
    index=0,
)

review_limit = st.sidebar.slider(
    "Reviews per app",
    min_value=150,
    max_value=300,
    value=200,
    step=50,
)

# -----------------------------
# App search
# -----------------------------
st.header("1. Discover Competitor Apps")

query = st.text_input(
    "Search by app name or market niche",
    placeholder="e.g. food delivery, banking, fitness",
)

if st.button("Search Google Play", type="primary"):
    if not query.strip():
        st.warning("Enter an app name or market niche first.")
    else:
        try:
            with st.spinner("Searching Google Play..."):
                results = search_apps(
                    query,
                    limit=10,
                    lang=language,
                    country=country,
                )

            st.session_state["search_results"] = results

            if results.empty:
                st.info("No matching apps were found.")
        except Exception as exc:
            st.error(f"App search failed: {exc}")

# -----------------------------
# Display search results
# -----------------------------
search_results = st.session_state.get(
    "search_results",
    pd.DataFrame(),
)

selected_apps = []

if not search_results.empty:
    st.subheader("Search Results")

    for _, app in search_results.iterrows():
        app_id = app["app_id"]

        col1, col2, col3 = st.columns([1, 5, 2])

        with col1:
            if isinstance(app.get("icon"), str) and app["icon"]:
                st.image(app["icon"], width=55)

        with col2:
            st.write(f"**{app['title']}**")
            st.caption(
                f"Developer: {app['developer']} | "
                f"Rating: {app['rating']}"
            )
            st.caption(f"App ID: {app_id}")

        with col3:
            chosen = st.checkbox(
                "Select",
                key=f"select_{app_id}",
            )

            if chosen:
                selected_apps.append(app.to_dict())

        st.divider()

    st.caption("Select between 2 and 4 apps for competitor analysis.")

    # -----------------------------
    # Run analysis
    # -----------------------------
    if st.button("Analyze Selected Competitors", type="primary"):
        if not 2 <= len(selected_apps) <= 4:
            st.error("Please select between 2 and 4 apps.")
        else:
            frames = []
            failures = []

            progress = st.progress(0)

            for index, app in enumerate(selected_apps):
                try:
                    with st.spinner(
                        f"Fetching reviews for {app['title']}..."
                    ):
                        df = scrape_app_reviews(
                            app_id=app["app_id"],
                            app_title=app["title"],
                            developer=app["developer"],
                            limit=review_limit,
                            lang=language,
                            country=country,
                        )

                        if not df.empty:
                            save_reviews(df)
                            frames.append(df)
                        else:
                            failures.append(
                                f"{app['title']}: no reviews returned"
                            )

                except Exception as exc:
                    failures.append(f"{app['title']}: {exc}")

                progress.progress((index + 1) / len(selected_apps))

            if frames:
                new_reviews = pd.concat(
                    frames,
                    ignore_index=True,
                ).drop_duplicates("review_id")

                st.session_state["analysis_app_ids"] = [
                    app["app_id"] for app in selected_apps
                ]

                st.session_state["latest_reviews"] = new_reviews

                st.success(
                    f"Collected {len(new_reviews)} unique reviews "
                    "from the selected apps."
                )

            for failure in failures:
                st.warning(failure)

# -----------------------------
# Load data for dashboard
# -----------------------------
app_ids = st.session_state.get("analysis_app_ids", [])

if app_ids:
    data = load_reviews(app_ids)

    if not data.empty:
        db_stats = get_database_summary()

        st.subheader("Database Statistics")

        db_col1, db_col2 = st.columns(2)

        db_col1.metric(
            "Reviews Stored in SQLite",
            db_stats["total_reviews"]
        )

        db_col2.metric(
            "Apps in Database",
            db_stats["total_apps"]
        )
        st.header("2. Competitor Overview")

        metric1, metric2, metric3 = st.columns(3)

        metric1.metric("Total Reviews", len(data))

        average_rating = pd.to_numeric(
            data["rating"], errors="coerce"
        ).mean()

        metric2.metric(
            "Average Review Rating",
            f"{average_rating:.2f}/5"
            if pd.notna(average_rating)
            else "N/A",
        )

        metric3.metric(
            "Apps Analyzed",
            data["app_id"].nunique(),
        )

        # -----------------------------
        # Charts
        # -----------------------------
        left, right = st.columns(2)

        with left:
            rating_data = (
                data.groupby("app_title")["rating"]
                .mean()
                .reset_index()
            )

            fig_rating = px.bar(
                rating_data,
                x="app_title",
                y="rating",
                title="Average Rating in Collected Reviews",
                labels={
                    "app_title": "App",
                    "rating": "Average rating",
                },
            )

            st.plotly_chart(
                fig_rating,
                use_container_width=True,
            )

        with right:
            sentiment_data = (
                data.groupby(["app_title", "sentiment"])
                .size()
                .reset_index(name="count")
            )

            fig_sentiment = px.bar(
                sentiment_data,
                x="app_title",
                y="count",
                color="sentiment",
                barmode="stack",
                title="Estimated Review Sentiment",
                color_discrete_map={
        "Positive": "#1A62CE",
        "Neutral": "#9E9E9E",
        "Negative": "#D60C0C",
    },
            )

            st.plotly_chart(
                fig_sentiment,
                use_container_width=True,
            )

        # -----------------------------
        # Review table and filters
        # -----------------------------
        st.header("3. Customer Feedback")

        sentiment_filter = st.multiselect(
            "Filter by estimated sentiment",
            options=["Positive", "Neutral", "Negative"],
            default=["Positive", "Neutral", "Negative"],
        )

        filtered = data[
            data["sentiment"].isin(sentiment_filter)
        ]

        st.dataframe(
            filtered[
                [
                    "app_title",
                    "rating",
                    "sentiment",
                    "review_date",
                    "review_text",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        # -----------------------------
        # AI analysis
        # -----------------------------
        st.header("4. AI-Powered Market Gap Analysis")

        if st.button("Generate AI Recommendations"):
            with st.spinner("Analyzing low-rated reviews..."):
                report = analyze_market_gaps(data)

            st.session_state["ai_report"] = report

        if st.session_state.get("ai_report"):
            st.markdown(st.session_state["ai_report"])

        # -----------------------------
        # Excel report
        # -----------------------------
        st.header("5. Download Reports")

        if st.button("Generate Excel Report"):
            try:
                path = export_excel(data)

                st.session_state["excel_path"] = str(path)
                st.success("Excel report generated.")
            except Exception as exc:
                st.error(f"Excel export failed: {exc}")

        excel_path = st.session_state.get("excel_path")

        if excel_path:
            try:
                with open(excel_path, "rb") as file:
                    st.download_button(
                        "Download Excel Report",
                        data=file,
                        file_name="competitor_intelligence_report.xlsx",
                        mime=(
                            "application/vnd.openxmlformats-officedocument."
                            "spreadsheetml.sheet"
                        ),
                    )
            except OSError:
                st.warning("Generate the Excel report again to download it.")

        # -----------------------------
        # SQLite database download
        # -----------------------------
        if DB_PATH.exists():
            with open(DB_PATH, "rb") as file:
                st.download_button(
                    "Download SQLite Database",
                    data=file,
                    file_name="competitor_intelligence.db",
                    mime="application/octet-stream",
                )

        st.caption(
            "Sentiment labels are estimates, not validated psychological "
            "or linguistic classifications. Results describe the collected "
            "sample and may not represent all app users."
        )

else:
    st.info(
        "Search for apps, select 2–4 competitors, and run an analysis "
        "to populate the dashboard."
    )
