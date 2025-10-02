# X Scraper & Trading Signal Analysis

A Python-based web scraping tool for collecting tweets from X (formerly Twitter) and performing sentiment analysis to generate trading signals for financial markets.

## 🚨 Important Notes

### API Usage Strongly Recommended
**Using official APIs is significantly better than web scraping.** Web scraping:
- Violates X's Terms of Service
- Is fragile and breaks when the website structure changes
- Can result in account suspension or legal action
- Is inefficient and resource-intensive

**Always prefer official APIs** (X API v2, etc.) for production use. This project is for **educational purposes only**.

### Parser Limitations
This project implements **basic HTML parsing** for tweet extraction. To make it more robust for production use, you should:
- Add parsers for different tweet layouts (quoted tweets, media tweets, polls)
- Handle threaded conversations
- Parse embedded cards (links, videos, images)
- Extract additional metadata (verified badges, reply context, etc.)
- Implement retry logic for failed parsing attempts
- Add validation for extracted data

## 📋 Features

- **Automated Scraping**: Selenium-based automation for X.com
- **Multi-Hashtag Support**: Scrape multiple hashtags in a single run
- **Trading Signal Analysis**: Convert tweet sentiment into actionable trading signals
- **TF-IDF Analysis**: Extract key features from tweet content
- **Interactive Dashboard**: Streamlit-based UI for configuration and visualization
- **Comprehensive Logging**: Structured logging for debugging and monitoring

## 🏗️ Project Structure

```
x-scraper/
├── src 
│   └──scraper.py           # Core scraping logic with Selenium
│   └── dashboard.py        # Streamlit dashboard for UI and analysis
│   └── logger.py           # Centralized logging module
│
├── README.md           # This file
├── io/                 # Output directory for scraped data
│   └── dd-mm-yyyy/     # Date-wise folders
│       └── tweets.parquet
└── logs/               # Application logs
    └── dd-mm-yyyy/
        └── app.log
```

## 🔧 Requirements

```bash
pip install -r requirements.txt
```

