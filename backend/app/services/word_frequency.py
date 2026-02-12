import re
from collections import Counter

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can", "need",
    "dare", "ought", "used", "this", "that", "these", "those", "it", "its",
    "he", "she", "they", "we", "you", "i", "me", "him", "her", "us", "them",
    "my", "your", "his", "our", "their", "what", "which", "who", "whom",
    "where", "when", "why", "how", "all", "each", "every", "both", "few",
    "more", "most", "other", "some", "such", "no", "not", "only", "own",
    "same", "so", "than", "too", "very", "just", "because", "if", "then",
    "also", "about", "up", "out", "into", "over", "after", "before",
    "between", "under", "again", "further", "once", "here", "there",
    "said", "new", "one", "two", "first", "also", "make", "like", "time",
    "just", "know", "take", "people", "year", "them", "way", "well",
    "back", "get", "even", "still", "made", "many", "will", "much",
    "per", "cent", "percent", "according", "since", "while", "however",
    "through", "during", "including", "part", "last", "going",
}


def compute_word_frequency(
    texts: list[str], top_n: int = 100
) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for text in texts:
        words = re.findall(r"[a-zA-Z]{3,}", text.lower())
        counter.update(w for w in words if w not in STOP_WORDS)
    return counter.most_common(top_n)
