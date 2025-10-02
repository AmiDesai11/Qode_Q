"""
Streamlit Dashboard for X Scraper with Analysis & Insights

Provides a user-friendly interface to configure, run the X scraper,
and analyze tweets with text-to-signal conversion for trading insights.
"""

import os
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA
from datetime import datetime
import re
from collections import Counter

from scraper import Scraper

# Page configuration
st.set_page_config(
    page_title="X Scraper & Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1DA1F2;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #1DA1F2;
        color: white;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #1a8cd8;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1DA1F2;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">📊 X Scraper & Trading Signal Analysis</div>', unsafe_allow_html=True)

# Initialize session state
if 'analysis_data' not in st.session_state:
    st.session_state.analysis_data = None
if 'output_path' not in st.session_state:
    st.session_state.output_path = None

# Tabs for different sections
tab1, tab2 = st.tabs(["🔍 Scraper", "📈 Analysis & Insights"])

# ==================== TAB 1: SCRAPER ====================
with tab1:
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # ChromeDriver Path
        driver_path = st.text_input(
            "ChromeDriver Path",
            placeholder="e.g., ./chromedriver.exe",
            help="Path to your ChromeDriver executable"
        )
        
        # Headless mode
        headless = st.checkbox(
            "Run in Headless Mode",
            value=False,
            help="Run browser in background without UI"
        )
        
        st.divider()
        
        # Login credentials
        st.subheader("🔐 Login Credentials")
        username = st.text_input(
            "Username/Email/Phone",
            placeholder="Your X username",
            help="Leave empty to scrape as guest"
        )
        
        password = st.text_input(
            "Password",
            type="password",
            placeholder="Your X password",
            help="Leave empty to scrape as guest"
        )
        
        if not password and os.environ.get("X_PASS"):
            st.info("Using password from X_PASS environment variable")
            password = os.environ.get("X_PASS")
        
        st.divider()
        
        # Scraping parameters
        st.subheader("📊 Scraping Parameters")
        per_tag_target = st.number_input(
            "Tweets per Hashtag",
            min_value=10,
            max_value=30,
            value=30,
            step=1,
            help="Target number of tweets to collect per hashtag"
        )

    # Main content area
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🏷️ Hashtags to Scrape")
        
        # Text area for hashtags
        hashtags_input = st.text_area(
            "Enter hashtags (one per line or comma-separated)",
            placeholder="#nifty50\n#sensex\n#stockmarket",
            height=150,
            help="Enter hashtags with or without the # symbol"
        )

    with col2:
        st.subheader("ℹ️ Information")
        st.info("""
        **How to use:**
        1. Set ChromeDriver path
        2. Add login credentials
        3. Enter hashtags to scrape
        4. Click 'Start Scraping'
        5. Analyze in the next tab
        
        **Output Location:**
        `../io/dd-mm-yyyy/tweets.parquet`
        """)

    # Parse hashtags
    def parse_hashtags(text):
        if not text:
            return []
        text = text.replace("\n", ",")
        tags = [tag.strip() for tag in text.split(",") if tag.strip()]
        tags = [tag if tag.startswith("#") else f"#{tag}" for tag in tags]
        return tags

    # Display parsed hashtags
    hashtags = parse_hashtags(hashtags_input)
    if hashtags:
        st.write("**Hashtags to scrape:**")
        cols = st.columns(min(len(hashtags), 5))
        for i, tag in enumerate(hashtags):
            with cols[i % len(cols)]:
                st.code(tag)

    # Start scraping button
    st.divider()

    col_button1, col_button2, col_button3 = st.columns([1, 2, 1])

    with col_button2:
        start_button = st.button("🚀 Start Scraping", use_container_width=True, type="primary")

    # Scraping logic
    if start_button:
        errors = []
        
        if not driver_path:
            errors.append("ChromeDriver path is required")
        elif not Path(driver_path).exists():
            errors.append(f"ChromeDriver not found at: {driver_path}")
        
        if not hashtags:
            errors.append("Please enter at least one hashtag")
        
        if errors:
            for error in errors:
                st.error(error)
        else:
            status_placeholder = st.empty()
            
            try:
                with st.spinner("Initializing scraper..."):
                    scraper = Scraper(driver_path=driver_path, headless=headless)
                
                status_placeholder.info(f"Starting scraper for {len(hashtags)} hashtag(s)...")
                
                with st.spinner("Scraping in progress... This may take several minutes."):
                    output_path = scraper.run(
                        username=username if username else None,
                        password=password if password else None,
                        hashtags=hashtags,
                        per_tag_target=per_tag_target
                    )
                
                status_placeholder.empty()
                st.success("Scraping completed successfully!")
                
                st.markdown(f"**📁 Output saved to:** `{output_path}`")
                
                # Load data for analysis
                df = pd.read_parquet(output_path)
                st.session_state.analysis_data = df
                st.session_state.output_path = output_path
                
                # Display statistics
                st.subheader("📊 Scraping Statistics")
                
                metric_cols = st.columns(4)
                with metric_cols[0]:
                    st.metric("Total Tweets", len(df))
                with metric_cols[1]:
                    st.metric("Unique Users", df['handle'].nunique() if 'handle' in df.columns else 0)
                with metric_cols[2]:
                    st.metric("Hashtags Scraped", len(hashtags))
                with metric_cols[3]:
                    st.metric("File Size", f"{Path(output_path).stat().st_size / 1024:.1f} KB")
                
                st.balloons()
                st.info("Switch to the 'Analysis & Insights' tab to view trading signals!")
                
            except Exception as e:
                status_placeholder.empty()
                st.error(f"Error occurred during scraping: {str(e)}")

# ==================== TAB 2: ANALYSIS & INSIGHTS ====================
with tab2:
    st.header("📈 Text-to-Signal Analysis for Trading")
    
    # File selector
    col1, col2 = st.columns([3, 1])
    with col1:
        # Check for existing files
        io_path = Path("../io")
        available_files = []
        if io_path.exists():
            for date_folder in sorted(io_path.iterdir(), reverse=True):
                if date_folder.is_dir():
                    parquet_file = date_folder / "tweets.parquet"
                    if parquet_file.exists():
                        available_files.append(str(parquet_file))
        
        if available_files:
            selected_file = st.selectbox(
                "Select a data file to analyze",
                options=available_files,
                index=0
            )
        else:
            st.warning("No data files found. Please scrape some data first in the Scraper tab.")
            selected_file = None
    
    with col2:
        if selected_file and st.button("🔄 Load Data", use_container_width=True):
            try:
                st.session_state.analysis_data = pd.read_parquet(selected_file)
                st.session_state.output_path = selected_file
                st.success("Data loaded!")
            except Exception as e:
                st.error(f"Error loading file: {e}")
    
    # Proceed with analysis if data is available
    if st.session_state.analysis_data is not None:
        df = st.session_state.analysis_data.copy()
        
        # Data preprocessing
        df['content'] = df['content'].fillna('')
        df['timestamp_iso'] = pd.to_datetime(df['timestamp_iso'], errors='coerce')
        
        # Sentiment keywords (simple approach for demonstration)
        bullish_keywords = ['bullish', 'buy', 'long', 'moon', 'pump', 'rally', 'surge', 'gain', 'profit', 'up', 'high', 'rise', 'bull']
        bearish_keywords = ['bearish', 'sell', 'short', 'dump', 'crash', 'drop', 'loss', 'down', 'low', 'fall', 'bear']
        
        def calculate_sentiment_score(text):
            text_lower = text.lower()
            bullish_count = sum(1 for word in bullish_keywords if word in text_lower)
            bearish_count = sum(1 for word in bearish_keywords if word in text_lower)
            return bullish_count - bearish_count
        
        df['sentiment_score'] = df['content'].apply(calculate_sentiment_score)
        
        # Normalize engagement metrics
        for col in ['reply_count', 'retweet_count', 'like_count', 'view_count']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Create engagement signal
        df['engagement_signal'] = (
            df['like_count'] * 1 + 
            df['retweet_count'] * 2 + 
            df['reply_count'] * 1.5
        )
        
        # Normalize signals
        if df['engagement_signal'].std() > 0:
            df['engagement_signal_norm'] = (df['engagement_signal'] - df['engagement_signal'].mean()) / df['engagement_signal'].std()
        else:
            df['engagement_signal_norm'] = 0
            
        if df['sentiment_score'].std() > 0:
            df['sentiment_signal_norm'] = (df['sentiment_score'] - df['sentiment_score'].mean()) / df['sentiment_score'].std()
        else:
            df['sentiment_signal_norm'] = 0
        
        # Composite trading signal with confidence intervals
        df['composite_signal'] = (df['sentiment_signal_norm'] * 0.6 + df['engagement_signal_norm'] * 0.4)
        
        # Calculate confidence based on data volume
        df['confidence'] = np.minimum(100, (df['engagement_signal'] / df['engagement_signal'].quantile(0.95)) * 100)
        
        # Display overview metrics
        st.subheader("📊 Signal Overview")
        
        metric_cols = st.columns(5)
        with metric_cols[0]:
            avg_sentiment = df['sentiment_score'].mean()
            st.metric("Avg Sentiment", f"{avg_sentiment:.2f}", 
                     delta="Bullish" if avg_sentiment > 0 else "Bearish")
        with metric_cols[1]:
            bullish_pct = (df['sentiment_score'] > 0).sum() / len(df) * 100
            st.metric("Bullish Tweets", f"{bullish_pct:.1f}%")
        with metric_cols[2]:
            bearish_pct = (df['sentiment_score'] < 0).sum() / len(df) * 100
            st.metric("Bearish Tweets", f"{bearish_pct:.1f}%")
        with metric_cols[3]:
            avg_composite = df['composite_signal'].mean()
            st.metric("Composite Signal", f"{avg_composite:.3f}",
                     delta="Buy" if avg_composite > 0.1 else ("Sell" if avg_composite < -0.1 else "Neutral"))
        with metric_cols[4]:
            avg_confidence = df['confidence'].mean()
            st.metric("Avg Confidence", f"{avg_confidence:.1f}%")
        
        st.divider()
        
        # TF-IDF Analysis
        st.subheader("🔤 TF-IDF Feature Extraction")
        
        with st.expander("View TF-IDF Analysis", expanded=False):
            # Sample data for memory efficiency
            sample_size = min(1000, len(df))
            df_sample = df.sample(n=sample_size, random_state=42) if len(df) > sample_size else df
            
            try:
                # TF-IDF vectorization
                vectorizer = TfidfVectorizer(
                    max_features=50,
                    stop_words='english',
                    ngram_range=(1, 2),
                    min_df=2
                )
                
                tfidf_matrix = vectorizer.fit_transform(df_sample['content'])
                feature_names = vectorizer.get_feature_names_out()
                
                # Get top features
                tfidf_scores = tfidf_matrix.sum(axis=0).A1
                top_indices = tfidf_scores.argsort()[-20:][::-1]
                top_features = [(feature_names[i], tfidf_scores[i]) for i in top_indices]
                
                # Display top features
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Top 20 TF-IDF Features:**")
                    feature_df = pd.DataFrame(top_features, columns=['Feature', 'TF-IDF Score'])
                    st.dataframe(feature_df, use_container_width=True, height=400)
                
                with col2:
                    # Visualize top features
                    fig = px.bar(
                        feature_df.head(15),
                        x='TF-IDF Score',
                        y='Feature',
                        orientation='h',
                        title='Top 15 TF-IDF Features'
                    )
                    fig.update_layout(yaxis={'categoryorder': 'total ascending'}, height=400)
                    st.plotly_chart(fig, use_container_width=True)
                
                # PCA for dimensionality reduction
                if tfidf_matrix.shape[0] > 2:
                    pca = PCA(n_components=2)
                    pca_result = pca.fit_transform(tfidf_matrix.toarray())
                    
                    pca_df = pd.DataFrame(pca_result, columns=['PC1', 'PC2'])
                    pca_df['sentiment'] = df_sample['sentiment_score'].values
                    
                    fig = px.scatter(
                        pca_df,
                        x='PC1',
                        y='PC2',
                        color='sentiment',
                        title='Tweet Clustering (PCA - TF-IDF Features)',
                        color_continuous_scale='RdYlGn'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
            except Exception as e:
                st.warning(f"TF-IDF analysis requires more diverse text data: {e}")
        
        st.divider()
        
        # Signal Aggregation & Visualization
        st.subheader("📉 Signal Aggregation & Trading Indicators")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Time-series signal (if timestamps available)
            if 'timestamp_iso' in df.columns and df['timestamp_iso'].notna().any():
                df_time = df.dropna(subset=['timestamp_iso']).copy()
                df_time = df_time.sort_values('timestamp_iso')
                
                # Resample to hourly aggregates for memory efficiency
                df_time.set_index('timestamp_iso', inplace=True)
                
                # Sample for plotting if too large
                if len(df_time) > 1000:
                    step = len(df_time) // 1000
                    df_plot = df_time.iloc[::step].copy()
                else:
                    df_plot = df_time.copy()
                
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=df_plot.index,
                    y=df_plot['composite_signal'].rolling(window=10, min_periods=1).mean(),
                    mode='lines',
                    name='Composite Signal (MA)',
                    line=dict(color='blue', width=2)
                ))
                
                fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
                fig.add_hline(y=0.5, line_dash="dot", line_color="green", opacity=0.3, annotation_text="Strong Buy")
                fig.add_hline(y=-0.5, line_dash="dot", line_color="red", opacity=0.3, annotation_text="Strong Sell")
                
                fig.update_layout(
                    title='Composite Trading Signal Over Time',
                    xaxis_title='Time',
                    yaxis_title='Signal Strength',
                    hovermode='x unified',
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Time-series analysis requires valid timestamps")
        
        with col2:
            # Signal distribution
            fig = go.Figure()
            
            fig.add_trace(go.Histogram(
                x=df['composite_signal'],
                nbinsx=50,
                name='Signal Distribution',
                marker_color='lightblue'
            ))
            
            fig.add_vline(x=0, line_dash="dash", line_color="black", opacity=0.5)
            fig.add_vline(x=df['composite_signal'].mean(), line_dash="dot", line_color="red", 
                         annotation_text=f"Mean: {df['composite_signal'].mean():.3f}")
            
            fig.update_layout(
                title='Composite Signal Distribution',
                xaxis_title='Signal Value',
                yaxis_title='Frequency',
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Hashtag-specific signals
        st.subheader("🏷️ Signal Breakdown by Hashtag")
        
        if '_queried_hashtag' in df.columns:
            hashtag_signals = df.groupby('_queried_hashtag').agg({
                'composite_signal': 'mean',
                'sentiment_score': 'mean',
                'engagement_signal': 'mean',
                'confidence': 'mean',
                'tweet_id': 'count'
            }).round(3)
            hashtag_signals.columns = ['Composite Signal', 'Sentiment', 'Engagement', 'Confidence %', 'Tweet Count']
            hashtag_signals = hashtag_signals.sort_values('Composite Signal', ascending=False)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig = px.bar(
                    hashtag_signals.reset_index(),
                    x='_queried_hashtag',
                    y='Composite Signal',
                    color='Composite Signal',
                    color_continuous_scale='RdYlGn',
                    title='Composite Signal by Hashtag'
                )
                fig.update_layout(xaxis_title='Hashtag', yaxis_title='Signal Strength')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.dataframe(hashtag_signals, use_container_width=True, height=400)
        
        # Confidence Intervals
        st.subheader("📊 Signal Confidence Analysis")
        
        # Create confidence bands
        signal_bins = pd.qcut(df['composite_signal'], q=5, labels=['Strong Sell', 'Sell', 'Neutral', 'Buy', 'Strong Buy'], duplicates='drop')
        confidence_analysis = df.groupby(signal_bins, observed=True).agg({
            'confidence': ['mean', 'std', 'count']
        }).round(2)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.dataframe(confidence_analysis, use_container_width=True)
        
        with col2:
            fig = go.Figure()
            
            for signal_type in confidence_analysis.index:
                mean_conf = confidence_analysis.loc[signal_type, ('confidence', 'mean')]
                std_conf = confidence_analysis.loc[signal_type, ('confidence', 'std')]
                
                fig.add_trace(go.Box(
                    y=df[signal_bins == signal_type]['confidence'],
                    name=str(signal_type),
                    boxmean='sd'
                ))
            
            fig.update_layout(
                title='Confidence Distribution by Signal Type',
                yaxis_title='Confidence %',
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Export processed signals
        st.divider()
        st.subheader("💾 Export Processed Signals")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Download Signal Data", use_container_width=True):
                output_df = df[['tweet_id', 'content', 'timestamp_iso', '_queried_hashtag', 
                               'sentiment_score', 'engagement_signal', 'composite_signal', 'confidence']]
                csv = output_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"trading_signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        with col2:
            # Show summary stats
            with st.expander("📊 Summary Statistics"):
                st.write(df[['sentiment_score', 'engagement_signal', 'composite_signal', 'confidence']].describe())
    
    else:
        st.info("No data loaded. Please scrape data in the 'Scraper' tab or load an existing file.")

# Footer
st.divider()
st.caption("Trading signals are for informational purposes only. Always conduct your own research before making trading decisions.")