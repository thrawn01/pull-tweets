# Tweet Extraction Tool Implementation Plan

## Overview

Building a Python script that extracts tweets from X.com for a specific user using the twikit library, saving all tweet data to a parquet file. The tool will work without requiring official API access and includes rate limiting, date-based filtering, and comprehensive data extraction.

## Current State Analysis

**Repository Status**: Empty Git repository ready for initial project setup

**Key Requirements**:
- Extract tweets from specified X.com user
- Use twikit library to bypass official API requirements
- Save all available tweet metadata to parquet format
- Implement intelligent rate limiting and error handling
- Filter tweets by configurable time duration
- Support configuration via YAML file

## Desired End State

A command-line tool that can be executed as:
```bash
python pull_tweets.py @username --duration "7 days" --output-file tweets.parquet
# Or using short aliases:
python pull_tweets.py @username -d "7 days" -o tweets.parquet
```

**Verification**: Successfully extract tweets from a test user account, save to timestamped parquet file, and verify data completeness with configurable time-based filtering.

### Key Design Decisions:
- **Duration Format**: Use dateutil library to parse natural language durations ("7 days", "1 month", "2 years")
- **Authentication**: Cookie-based session with credential storage in config.yaml (no 2FA support)
- **Rate Limiting**: Exponential backoff with twikit-specific exception handling
- **Data Schema**: Complete tweet metadata extraction with all available twikit Tweet fields
- **Memory Management**: Streaming batch processing with configurable batch sizes
- **Resume Capability**: Checkpoint/resume from existing parquet files
- **Error Handling**: Graceful handling of private accounts, rate limits, and network issues
- **Output**: Single parquet file per execution with user-specified filename

## What We're NOT Doing

- Real-time streaming or monitoring
- Multi-user batch processing (single user per execution)
- Tweet content analysis or processing
- Direct database integration (parquet files only)
- GUI interface (CLI only)
- Tweet posting or interaction capabilities
- Two-factor authentication support
- Nested tweet extraction (replies to replies, quoted tweet content)
- Additional HTTP calls for missing metadata
- Loading entire tweet history into memory

## Implementation Approach

**Technology Stack**:
- **twikit**: X.com data extraction
- **pandas + pyarrow**: Streaming parquet file generation and data handling
- **argparse**: Command-line interface
- **PyYAML**: Configuration file management
- **dateutil**: Natural language date parsing
- **asyncio**: Asynchronous tweet retrieval

**Architecture**: Single-threaded async script with modular components for authentication, data extraction, rate limiting, and streaming file output. Implements memory-efficient batch processing with checkpoint/resume capability.

## Phase 1: Python Environment and Project Structure Setup

### Overview
Set up a Python virtual environment, project structure, and all necessary dependencies with configuration templates.

### Changes Required:

#### 1. Python Environment Setup
**Environment Setup Commands**:
```bash
# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Upgrade pip to latest version
pip install --upgrade pip
```

#### 2. Project Structure Files
**Files to Create**:
- `requirements.txt`
- `config.yaml.template`
- `pull_tweets.py`
- `.gitignore`
- `README.md`
- `.python-version` (for version consistency)

**Dependencies List**:
```text
twikit>=2.0.0
pandas>=2.0.0
pyarrow>=12.0.0
PyYAML>=6.0
python-dateutil>=2.8.0
aiofiles>=0.8.0
psutil>=5.8.0
```

**Configuration Template Structure**:
```yaml
# X.com Authentication
auth:
  username: ""
  email: ""
  password: ""
  
# Rate Limiting Settings
rate_limiting:
  base_delay_seconds: 2.0
  max_retries: 5
  backoff_multiplier: 2.0
  
# Output Settings
output:
  include_engagement_metrics: true
  include_media_info: true
  date_format: "ISO"  # Stores as ISO 8601 strings, compatible with DuckDB datetime parsing
  batch_size: 50
  
# Processing Settings
processing:
  enable_resume: true
  checkpoint_interval: 100
  max_memory_mb: 500
```