Additional requirements:
- **ChromeDriver**: Download from [chromedriver.chromium.org](https://chromedriver.chromium.org/)
- Chrome/Chromium browser installed

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Download ChromeDriver

Download the appropriate ChromeDriver for your Chrome version and place it in your project directory.

### 3. Run the Dashboard

```bash
streamlit run dashboard.py
```

### 4. Configure & Scrape

1. Enter ChromeDriver path in the sidebar
2. Add X login credentials
3. Enter hashtags to scrape (e.g., `#nifty50`, `#sensex`)
4. Click "Start Scraping"
5. Switch to "Analysis & Insights" tab to view results

## 🔍 How It Works

### Scraping Flow (per hashtag)

1. **Login**: Authenticate with X (optional, can scrape as guest)
2. **Navigate**: Click Explore icon
3. **Search**: Enter hashtag in search box
4. **Filter**: Click "Latest" tab for recent tweets
5. **Scroll**: Load at least 500 tweets (configurable)
6. **Capture**: Extract HTML from tweet container
7. **Parse**: Extract tweet data with BeautifulSoup
8. **Save**: Store as Parquet file

### Analysis Pipeline

1. **Sentiment Scoring**: Keyword-based sentiment analysis
   - Bullish keywords: buy, long, rally, surge, gain, profit, etc.
   - Bearish keywords: sell, short, crash, drop, loss, fall, etc.

2. **Engagement Signal**: Weighted combination of interactions
   - Formula: `likes × 1 + retweets × 2 + replies × 1.5`

3. **Composite Signal**: Normalized trading indicator
   - Formula: `sentiment × 0.6 + engagement × 0.4`

4. **Confidence Scoring**: Based on engagement volume

## 📈 Dashboard Features

### Scraper Tab
- Configure ChromeDriver path
- Set login credentials
- Enter hashtags to scrape
- Monitor scraping progress
- View scraping statistics

### Analysis & Insights Tab
- **Signal Overview**: Key metrics at a glance
- **TF-IDF Analysis**: Extract important terms from tweets
- **PCA Clustering**: Visualize tweet similarity
- **Time Series**: Track signals over time
- **Signal Distribution**: Histogram of trading signals
- **Hashtag Breakdown**: Compare signals across hashtags
- **Confidence Analysis**: Signal reliability metrics
- **CSV Export**: Download processed signals

## 🎨 Visualizations

1. **TF-IDF Features**: Top keywords by importance
2. **PCA Clustering**: Tweet similarity scatter plot
3. **Time Series**: Signal strength over time with buy/sell zones
4. **Signal Distribution**: Histogram with mean indicator
5. **Hashtag Signals**: Bar chart comparing hashtags
6. **Confidence Box Plots**: Signal reliability by category

### Scraping Parameters

- `per_tag_target`: Tweets to collect per hashtag (default: 500)
- `MAX_SCROLLS`: Maximum scroll attempts (default: 300)
- `SCROLL_PAUSE`: Wait time between scrolls (default: 0.8s)
- `WAIT`: Selenium wait timeout (default: 18s)

## 📝 Logging

Logs are saved to `../logs/dd-mm-yyyy/app.log` with the format:

```
HH:MM:SS - LEVEL - CLASS - FUNCTION - LINE - MESSAGE
```

Levels: INFO, WARNING, ERROR, DEBUG, CRITICAL

## 🛡️ Error Handling

- Robust selector fallbacks for UI elements
- Graceful degradation when login fails
- Continues scraping even if one hashtag fails
- Validates ChromeDriver path before starting
- Handles missing data fields in parsing

## ⚠️ Limitations & Considerations

### Legal & Ethical
- Web scraping may violate X's Terms of Service
- Risk of account suspension
- Rate limiting and IP blocks possible
- Not suitable for production or commercial use

### Technical
- **Basic parser**: Only extracts standard tweet format
- **No advanced features**: No support for:
  - Quoted tweets
  - Poll tweets
  - Media-heavy tweets
  - Threaded conversations
  - Reply context
- **Fragile**: Breaks when X updates their HTML structure
- **Slow**: Selenium is resource-intensive
- **Guest limitations**: Reduced access without login

### Analysis
- Keyword-based sentiment is simplistic
- No machine learning models
- Assumes engagement = importance
- No bot detection or filtering
- Time-series analysis requires sufficient data points

## 🔮 Future Improvements

### Recommended Enhancements
1. **Use Official API**: Migrate to X API v2 for reliability
2. **Advanced Parsers**: Handle all tweet types and formats
3. **ML Sentiment Analysis**: Use BERT/FinBERT for better accuracy
4. **Bot Detection**: Filter out automated accounts
5. **Real-time Streaming**: WebSocket for live data
6. **Database Integration**: Store data in PostgreSQL/MongoDB
7. **Backtesting**: Historical signal validation
8. **Alert System**: Notifications for strong signals

## 📚 Data Schema

### Scraped Tweet Fields

```python
{
    "tweet_id": str,
    "display_name": str,
    "handle": str,
    "username": str,
    "timestamp_iso": str,
    "timestamp_relative": str,
    "content": str,
    "hashtags": list,
    "mentions": list,
    "reply_count": int,
    "retweet_count": int,
    "like_count": int,
    "view_count": int,
    "_queried_hashtag": str  # Added during scraping
}
```

### Computed Analysis Fields

```python
{
    "sentiment_score": float,        # Net bullish/bearish score
    "engagement_signal": float,      # Weighted interaction score
    "engagement_signal_norm": float, # Normalized engagement
    "sentiment_signal_norm": float,  # Normalized sentiment
    "composite_signal": float,       # Combined trading signal
    "confidence": float              # Signal confidence percentage
}
```

## 🤝 Contributing

Contributions welcome! Priority areas:
1. Robust parsers for different tweet types
2. ML-based sentiment analysis
3. API integration instead of scraping
4. Better error handling
5. Unit tests

## ⚖️ License

Educational use only. Not for production or commercial purposes.

## 📧 Disclaimer

This tool is for **educational purposes only**. The authors:
- Do not encourage violating any Terms of Service
- Are not responsible for misuse of this software
- Recommend using official APIs for any serious application
- Provide no warranty for trading signals generated

**Trading signals are informational only. Always conduct your own research before making trading decisions.**

---

**Remember**: APIs > Web Scraping. Always choose the official, supported method when available.