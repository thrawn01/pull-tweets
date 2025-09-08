#!/usr/bin/env python3
"""
Extract tweet bodies from parquet file and format as markdown.

Usage:
    python extract_to_markdown.py input.parquet output.md
    
Format:
    ## YYYY-MM-DD HH:MM:SS
    Tweet body text here
    
    ## YYYY-MM-DD HH:MM:SS  
    Another tweet body here
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime


def extract_tweets_to_markdown(parquet_file: str, output_file: str, exclude_retweets: bool = True) -> None:
    """Extract tweets from parquet and format as markdown."""
    try:
        # Load parquet file
        df = pd.read_parquet(parquet_file)
        print(f"Loaded {len(df)} tweets from {parquet_file}")
        
        # Filter out retweets if requested
        if exclude_retweets:
            original_count = len(df)
            df = df[~df['text'].str.startswith('RT @', na=False)]
            print(f"Filtered out {original_count - len(df)} retweets, {len(df)} original tweets remaining")
        
        # Sort by creation date (newest first)
        df = df.sort_values('created_at', ascending=False)
        
        # Extract and format tweets
        markdown_lines = []
        
        for _, tweet in df.iterrows():
            # Format the date
            if pd.isna(tweet['created_at']):
                date_str = "Unknown Date"
            else:
                # Handle different datetime formats
                if isinstance(tweet['created_at'], str):
                    try:
                        dt = pd.to_datetime(tweet['created_at'])
                        date_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        date_str = str(tweet['created_at'])
                else:
                    date_str = tweet['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            
            # Get tweet text (prefer full_text over text)
            text = tweet.get('full_text', tweet.get('text', ''))
            if pd.isna(text):
                text = '[No text content]'
            
            # Clean up the text (remove extra whitespace, preserve line breaks)
            text = str(text).strip()
            
            # Add to markdown format
            markdown_lines.append(f"## {date_str}")
            markdown_lines.append(f"{text}")
            markdown_lines.append("")  # Empty line between tweets
        
        # Write to output file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(markdown_lines))
        
        print(f"Successfully extracted {len(df)} tweets to {output_file}")
        
    except FileNotFoundError:
        print(f"Error: Parquet file '{parquet_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error processing file: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Extract tweet bodies from parquet file to markdown format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic usage
    python extract_to_markdown.py tweets.parquet tweets.md
    
    # Include retweets  
    python extract_to_markdown.py tweets.parquet tweets.md --include-retweets
        """
    )
    
    parser.add_argument(
        'input_file',
        help='Input parquet file path'
    )
    
    parser.add_argument(
        'output_file', 
        help='Output markdown file path'
    )
    
    parser.add_argument(
        '--include-retweets',
        action='store_true',
        help='Include retweets (RT @username) in output (default: exclude)'
    )
    
    args = parser.parse_args()
    
    # Validate input file exists
    if not Path(args.input_file).exists():
        print(f"Error: Input file '{args.input_file}' does not exist")
        sys.exit(1)
    
    # Extract tweets
    extract_tweets_to_markdown(
        parquet_file=args.input_file,
        output_file=args.output_file,
        exclude_retweets=not args.include_retweets
    )


if __name__ == '__main__':
    main()