**Python Environment Files**:
```text
# .python-version
3.11.0

# .gitignore additions for Python
__pycache__/
*.py[cod]
*$py.class
*.so
venv/
env/
.env
*.egg-info/
dist/
build/
.pytest_cache/
.coverage
*.parquet
*.checkpoint
config.yaml
.twikit_cookies
```

**Testing Requirements**:
```python
def test_virtual_environment_setup()
def test_requirements_installation()
def test_config_template_validity()
def test_python_version_compatibility()
```

**Test Objectives**:
- Verify virtual environment is properly activated
- Verify all dependencies install correctly without conflicts
- Validate config.yaml template structure
- Ensure Python version compatibility (3.11+)
- Ensure project structure is complete

**Validation Commands**:
```bash
# Verify virtual environment
which python  # Should show venv/bin/python path
python --version  # Should show Python 3.11+

# Install and test dependencies
pip install -r requirements.txt
python -c "import twikit, pandas, pyarrow, yaml, dateutil, aiofiles, psutil; print('All dependencies imported successfully')"

# Verify no dependency conflicts
pip check
```

**Context for Implementation**:
- Create isolated Python virtual environment to avoid system conflicts
- Use Python 3.11+ for optimal async performance and type hints
- Use semantic versioning for dependencies with tested version ranges
- Include comprehensive .gitignore for Python projects and tool-specific files
- Store Python version in .python-version for consistency across environments

## Phase 2: Configuration Management and Authentication

### Overview
Implement configuration loading from YAML and X.com authentication with session persistence.

### Changes Required:

#### 1. Configuration Module
**File**: `config_manager.py`

```python
class ConfigManager:
    def __init__(self, config_path: str)
    def load_config(self) -> dict
    def validate_auth_config(self) -> bool
    def get_rate_limit_settings(self) -> dict
    def get_output_settings(self) -> dict
```

**Function Responsibilities**:
- Load and parse YAML configuration file
- Validate required authentication fields are present
- Provide typed access to configuration sections
- Handle missing or malformed config files gracefully

#### 2. Authentication Module
**File**: `auth_manager.py`

```python
class AuthManager:
    def __init__(self, config: dict)
    async def authenticate(self) -> Client
    async def save_session(self, client: Client) -> None
    async def load_existing_session(self) -> Client | None
    def is_authenticated(self, client: Client) -> bool
```

**Function Responsibilities**:
- Handle twikit Client initialization and login
- Implement session cookie persistence to avoid repeated logins
- Manage authentication failures and retry logic
- Validate existing sessions before use

**Testing Requirements**:
```python
def test_config_loading()
def test_config_validation()
def test_auth_initialization()
def test_session_persistence()
```

**Test Objectives**:
- Verify YAML parsing handles various config formats
- Validate authentication credential validation
- Test session saving/loading functionality
- Ensure error handling for invalid credentials

**Validation Commands**:
```bash
python -c "from config_manager import ConfigManager; cm = ConfigManager('config.yaml.template'); print('Config manager works')"
python -m pytest test_config.py -v
```

**Context for Implementation**:
- Use PyYAML's safe_load for security
- Store session cookies in local .twikit_cookies file
- Follow twikit documentation patterns for client initialization

## Phase 3: Tweet Data Extraction Engine

### Overview
Core tweet retrieval functionality with pagination, date filtering, and comprehensive metadata extraction.

### Changes Required:

#### 1. Tweet Extractor Module
**File**: `tweet_extractor.py`

```python
class TweetExtractor:
    def __init__(self, client: Client, rate_limiter: RateLimiter)
    async def extract_user_tweets(self, username: str, duration: timedelta) -> AsyncGenerator[dict, None]
    async def get_user_by_username(self, username: str) -> User
    async def fetch_tweet_batch(self, user_id: str, cursor: str = None) -> Result[Tweet]
    def convert_tweet_to_dict(self, tweet: Tweet) -> dict
    def is_within_duration(self, tweet_date: datetime, cutoff_date: datetime) -> bool
    async def handle_twikit_exceptions(self, error: Exception) -> bool
    async def extract_with_pagination(self, user: User, cutoff_date: datetime) -> AsyncGenerator[Tweet, None]
```

