import re
from collections import Counter

# Expanded stop words: English function words + common news filler
STOP_WORDS = {
    # Articles, prepositions, conjunctions
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can", "need",
    "not", "no", "nor", "so", "yet", "both", "either", "neither",
    # Pronouns
    "this", "that", "these", "those", "it", "its", "he", "she", "they",
    "we", "you", "i", "me", "him", "her", "us", "them", "my", "your",
    "his", "our", "their", "what", "which", "who", "whom", "where",
    "when", "why", "how", "whose",
    # Common verbs (non-meaningful alone)
    "said", "says", "say", "told", "tell", "get", "got", "gets",
    "make", "made", "makes", "take", "took", "taken", "takes",
    "come", "came", "comes", "give", "gave", "gives", "given",
    "go", "went", "gone", "goes", "put", "set", "run", "ran",
    "see", "saw", "seen", "know", "knew", "known", "think",
    "use", "used", "uses", "using", "keep", "kept", "let",
    "begin", "began", "show", "shown", "shows", "showed",
    "call", "called", "calls", "try", "tried", "want", "wanted",
    "look", "looked", "add", "added", "adds", "include", "included",
    "includes", "including", "become", "became", "bring", "brought",
    "hold", "held", "move", "moved", "pay", "paid", "meet", "met",
    "play", "lead", "led", "stand", "lose", "lost", "turn", "turned",
    "leave", "left", "reach", "reached", "remain", "remained",
    # Adverbs and fillers
    "also", "just", "still", "even", "already", "yet", "too", "very",
    "well", "back", "then", "now", "here", "there", "only", "again",
    "further", "once", "much", "more", "most", "less", "least",
    "other", "another", "such", "own", "same", "able", "about",
    "above", "after", "before", "between", "under", "over", "into",
    "through", "during", "up", "out", "off", "down", "away",
    "around", "along", "across", "against", "among", "within",
    "without", "toward", "towards", "upon",
    # Numbers / time
    "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "hundred", "thousand", "million", "billion",
    "first", "second", "third", "last", "next", "per", "cent",
    "percent", "year", "years", "month", "months", "week", "weeks",
    "day", "days", "time", "times", "quarter",
    # Generic news filler
    "new", "many", "some", "few", "all", "each", "every", "any",
    "part", "way", "like", "people", "thing", "things",
    "according", "since", "while", "however", "although", "though",
    "because", "therefore", "meanwhile", "overall", "based",
    "noted", "stated", "reported", "announced", "expected",
    "continue", "continued", "continues", "continuing",
    "number", "total", "level", "levels", "rate", "rates",
    "area", "areas", "end", "high", "low", "large", "small",
    "long", "good", "best", "great", "major", "general",
    "increase", "increased", "increases", "rise", "rose", "grew",
    "growth", "growing", "grown", "change", "changed", "changes",
    "develop", "developed", "development", "developments",
    "plan", "plans", "planned", "planning",
    "work", "working", "works", "worked",
    "country", "countries", "state", "states",
    "government", "governments", "minister", "president",
    "official", "officials", "authority", "authorities",
    "public", "national", "international", "local", "global",
    "world", "region", "regional", "city",
    "company", "companies", "business", "businesses",
    "market", "markets", "sector", "sectors",
    "service", "services", "system", "systems",
    "group", "groups", "member", "members",
    "report", "reports", "data", "information",
    "issue", "issues", "case", "cases",
    "process", "program", "project", "projects",
    "result", "results", "order", "support",
    "provide", "provided", "provides",
    "need", "needs", "needed",
    "help", "helped", "point",
    "going", "really",
}

# Words too vague to be useful alone but fine in bigrams
UNIGRAM_EXTRA_STOP = {
    "policy", "economic", "economy", "trade", "investment",
    "financial", "foreign", "domestic", "billion", "million",
    "current", "recent", "significant", "important", "potential",
    "positive", "negative", "strong", "higher", "lower",
}


def _tokenize(text: str) -> list[str]:
    """Lowercase and extract alphabetic words of 3+ chars."""
    return re.findall(r"[a-zA-Z]{3,}", text.lower())


def _is_meaningful_unigram(w: str) -> bool:
    return w not in STOP_WORDS and w not in UNIGRAM_EXTRA_STOP and len(w) >= 4


def _is_meaningful_bigram(a: str, b: str) -> bool:
    return a not in STOP_WORDS and b not in STOP_WORDS and len(a) >= 3 and len(b) >= 3


def compute_word_frequency(
    texts: list[str], top_n: int = 100
) -> list[tuple[str, int]]:
    unigram_counter: Counter[str] = Counter()
    bigram_counter: Counter[str] = Counter()

    for text in texts:
        words = _tokenize(text)

        # Unigrams
        unigram_counter.update(w for w in words if _is_meaningful_unigram(w))

        # Bigrams
        for i in range(len(words) - 1):
            a, b = words[i], words[i + 1]
            if _is_meaningful_bigram(a, b):
                bigram_counter.update([f"{a} {b}"])

    # Deduplicate: if a bigram is frequent, suppress its component unigrams
    # to avoid "palm" + "oil" + "palm oil" cluttering the cloud
    top_bigrams = bigram_counter.most_common(top_n * 2)
    suppressed: set[str] = set()
    for phrase, cnt in top_bigrams:
        if cnt >= 3:
            parts = phrase.split()
            suppressed.update(parts)

    # Build combined list: bigrams weighted x1.5 to surface them
    combined: Counter[str] = Counter()
    for word, cnt in unigram_counter.items():
        if word not in suppressed:
            combined[word] = cnt
    for phrase, cnt in bigram_counter.items():
        if cnt >= 2:  # Only bigrams appearing 2+ times
            combined[phrase] = int(cnt * 1.5)

    return combined.most_common(top_n)
