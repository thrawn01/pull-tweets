# Tweet Extraction Tool

A Research tool for extracting tweets from X.com (Twitter) using the twikit
library. This tool saves tweet data to parquet files with intelligent rate
limiting and memory-efficient processing.

## ✨ Features

- **🔓 No API Keys Required**: Uses twikit to access X.com without official API credentials
- **📅 Flexible Duration**: Extract tweets from any time period using natural language ("7 days", "1 month")
- **💾 Memory Efficient**: Streams data in batches to handle large extractions without memory issues
- **🔄 Auto-Resume**: Automatically saves progress and can resume interrupted extractions
- **📊 Comprehensive Data**: Extracts all available tweet metadata including engagement metrics
- **🛡️ Smart Rate Limiting**: Intelligent rate limiting with exponential backoff
- **📈 Parquet Output**: Efficient columnar format compatible with pandas, DuckDB, and other analysis tools

## 🚀 Quick Start with UV

### Prerequisites

- Python 3.11+ (UV will use your system Python if compatible)
- [UV](https://docs.astral.sh/uv/) package manager

### Clone and Setup

```bash
git clone git@github.com:thrawn01/pull-tweets.git
cd pull-tweets

# UV will automatically create a virtual environment and install dependencies
uv sync
```

### Configure Credentials

```bash
cp config.yaml.template config.yaml
# Edit config.yaml with research account X.com credentials
```

### Fetch Tweets

```bash
# Basic usage
uv run python pull_tweets.py @elonmusk -o tweets.parquet

# With custom duration
uv run python pull_tweets.py @username --duration "7 days" -o tweets_7d.parquet
```

## ⚙️ Configuration
> NOTE: Highly recommend creating a research account for data extraction. Do not
> use your personal account with this tool.

```yaml
# X.com Authentication
auth:
  username: "your_username"
  email: "your_email@example.com"
  password: "your_password"
  
# Rate Limiting Settings
rate_limiting:
  base_delay_seconds: 4.0
  max_retries: 5
  backoff_multiplier: 2.0
  
# Output Settings
output:
  include_engagement_metrics: true
  include_media_info: true
  date_format: "ISO"
  batch_size: 50
  
# Processing Settings
processing:
  checkpoint_interval: 100  # Save progress every N tweets
  max_memory_mb: 500        # Force batch write if memory usage exceeds this limit
```

### Command Line Options

```
uv run python pull_tweets.py <username> --output-file <filename> [options]

Required Arguments:
  username              Twitter username (with or without @)
  --output-file, -o     Output parquet filename (e.g., tweets.parquet)

Optional Arguments:
  --duration, -d        Time period to go back (default: "30 days")
                        Examples: "7 days", "1 month", "2 weeks", "1 year"
  --config CONFIG       Path to config.yaml file (default: ./config.yaml)
  --resume              Resume from existing checkpoint if present (progress is always saved)
  --batch-size SIZE     Number of tweets to process per batch (default: 50)
  --verbose, -v         Enable verbose logging
```

### Duration Formats

The tool accepts various natural language duration formats:

```bash
# Days
uv run python pull_tweets.py @user -d "7 days" -o tweets.parquet

# Weeks  
uv run python pull_tweets.py @user -d "2 weeks" -o tweets.parquet

# Months
uv run python pull_tweets.py @user -d "1 month" -o tweets.parquet

# Years
uv run python pull_tweets.py @user -d "1 year" -o tweets.parquet

# Hours (for recent activity)
uv run python pull_tweets.py @user -d "24 hours" -o tweets.parquet
```

## 📊 Output Data Schema

The parquet file contains comprehensive tweet metadata:

### Core Tweet Data
- `id`: Unique tweet identifier
- `text`: Tweet text content
- `full_text`: Complete tweet text (if available)
- `created_at`: Tweet creation timestamp (ISO 8601)
- `lang`: Tweet language code

### User Information
- `user_id`: User's unique identifier
- `user_screen_name`: Username (@handle)
- `user_name`: Display name

### Engagement Metrics
- `favorite_count`: Number of likes
- `retweet_count`: Number of retweets  
- `reply_count`: Number of replies
- `quote_count`: Number of quote tweets
- `view_count`: Number of views
- `bookmark_count`: Number of bookmarks

### Content Metadata
- `hashtags`: Array of hashtags used
- `urls`: Array of URLs mentioned
- `media`: Media attachments (JSON string)
- `has_card`: Whether tweet has a preview card
- `is_quote_status`: Whether tweet is a quote tweet
- `possibly_sensitive`: Content sensitivity flag

### Thread Information
- `in_reply_to`: ID of tweet being replied to
- `conversation_id`: Thread conversation identifier

## 📈 Data Analysis Examples

### Export to Markdown

Extract tweet content in markdown format for research and analysis:

```bash
# Extract original tweets (excludes retweets) to markdown
uv run python extract_to_markdown.py tweets.parquet research_notes.md

# Include retweets if needed
uv run python extract_to_markdown.py tweets.parquet all_tweets.md --include-retweets
```

**Output format:**
```markdown
## 2025-09-06 19:43:35
Everyone's always trying to make SQL better. What if we made SQL more SQL-y.

## 2025-09-06 19:34:36  
Iowa State is onto something..

You heard it here first on the Locker Room. @TaylorLewan77 @JoshPateCFB 
```

Perfect for:
- Qualitative research and content analysis
- Import into note-taking apps
- LLM Analysis

### Load and Explore Data

```python
import pandas as pd

# Load with pandas
df = pd.read_parquet('tweets.parquet')
print(f"Extracted {len(df)} tweets")
```

### Analysis Examples

```python
# Top hashtags
hashtags = df['hashtags'].explode().value_counts().head(10)
print("Top hashtags:")
print(hashtags)

# Engagement analysis
engagement = df[['favorite_count', 'retweet_count', 'reply_count']].describe()
print("Engagement metrics:")
print(engagement)

# Tweet frequency over time
df['date'] = pd.to_datetime(df['created_at']).dt.date
daily_tweets = df['date'].value_counts().sort_index()
print("Daily tweet counts:")
print(daily_tweets.tail())

# Most retweeted tweets
top_tweets = df.nlargest(5, 'retweet_count')[['text', 'retweet_count', 'created_at']]
print("Most retweeted:")
print(top_tweets)
```

### DuckDB CLI Analysis

For larger datasets and advanced analytics, use the DuckDB CLI directly - no Python dependencies needed!

**Basic Tweet Summary:**
```bash
duckdb -c "
SELECT 
    COUNT(*) as total_tweets,
    ROUND(AVG(favorite_count)) as avg_likes,
    ROUND(AVG(retweet_count)) as avg_retweets, 
    ROUND(AVG(view_count)) as avg_views,
    MAX(favorite_count) as most_liked
FROM 'tweets.parquet';"
```

**Output:**
```
┌──────────────┬───────────┬──────────────┬───────────┬────────────┐
│ total_tweets │ avg_likes │ avg_retweets │ avg_views │ most_liked │
│    int64     │  double   │    double    │  double   │   int64    │
├──────────────┼───────────┼──────────────┼───────────┼────────────┤
│           85 │    1954.0 │        171.0 │  164475.0 │      58684 │
└──────────────┴───────────┴──────────────┴───────────┴────────────┘
```

**Most Engaging Tweets:**
```bash
duckdb -c "
SELECT 
    SUBSTRING(text, 1, 60) || '...' as tweet_preview,
    favorite_count,
    view_count,
    (favorite_count + view_count/100) as engagement_score
FROM 'tweets.parquet'
WHERE text NOT LIKE 'RT @%'  -- Exclude retweets
ORDER BY engagement_score DESC
LIMIT 5;"
```

**Output:**
```
┌─────────────────────────────────────────────────┬────────────────┬────────────┬──────────────────┐
│                 tweet_preview                   │ favorite_count │ view_count │ engagement_score │
├─────────────────────────────────────────────────┼────────────────┼────────────┼──────────────────┤
│ A+ joke by the way ...                          │          58684 │    3304315 │         91727.15 │
│ I invented a thought controlled air freshene..  │          22429 │    1748634 │         39915.34 │
│ I need the apology for saying Peyton Manning... │          15680 │    1056758 │         26247.58 │
│ Let me just ask - Is the SEC overrated?...      │           8202 │     577566 │         13977.66 │
└─────────────────────────────────────────────────┴────────────────┴────────────┴──────────────────┘
```

**Tweet Timeline Analysis:**
```bash
duckdb -c "
SELECT 
    DATE_TRUNC('day', created_at) as day,
    COUNT(*) as tweets_per_day,
    ROUND(AVG(view_count)) as avg_views_per_day
FROM 'tweets.parquet'
GROUP BY day
ORDER BY day DESC;"
```

**Extract All Tweet Text:**
```bash
duckdb -c "
SELECT 
    created_at,
    text,
    favorite_count as likes,
    view_count as views
FROM 'tweets.parquet'
WHERE text NOT LIKE 'RT @%'  -- Original tweets only
ORDER BY created_at DESC;"
```

**Advanced Analytics:**
```bash
# Find tweets with high engagement rate
duckdb -c "
SELECT 
    text,
    ROUND(100.0 * favorite_count / NULLIF(view_count, 0), 2) as engagement_rate_pct
FROM 'tweets.parquet'
WHERE view_count > 1000 AND text NOT LIKE 'RT @%'
ORDER BY engagement_rate_pct DESC
LIMIT 10;"

# Hashtag analysis
duckdb -c "
SELECT 
    UNNEST(hashtags) as hashtag,
    COUNT(*) as usage_count
FROM 'tweets.parquet'
WHERE hashtags IS NOT NULL AND LENGTH(hashtags) > 0
GROUP BY hashtag
ORDER BY usage_count DESC;"
```

**Export Tweet Text to File:**
```bash
duckdb -c "
COPY (
    SELECT text
    FROM 'tweets.parquet'
    WHERE text NOT LIKE 'RT @%'  -- Exclude retweets
    ORDER BY created_at DESC
) TO 'tweets.txt' (FORMAT CSV, HEADER false, DELIMITER '|');
"
```

This extracts only original tweet text (excluding retweets) and saves it to `tweets.txt`, one tweet per line.

## 🚀 Tips

### For Large Extractions

- **Optimize batch size**: Increase `batch_size` to 100-200 for better performance
- **Automatic progress saving**: Progress is saved every 100 tweets (configurable), use `--resume` if extraction fails
- **Memory management**: Tool automatically monitors and manages memory usage (configurable via `max_memory_mb`)
- **Run during off-peak**: Better rate limits during non-peak hours

## 🔒 Security & Privacy
> Highly recommend creating a research account for data extraction.

- **Credentials**: Stored locally in `config.yaml`.
- **Session cookies**: Cached in `.twikit_cookies` for faster authentication
- **Data privacy**: All extracted data stays on your machine
- **Rate limiting**: Respects X.com's rate limits to avoid account penalties

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚖️ Legal Notice

This tool is for educational and research purposes. Users are responsible for
complying with X.com's Terms of Service and applicable laws. Always respect
rate limits and user privacy.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 🔧 Development

### Using UV for Development

```bash
# Install with development dependencies
uv sync --group dev

# Run tests
uv run pytest

# Format code
uv run black .
uv run isort .

# Lint code  
uv run ruff check .

# Type checking
uv run mypy .
```
---

Made with ❤️ using [UV](https://docs.astral.sh/uv/) for blazing-fast Python dependency management.