**Function Responsibilities**:
- Convert username to user_id via twikit API
- Implement paginated tweet retrieval with date-based stopping
- Extract comprehensive tweet metadata following twikit Tweet class structure
- Handle tweet date parsing and duration comparison
- Convert Tweet objects to dictionary format for parquet storage
- Handle twikit-specific exceptions (TooManyRequests, Unauthorized, Forbidden)
- Stream tweets using async generator to minimize memory usage
- Proper twikit Result object pagination with cursor handling

#### 2. Rate Limiter Module
**File**: `rate_limiter.py`

```python
class RateLimiter:
    def __init__(self, base_delay: float, max_retries: int, backoff_multiplier: float)
    async def wait_before_request(self) -> None
    async def handle_rate_limit_error(self, attempt: int) -> bool
    def calculate_backoff_delay(self, attempt: int) -> float
    async def handle_twikit_rate_limits(self, error: Exception) -> bool
```

**Function Responsibilities**:
- Implement configurable delays between API requests
- Handle rate limit exceptions with exponential backoff
- Track request timing and adapt delay strategies
- Provide retry logic for failed requests
- Handle twikit-specific TooManyRequests exceptions
- Implement intelligent backoff based on twikit response headers

#### 3. Date Parser Module
**File**: `date_parser.py`

```python
class DateParser:
    @staticmethod
    def parse_duration(duration_str: str) -> timedelta
    @staticmethod
    def calculate_cutoff_date(duration: timedelta) -> datetime
    @staticmethod
    def parse_tweet_date(date_str: str) -> datetime
```

**Function Responsibilities**:
- Parse natural language duration strings using dateutil
- Calculate cutoff dates for tweet filtering
- Handle various Twitter date formats consistently
- Provide timezone-aware datetime objects

**Testing Requirements**:
```python
def test_user_lookup()
def test_tweet_extraction()
def test_date_filtering()
def test_rate_limiting()
def test_duration_parsing()
```

**Test Objectives**:
- Verify username to user_id conversion
- Test pagination handling and stopping conditions
- Validate comprehensive tweet metadata extraction
- Ensure rate limiting and backoff work correctly
- Test various duration string formats

**Validation Commands**:
```bash
python -m pytest test_extraction.py -v
python -c "from tweet_extractor import TweetExtractor; print('Extractor imports successfully')"
```

**Context for Implementation**:
- Follow twikit's async patterns for all API calls
- Use dateutil.parser for flexible date string parsing
- Extract all available Tweet class properties to dictionary
- Implement graceful handling of deleted or protected tweets

**CRITICAL IMPLEMENTATION NOTES**:
1. **Verify twikit Tweet date attribute**: The exact attribute name for tweet creation date must be confirmed during implementation (could be `created_at`, `created_at_datetime`, or similar)
2. **Test PyArrow schema compatibility**: All schema fields must be validated against actual twikit Tweet objects
3. **Rate limiting values**: The sleep times (300s, 900s) are estimates and should be adjusted based on actual X.com rate limit responses
4. **Memory monitoring**: Implement memory usage checks to prevent system overload during large extractions

