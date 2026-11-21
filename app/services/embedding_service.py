"""Semantic Embedding Service for transaction classification and vector similarity.

Uses SentenceTransformer (all-MiniLM-L6-v2) to generate 384-dimensional dense vectors
and matches transaction merchant strings against semantic anchor exemplars via cosine similarity.
"""
import logging
import re
from functools import lru_cache
import numpy as np
from sentence_transformers import SentenceTransformer

log = logging.getLogger(__name__)

# Category anchor exemplars (concise representative phrases for high-fidelity vector matching)
CATEGORY_ANCHORS: dict[str, dict] = {
    "Food": {
        "direction": "expense",
        "anchors": [
            "restaurant and cafe food",
            "zomato online food order",
            "swiggy meal delivery",
            "fast food burger pizza fries",
            "coffee shop cafe bakery snacks",
            "dining out bar pub eatery",
            "dominos kfc mcdonalds starbucks subway"
        ]
    },
    "Groceries": {
        "direction": "expense",
        "anchors": [
            "supermarket daily provisions",
            "grocery vegetables fruits store",
            "blinkit zepto quick delivery",
            "bigbasket instamart grocery items",
            "milk bread eggs dairy items",
            "organic food provisions general merchant",
            "dmart walmart carrefour hypermarket"
        ]
    },
    "Transport": {
        "direction": "expense",
        "anchors": [
            "gas station petrol diesel fuel",
            "shell indian oil bharat petroleum fuel pump",
            "cab taxi auto rideshare fare",
            "uber ola rapido ride payment",
            "metro train bus transit pass",
            "highway toll tax FASTag recharge",
            "parking charges garage parking"
        ]
    },
    "Utilities": {
        "direction": "expense",
        "anchors": [
            "electricity power bill payment",
            "water utility bill payment",
            "broadband wifi internet service provider",
            "mobile postpaid phone recharge bill",
            "cooking gas lpg cylinder bill",
            "cable dth dish tv recharge bill"
        ]
    },
    "Rent & Housing": {
        "direction": "expense",
        "anchors": [
            "monthly apartment house rent payment",
            "landlord rent transfer flat lease",
            "housing society maintenance maintenance fee",
            "property municipal tax building payment",
            "home mortgage loan monthly payment"
        ]
    },
    "Entertainment": {
        "direction": "expense",
        "anchors": [
            "movie cinema theater tickets bookmyshow",
            "concert live event show tickets",
            "video games steam playstation xbox purchase",
            "amusement theme park entry ticket",
            "sports event match ticket"
        ]
    },
    "Shopping": {
        "direction": "expense",
        "anchors": [
            "clothing apparel fashion store",
            "amazon flipkart online shopping order",
            "shoes footwear store retail",
            "electronics computer phone gadget store",
            "zara h&m myntra ajio clothing purchase",
            "shopping mall retail merchandise store"
        ]
    },
    "Health": {
        "direction": "expense",
        "anchors": [
            "pharmacy chemist medicines medical store",
            "apollo pharmacy tata 1mg pharmeasy medicines",
            "doctor hospital clinic consultation fee",
            "dental checkup eye clinic treatment",
            "diagnostic lab blood medical test",
            "gym fitness membership cult fit workout"
        ]
    },
    "Education": {
        "direction": "expense",
        "anchors": [
            "university college school tuition fee",
            "online course training udemy coursera",
            "educational books study materials stationery",
            "examination fee coaching classes institute",
            "academic certification student fee"
        ]
    },
    "Travel": {
        "direction": "expense",
        "anchors": [
            "flight airline air ticket booking",
            "hotel room resort stay reservation",
            "railway train irctc ticket booking",
            "makemytrip agoda booking.com airbnb travel",
            "holiday tour vacation travel agency package"
        ]
    },
    "Subscriptions": {
        "direction": "expense",
        "anchors": [
            "netflix recurring streaming subscription",
            "spotify music monthly subscription",
            "youtube premium subscription renewal",
            "apple icloud google one cloud storage",
            "chatgpt openai github copilot subscription",
            "amazon prime membership annual renewal"
        ]
    },
    "Fees & Charges": {
        "direction": "expense",
        "anchors": [
            "bank service charge processing fee",
            "atm withdrawal fee penalty charge",
            "credit card late payment fee finance charge",
            "account maintenance fee overdraft charge",
            "foreign transaction currency conversion fee"
        ]
    },
    "Salary": {
        "direction": "income",
        "anchors": [
            "monthly company employee salary credit",
            "payroll direct deposit compensation wages",
            "stipend internship monthly payout",
            "annual performance bonus employer payment"
        ]
    },
    "Other Income": {
        "direction": "income",
        "anchors": [
            "cashback reward credited to account",
            "refund return credited to account",
            "bank savings interest credited",
            "stock dividend payout credited",
            "reimbursement expense claim approved"
        ]
    },
}


def clean_merchant_text(text: str) -> str:
    """Cleans noisy bank transaction strings (removes punctuation, noise codes, numbers)."""
    # Replace non-alphanumeric with spaces, keep basic text
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    # Remove stand-alone numbers (like transaction IDs, branch numbers)
    cleaned = re.sub(r"\b\d+\b", " ", cleaned)
    return " ".join(cleaned.split()).lower()


class EmbeddingClassifier:
    """Singleton service for semantic vector embedding and cosine similarity classification."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingClassifier, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        log.info("Initializing SentenceTransformer embedding engine (all-MiniLM-L6-v2)...")
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        
        # Build category index with anchor vectors
        self.categories = list(CATEGORY_ANCHORS.keys())
        self.category_data = {}
        
        for cat_name, data in CATEGORY_ANCHORS.items():
            anchors = data["anchors"]
            vectors = self.model.encode(anchors, convert_to_numpy=True, normalize_embeddings=True)
            self.category_data[cat_name] = {
                "direction": data["direction"],
                "vectors": vectors,  # shape: (M, 384)
            }
            
        log.info("Semantic vector index compiled across %d categories with anchor exemplars.", len(self.categories))

    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text string into a 384-D normalized vector."""
        cleaned = clean_merchant_text(text)
        return self.model.encode(cleaned if cleaned else text, convert_to_numpy=True, normalize_embeddings=True)

    def classify(self, text: str, direction: str = "expense", threshold: float = 0.35) -> tuple[str, float] | None:
        """
        Classifies transaction text into the best matching category using maximum cosine similarity
        against category anchor exemplars.
        Returns (category_name, confidence_score) or None if below threshold.
        """
        if not text or not text.strip():
            return None
            
        query_vec = self.embed_text(text)  # shape: (384,)
        best_cat = None
        best_score = -1.0
        
        for cat_name, cat_info in self.category_data.items():
            if cat_info["direction"] != direction:
                continue
                
            # Cosine similarity against each anchor in this category
            sims = np.dot(cat_info["vectors"], query_vec)
            max_sim = float(np.max(sims))
            
            if max_sim > best_score:
                best_score = max_sim
                best_cat = cat_name
                
        if best_cat and best_score >= threshold:
            return best_cat, round(best_score, 3)
            
        return None


# Global singleton instance accessor
@lru_cache(maxsize=1)
def get_embedding_classifier() -> EmbeddingClassifier:
    return EmbeddingClassifier()
