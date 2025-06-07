# utils/helpers.py
import re
import hashlib
from datetime import datetime
from typing import List, Tuple, Dict, Optional

def split_trend_blocks(raw_md: str) -> Tuple[List[str], List[str]]:
    """Split markdown into trend titles and blocks"""
    matches = list(re.finditer(r"(?mi)^.*?trend title:\s*(.+)$", raw_md))
    titles, blocks = [], []
    
    for i, m in enumerate(matches):
        titles.append(m.group(1).strip())
        start = m.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(raw_md)
        blocks.append(raw_md[start:end].strip())
    
    return titles, blocks

def extract_confidence_score(block: str) -> float:
    """Extract confidence score from trend block"""
    m = re.search(r"Confidence\s*Score:\s*([0-9.]+)", block, re.IGNORECASE)
    return float(m.group(1)) if m else 0.5

def generate_trend_id(title: str, timestamp: datetime = None) -> str:
    """Generate unique ID for trend"""
    if not timestamp:
        timestamp = datetime.now()
    
    id_string = f"{title}{timestamp.isoformat()}"
    return hashlib.md5(id_string.encode()).hexdigest()[:8]

def format_trend_summary(title: str, block: str, max_length: int = 200) -> str:
    """Format trend summary for display"""
    # Extract description from block
    desc_match = re.search(r"\*\*Description:\*\*\s*(.+?)(?=\*\*|$)", block, re.DOTALL)
    description = desc_match.group(1).strip() if desc_match else block[:max_length]
    
    # Clean up formatting
    description = re.sub(r'\s+', ' ', description)
    
    if len(description) > max_length:
        description = description[:max_length-3] + "..."
    
    return description

def parse_market_impact(block: str) -> Dict[str, str]:
    """Parse market impact section from trend block"""
    impact = {}
    
    # Extract market size
    size_match = re.search(r"\*\*Market Size:\*\*\s*(.+?)(?=\n|$)", block)
    if size_match:
        impact['size'] = size_match.group(1).strip()
    
    # Extract timeline
    timeline_match = re.search(r"\*\*Timeline:\*\*\s*(.+?)(?=\n|$)", block)
    if timeline_match:
        impact['timeline'] = timeline_match.group(1).strip()
    
    # Extract key drivers
    drivers_match = re.search(r"\*\*Key Drivers:\*\*\s*(.+?)(?=\n|$)", block)
    if drivers_match:
        impact['drivers'] = drivers_match.group(1).strip()
    
    return impact

def calculate_trend_priority(confidence: float, impact: str, 
                           timeline: str = None) -> float:
    """Calculate priority score for trend"""
    # Base score from confidence
    priority = confidence
    
    # Adjust for impact
    impact_multiplier = {
        'high': 1.5,
        'medium': 1.0,
        'low': 0.5
    }
    priority *= impact_multiplier.get(impact.lower(), 1.0)
    
    # Adjust for timeline urgency
    if timeline:
        if 'immediate' in timeline.lower() or '1 year' in timeline.lower():
            priority *= 1.2
        elif '5 year' in timeline.lower() or 'long' in timeline.lower():
            priority *= 0.8
    
    return min(priority, 1.0)

def format_currency(amount: float, currency: str = 'USD') -> str:
    """Format currency amounts"""
    symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£'
    }
    
    symbol = symbols.get(currency, currency)
    
    if amount >= 1e9:
        return f"{symbol}{amount/1e9:.1f}B"
    elif amount >= 1e6:
        return f"{symbol}{amount/1e6:.1f}M"
    elif amount >= 1e3:
        return f"{symbol}{amount/1e3:.1f}K"
    else:
        return f"{symbol}{amount:.2f}"

def sanitize_html(text: str) -> str:
    """Basic HTML sanitization"""
    # Remove script tags
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove style tags
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove dangerous attributes
    text = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
    
    return text

def validate_email(email: str) -> bool:
    """Basic email validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def get_time_ago(timestamp: datetime) -> str:
    """Get human-readable time ago string"""
    now = datetime.now()
    delta = now - timestamp
    
    if delta.days > 365:
        return f"{delta.days // 365} year{'s' if delta.days // 365 > 1 else ''} ago"
    elif delta.days > 30:
        return f"{delta.days // 30} month{'s' if delta.days // 30 > 1 else ''} ago"
    elif delta.days > 0:
        return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
    elif delta.seconds > 3600:
        return f"{delta.seconds // 3600} hour{'s' if delta.seconds // 3600 > 1 else ''} ago"
    elif delta.seconds > 60:
        return f"{delta.seconds // 60} minute{'s' if delta.seconds // 60 > 1 else ''} ago"
    else:
        return "just now"

def truncate_text(text: str, max_length: int = 100, 
                 ellipsis: str = "...") -> str:
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    
    # Try to break at word boundary
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    
    if last_space > max_length * 0.8:  # If space is reasonably close to end
        truncated = truncated[:last_space]
    
    return truncated + ellipsis

def extract_keywords(text: str, min_length: int = 3) -> List[str]:
    """Extract potential keywords from text"""
    # Remove common words
    stop_words = {
        'the', 'and', 'for', 'with', 'this', 'that', 'from', 'are', 'was',
        'were', 'been', 'have', 'has', 'had', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'can', 'our', 'your', 'their'
    }
    
    # Extract words
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    
    # Filter
    keywords = []
    for word in words:
        if len(word) >= min_length and word not in stop_words:
            keywords.append(word)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)
    
    return unique_keywords[:20]  # Limit to 20 keywords