**Twikit-Specific Implementation Patterns**:
```python
# Proper twikit pagination pattern:
async def extract_with_pagination(self, user: User, cutoff_date: datetime):
    tweets = await self.client.get_user_tweets(user.id, 'Tweets', count=40)
    for tweet in tweets:
        if tweet.created_at_datetime < cutoff_date:
            return  # Stop when reaching cutoff
        yield tweet
    
    # Continue pagination
    while hasattr(tweets, 'next_cursor') and tweets.next_cursor:
        await self.rate_limiter.wait_before_request()
        tweets = await tweets.next()
        for tweet in tweets:
            # NOTE: Verify actual twikit Tweet date attribute during implementation
            tweet_date = getattr(tweet, 'created_at_datetime', None) or getattr(tweet, 'created_at', None)
            if tweet_date and tweet_date < cutoff_date:
                return
            yield tweet

# Enhanced twikit exception handling with specific rate limiting:
async def handle_twikit_exceptions(self, error: Exception) -> bool:
    from twikit.errors import TooManyRequests, Unauthorized, Forbidden
    if isinstance(error, TooManyRequests):
        # Handle specific rate limit reset times if available
        if hasattr(error, 'rate_limit_reset') and error.rate_limit_reset:
            reset_time = int(error.rate_limit_reset)
            current_time = int(time.time())
            sleep_time = reset_time - current_time + 60  # Extra buffer
            await asyncio.sleep(max(sleep_time, 300))  # Minimum 5 min wait
        else:
            await asyncio.sleep(900)  # Default 15 min wait for rate limits
        return True
    elif isinstance(error, (Unauthorized, Forbidden)):
        # Handle private/protected accounts
        logging.warning(f"Account access denied: {error}")
        return False
    else:
        raise error
```

## Phase 4: Streaming Data Processing and Checkpoint Management

### Overview
Implement memory-efficient streaming parquet writing with checkpoint/resume functionality for large extractions.

### Changes Required:

#### 1. Data Processor Module
**File**: `data_processor.py`

```python
class StreamingDataProcessor:
    def __init__(self, output_settings: dict, output_file: str)
    async def process_tweet_stream(self, tweet_stream: AsyncGenerator[dict, None]) -> None
    def define_parquet_schema(self) -> pa.Schema
    async def write_batch_to_parquet(self, tweets: List[dict]) -> None
    def validate_data_completeness(self, tweets: List[dict]) -> bool
    def initialize_parquet_writer(self) -> None
    def finalize_parquet_writer(self) -> None

class CheckpointManager:
    def __init__(self, output_file: str)
    async def save_checkpoint(self, last_tweet_id: str, count: int) -> None
    async def load_checkpoint(self) -> dict | None
    async def get_resume_point(self) -> str | None
    async def cleanup_checkpoint(self) -> None
```

**StreamingDataProcessor Responsibilities**:
- Process tweet stream in configurable batches to minimize memory usage
- Define consistent schema for parquet output with proper data types
- Use PyArrow ParquetWriter for proper incremental writing (NOT append mode)
- Handle data type conversions and null value management
- Validate data integrity before each batch write
- Initialize and manage ParquetWriter lifecycle properly

**CheckpointManager Responsibilities**:
- Save extraction progress to separate checkpoint JSON files
- Enable resume functionality from checkpoint files (not parquet files)
- Track last extracted tweet ID and count for resume capability
- Handle corrupted or incomplete checkpoint files gracefully
- Clean up checkpoint files on successful completion

#### 2. Enhanced Tweet Data Schema
**PyArrow Schema Definition** (proper typing for parquet):
```python
def define_parquet_schema(self) -> pa.Schema:
    return pa.schema([
        # Core tweet data
        pa.field('id', pa.string()),
        pa.field('text', pa.string()),
        pa.field('full_text', pa.string()),
        pa.field('created_at', pa.timestamp('ns')),
        pa.field('lang', pa.string()),
        
        # User information  
        pa.field('user_id', pa.string()),
        pa.field('user_screen_name', pa.string()),
        pa.field('user_name', pa.string()),
        
        # Engagement metrics
        pa.field('favorite_count', pa.int64()),
        pa.field('favorited', pa.bool_()),
        pa.field('retweet_count', pa.int64()),
        pa.field('reply_count', pa.int64()),
        pa.field('quote_count', pa.int64()),
        pa.field('view_count', pa.int64()),
        pa.field('bookmark_count', pa.int64()),
        pa.field('bookmarked', pa.bool_()),
        
        # Content metadata
        pa.field('hashtags', pa.list_(pa.string())),
        pa.field('urls', pa.list_(pa.string())),
        pa.field('media', pa.string()),  # JSON string representation
        pa.field('has_card', pa.bool_()),
        pa.field('is_quote_status', pa.bool_()),
        pa.field('possibly_sensitive', pa.bool_()),
        pa.field('is_translatable', pa.bool_()),
        
        # Thread/reply information
        pa.field('in_reply_to', pa.string()),
        pa.field('conversation_id', pa.string()),
        
        # Location data (if available)
        pa.field('place', pa.string()),  # JSON string representation
        
        # Content source
        pa.field('source', pa.string()),
    ])
```

