# import spacy
from typing import List, Set

# # Load a spaCy model. You might need to download it first: python -m spacy download en_core_web_sm
# try:
#     nlp = spacy.load("en_core_web_sm")
# except OSError:
#     print("Downloading spaCy model 'en_core_web_sm'...")
#     # spacy.cli.download("en_core_web_sm")
#     nlp = spacy.load("en_core_web_sm")

def extract_keywords(text: str) -> List[str]:
    """
    Extracts keywords from a given text using spaCy.
    Keywords are identified as nouns or proper nouns.
    """
    # if not text:
    #     return []

    # doc = nlp(text)
    # keywords = set()
    # for token in doc:
    #     # Consider nouns and proper nouns as keywords
    #     if token.pos_ in ["NOUN", "PROPN"]:
    #         keywords.add(token.lemma_.lower()) # Use lemma for normalization
    
    # return sorted(list(keywords))
    return []


def normalize_keywords(keywords: List[str]) -> List[str]:
    """
    Normalizes a list of keywords by lowercasing and removing duplicates.
    """
    # return sorted(list(set(k.lower() for k in keywords)))
    return []

# if __name__ == "__main__":
#     test_text1 = "This is a test sentence about Python programming and machine learning."
#     test_text2 = "Errors occurred during the database migration process, specifically with PostgreSQL."
#     test_text3 = ""

#     print(f"Keywords for '{test_text1}': {extract_keywords(test_text1)}")
#     print(f"Keywords for '{test_text2}': {extract_keywords(test_text2)}")
#     print(f"Keywords for '{test_text3}': {extract_keywords(test_text3)}")

#     keywords_to_normalize = ["Python", "python", "Database", "database", "ML"]
#     print(f"Normalized keywords for {keywords_to_normalize}: {normalize_keywords(keywords_to_normalize)}")
