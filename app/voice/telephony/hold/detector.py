"""Conservative English transcript heuristics; not an acoustic classifier."""
import re
from .models import HoldDecision, HoldIntent


class HoldDetector:
    def detect(self, text: str) -> HoldDecision:
        text = ' '.join(text.lower().replace('’', "'").split())
        rules = (
            (HoldIntent.NONE, r"\b(?:don't|do not|never|cannot|can't)\s+(?:put|place|keep|ask)\b|\b(?:don't|do not)\s+(?:please\s+)?hold\b", 'negated request'),
            (HoldIntent.ANNOUNCEMENT, r'\b(?:your call is important|all (?:our )?(?:agents|representatives) are busy|next available (?:agent|representative)|remain on the line|estimated wait time|thank you for your patience|please continue to hold|your call will be answered|press\s+\d)\b', 'queue announcement'),
            (HoldIntent.REQUEST, r'\b(?:please hold(?: the line)?|hold (?:on|the line|for (?:a|one) (?:moment|minute|second))|(?:can|could|may) (?:i|we) (?:put|place) you on hold|(?:i will|i\'ll|let me) (?:put|place) you on hold|please wait (?:a|one) (?:moment|minute|second))\b', 'explicit hold request'),
            (HoldIntent.POSSIBLE_REQUEST, r'\b(?:let me (?:check|look|verify)|give me (?:a|one) (?:moment|minute|second)|one moment please)\b', 'ambiguous pause request'),
            (HoldIntent.RESUME, r"\b(?:i(?: have|'ve)? (?:checked|found|reviewed|verified|located) (?:your|the) (?:claim|record|information|details)|i(?: am|'m) back|(?:your|the) claim (?:has been|was|is) (?:approved|denied|processed|paid|pending))\b", 'specific conversational return'),
            (HoldIntent.POSSIBLE_RESUME, r'\b(?:thank you for waiting|thanks for waiting|sorry (?:for|about) the wait|are you still there|hello)\b', 'ambiguous return greeting'),
        )
        for intent, pattern, reason in rules:
            if re.search(pattern, text):
                return HoldDecision(intent, reason)
        return HoldDecision(HoldIntent.NONE, 'no supported hold evidence')