**Note**: 
- Uses proper PyArrow types for consistent parquet output
- Complex objects (media, place) stored as JSON strings
- Only fields with available data from twikit will be populated
- Schema must be verified against actual twikit Tweet attributes during implementation

**Testing Requirements**:
```python
def test_streaming_batch_processing()
def test_parquet_append_functionality()
def test_checkpoint_resume_logic()
def test_memory_efficiency()
def test_schema_validation()
```

**Test Objectives**:
- Verify streaming batch processing doesn't exceed memory limits
- Validate parquet append functionality works correctly
- Test checkpoint/resume logic with existing files
- Ensure consistent schema across batches
- Validate memory efficiency with large datasets

**Validation Commands**:
```bash
python -c "import pandas as pd; import pyarrow as pa; print('Data libraries working')"
python -m pytest test_data_processing.py -v
```

**Context for Implementation**:
- Use pyarrow for efficient parquet writing with append mode
- Implement schema validation to catch data inconsistencies
- Handle nested data structures (hashtags, URLs, media) appropriately
- Include metadata in parquet files for traceability

**Memory-Efficient Processing Workflow**:
```python
# Proper PyArrow streaming writer pattern:
class StreamingDataProcessor:
    def __init__(self, output_file: str, batch_size: int = 50):
        self.output_file = output_file
        self.batch_size = batch_size
        self.parquet_writer = None
        self.first_write = True
        self.schema = self.define_parquet_schema()
    
    async def process_tweet_stream(self, tweet_stream: AsyncGenerator[dict, None]):
        batch = []
        async for tweet_dict in tweet_stream:
            batch.append(tweet_dict)
            
            if len(batch) >= self.batch_size:
                await self.write_batch_to_parquet(batch)
                batch.clear()  # Free memory immediately
                
        # Write final batch
        if batch:
            await self.write_batch_to_parquet(batch)
        
        self.finalize_parquet_writer()
    
    async def write_batch_to_parquet(self, tweets: List[dict]):
        table = pa.Table.from_pandas(pd.DataFrame(tweets), schema=self.schema)
        if self.first_write:
            self.parquet_writer = pq.ParquetWriter(self.output_file, table.schema)
            self.first_write = False
        self.parquet_writer.write_table(table)

# Checkpoint-based resume (not from parquet):
class CheckpointManager:
    async def save_checkpoint(self, last_tweet_id: str, count: int):
        checkpoint = {
            "last_tweet_id": last_tweet_id,
            "count": count,
            "timestamp": datetime.now().isoformat()
        }
        checkpoint_file = f"{self.output_file}.checkpoint"
        async with aiofiles.open(checkpoint_file, 'w') as f:
            await f.write(json.dumps(checkpoint))
    
    async def load_checkpoint(self) -> dict | None:
        checkpoint_file = f"{self.output_file}.checkpoint"
        try:
            async with aiofiles.open(checkpoint_file, 'r') as f:
                content = await f.read()
                return json.loads(content)
        except (FileNotFoundError, json.JSONDecodeError):
            return None
```

## Phase 5: Command Line Interface and Main Application

### Overview
Complete CLI application that ties all components together with proper error handling and user feedback.

### Changes Required:

#### 1. Main Application
**File**: `pull_tweets.py`

```python
class TweetPuller:
    def __init__(self, config_path: str)
    async def run(self, username: str, duration: str, output_file: str) -> None
    async def initialize_client(self) -> Client
    def setup_logging(self) -> None
    def validate_inputs(self, username: str, duration: str, output_file: str) -> bool
    async def check_resume_capability(self, output_file: str) -> str | None

def parse_arguments() -> argparse.Namespace
async def main() -> None
```

