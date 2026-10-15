Market Intelligence & Competitor Scraping Tool

Project Overview

A Python-based web application that collects and analyzes Google Play reviews to help identify competitor strengths, customer complaints, missing features, and potential market opportunities.

Main Features

Search for mobile applications on Google Play.

Compare 2–4 selected competitor applications.

Collect recent reviews from Google Play.

Clean and normalize review text.

Classify review sentiment as Positive, Neutral, or Negative.

Store review data in an SQLite database.

Visualize competitor ratings and sentiment using Plotly.

Export results to a multi-sheet Excel report.

Generate AI-powered market gap insights using Google Gemini when an API key is configured.

Technologies Used

Python

Pandas

Google Play Scraper

SQLite

Streamlit

Plotly

OpenPyXL

Google Gen AI SDK

Installation

Install Python 3.10 or later.

Clone or download this repository.

Open a terminal in the project directory.

Install the required packages:

pip install -r requirements.txt

Run the Application

python -m streamlit run app.py

Open the local URL displayed in the terminal.

How to Use

Enter an application name or search keyword.

Select between two and four competitor applications.

Choose the review language, country, and review count.

Run the competitor analysis.

Explore ratings, sentiment charts, and customer reviews.

Download the Excel report.

Gemini AI Configuration

AI analysis requires a valid Gemini API key.

Set the GEMINI_API_KEY environment variable or configure it using Streamlit secrets. Never commit API keys to the repository.

Database and Reports

The application stores collected reviews in competitor_intelligence.db and generates Excel reports in the reports directory.

Limitations

Search results and review availability depend on Google Play.

Review sentiment classification is an estimate and may misclassify sarcasm, context, or mixed-language feedback.

AI recommendations depend on the available review evidence and require human review.

The database and generated reports are local files unless separately configured for persistent cloud storage.

Author

Market Intelligence & Competitor Scraping Tool Project WAAD FOUAD ABUHAMAD