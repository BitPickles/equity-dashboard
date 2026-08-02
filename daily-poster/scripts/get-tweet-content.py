#!/usr/bin/env python3
"""
Extract tweet content from daily comment file.
MUST call this before posting tweets.
AI is NOT allowed to make up content.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "daily-poster" / "output"
DATA_DIR = PROJECT_ROOT / "indicators" / "data"

def get_tweet_content(date_str=None):
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    result = {
        'success': False,
        'date': date_str,
        'title': '',
        'body': '',
        'tweet_text': '',
        'poster_path': '',
        'error': ''
    }
    
    comment_file = OUTPUT_DIR / f"{date_str}-comment.json"
    if not comment_file.exists():
        result['error'] = f"Comment file not found: {comment_file}"
        return result
    
    try:
        with open(comment_file, 'r', encoding='utf-8') as f:
            comment = json.load(f)
    except Exception as e:
        result['error'] = f"Failed to read comment file: {e}"
        return result
    
    result['title'] = comment.get('title', '')
    result['body'] = comment.get('body', '')
    
    ahr999_file = DATA_DIR / "ahr999.json"
    mvrv_file = DATA_DIR / "mvrv.json"
    
    if not ahr999_file.exists():
        result['error'] = "AHR999 data file not found"
        return result
    
    if not mvrv_file.exists():
        result['error'] = "MVRV data file not found"
        return result
    
    poster_path = OUTPUT_DIR / f"{date_str}.png"
    if not poster_path.exists():
        result['error'] = f"Poster image not found: {poster_path}"
        return result
    
    result['poster_path'] = str(poster_path)
    
    # Extract title (remove ALL emojis)
    title = result['title']
    import re
    # Remove emoji characters (covers most common ranges)
    title = re.sub(r'[\U0001F300-\U0001F9FF\u2600-\u27BF\uFE00-\uFE0F\u200D]+', '', title).strip()
    
    # Build full tweet: title + body + footer
    body = result['body'].strip()
    tweet_text = f"{title}\n\n{body}"
    
    result['tweet_text'] = tweet_text
    result['success'] = True
    
    return result


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    result = get_tweet_content(date_arg)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result['success']:
        sys.exit(1)