**Function Responsibilities**:
- Parse command line arguments using argparse
- Initialize all components (config, auth, extractor, processor)
- Orchestrate the complete tweet extraction workflow with streaming processing
- Check for existing output file and enable resume if requested
- Provide user feedback and progress updates with tweet counts
- Handle and report errors appropriately with graceful shutdown

#### 2. CLI Argument Structure
```bash
python pull_tweets.py <username> --output-file <filename> [options]

Required Arguments:
  username              Twitter username (with or without @)
  --output-file, -o     Output parquet filename (e.g., tweets.parquet)
  
Optional Arguments:
  --duration, -d        Time period to go back (e.g., "7 days", "1 month", default: "30 days")
  --config CONFIG       Path to config.yaml file (default: ./config.yaml)
  --resume              Resume from existing output file if present
  --batch-size SIZE     Number of tweets to process per batch (default: 50)
  --verbose, -v         Enable verbose logging
```

#### 3. Error Handling and Logging
**File**: `error_handler.py`

```python
class ErrorHandler:
    @staticmethod
    def handle_authentication_error(error: Exception) -> None
    @staticmethod
    def handle_rate_limit_error(error: Exception) -> None
    @staticmethod
    def handle_user_not_found_error(error: Exception) -> None
    @staticmethod
    def handle_network_error(error: Exception) -> None
```

**Function Responsibilities**:
- Provide user-friendly error messages for common failures
- Log technical details while showing simple messages to users
- Implement graceful application shutdown on critical errors
- Handle partial data recovery scenarios

**Testing Requirements**:
```python
def test_argument_parsing()
def test_main_workflow()
def test_error_handling()
def test_output_generation()
```

**Test Objectives**:
- Verify CLI argument parsing handles various input formats
- Test complete end-to-end workflow with mock data
- Validate error handling for common failure scenarios
- Ensure proper output file generation and naming

**Validation Commands**:
```bash
python pull_tweets.py --help
python pull_tweets.py testuser --output-file test_tweets.parquet --duration "1 day" --config config.yaml.template
python pull_tweets.py testuser --output-file test_tweets.parquet --resume --verbose
```

**Context for Implementation**:
- Use argparse for robust CLI argument handling
- Implement logging with configurable verbosity levels
- Follow Python async best practices for main application flow
- Provide clear progress indicators for long-running operations

## Phase 6: Documentation and Final Integration

### Overview
Complete project documentation, usage examples, and final testing to ensure production readiness.

### Changes Required:

#### 1. Documentation Files
**File**: `README.md`

**Documentation Content**:
- Installation and setup instructions
- Configuration file setup guide
- Usage examples with various duration formats
- Troubleshooting common issues
- Output file structure explanation

#### 2. Example Usage Scripts
**File**: `examples/`

**Example Scripts**:
- Basic usage example
- Configuration file templates
- Sample output analysis notebook

#### 3. Integration Testing
**File**: `test_integration.py`

```python
def test_full_workflow_integration()
def test_config_file_variations()
def test_error_scenarios()
def test_output_validation()
```

**Test Objectives**:
- Verify complete end-to-end functionality
- Test various configuration combinations
- Validate output file format and content
- Ensure error handling works in real scenarios

**Testing Requirements**:
```python
def test_end_to_end_workflow()
def test_documentation_examples()
def test_error_recovery()
```

**Validation Commands**:
```bash
python -m pytest test_integration.py -v
python pull_tweets.py example_user --output-file example_tweets.parquet --duration "1 hour"
ls -la example_tweets.parquet
python -c "import pandas as pd; df = pd.read_parquet('example_tweets.parquet'); print(f'Extracted {len(df)} tweets')"
python pull_tweets.py example_user --output-file example_tweets.parquet --resume --verbose
```

**Context for Implementation**:
- Include comprehensive setup instructions
- Provide troubleshooting guide for common authentication issues
- Document all configuration options with examples
- Create sample data analysis examples using output files