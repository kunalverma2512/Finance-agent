"""Unit tests for semantic vector embedding categorization."""
import pytest
from app.services.embedding_service import get_embedding_classifier


def test_semantic_embedding_accuracy():
    classifier = get_embedding_classifier()
    
    benchmark = [
        ("ZOMATO*REST 8941", "expense", "Food"),
        ("SWIGGY DINING GURGAON", "expense", "Food"),
        ("BLINKIT INSTANT GROCERY", "expense", "Groceries"),
        ("APOLLO PHARMACY DEL SEC 14", "expense", "Health"),
        ("SHELL AUTO FUEL IND", "expense", "Transport"),
        ("UBER RIDE MUMBAI", "expense", "Transport"),
        ("NETFLIX SUBSCRIPTION IN", "expense", "Subscriptions"),
        ("AMZN PAY INDIA RETAIL", "expense", "Shopping"),
        ("MONTHLY SALARY ACME CORP", "income", "Salary"),
    ]
    
    passed = 0
    for text, direction, expected in benchmark:
        res = classifier.classify(text, direction=direction)
        assert res is not None, f"Failed to classify: {text}"
        category_name, confidence = res
        assert category_name == expected, f"Mismatch for '{text}': got {category_name}, expected {expected}"
        assert confidence > 0.40, f"Low confidence {confidence} for {text}"
        passed += 1
        
    assert passed == len(benchmark)
