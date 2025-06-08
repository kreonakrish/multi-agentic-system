"""
Query preprocessing utilities for query understanding and expansion.
"""

from typing import List, Dict, Any, Optional
import re
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import wordnet, stopwords
from ..processing.cleaning import DataCleaner

class QueryPreprocessor:
    """Handles query preprocessing and expansion."""
    
    def __init__(
        self,
        expand_synonyms: bool = True,
        max_synonyms: int = 3,
        min_word_length: int = 3
    ):
        """
        Initialize the preprocessor.
        
        Args:
            expand_synonyms: Whether to expand queries with synonyms
            max_synonyms: Maximum number of synonyms per word
            min_word_length: Minimum word length for synonym expansion
        """
        self.expand_synonyms = expand_synonyms
        self.max_synonyms = max_synonyms
        self.min_word_length = min_word_length
        
        # Initialize NLTK resources
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords', quiet=True)
        
        # Initialize stopwords separately from cleaner
        self.stopwords = set(stopwords.words('english'))
        
        # Initialize cleaner without stopwords removal
        self.cleaner = DataCleaner(
            remove_stopwords=False,  # Keep stopwords for query context
            remove_punctuation=True,
            lowercase=True,
            normalize_whitespace=True
        )
    
    def preprocess_query(self, query: str) -> str:
        """
        Clean and normalize query text.
        
        Args:
            query: Query text
            
        Returns:
            Preprocessed query
        """
        return self.cleaner.clean_text(query)
    
    def expand_query(self, query: str) -> List[str]:
        """
        Generate query variations using synonyms.
        
        Args:
            query: Query text
            
        Returns:
            List of expanded queries
        """
        if not self.expand_synonyms:
            return [query]
        
        # Tokenize query
        words = word_tokenize(query)
        expanded_queries = [query]
        
        for i, word in enumerate(words):
            if len(word) >= self.min_word_length:
                # Get synonyms from WordNet
                synonyms = set()
                for syn in wordnet.synsets(word):
                    for lemma in syn.lemmas():
                        if lemma.name() != word:
                            synonyms.add(lemma.name())
                
                # Limit number of synonyms
                synonyms = list(synonyms)[:self.max_synonyms]
                
                # Create new queries with synonyms
                for synonym in synonyms:
                    new_words = words.copy()
                    new_words[i] = synonym
                    expanded_queries.append(' '.join(new_words))
        
        return expanded_queries
    
    def extract_keywords(self, query: str) -> List[str]:
        """
        Extract important keywords from query.
        
        Args:
            query: Query text
            
        Returns:
            List of keywords
        """
        def safe_word_tokenize(text):
            """Tokenize text, downloading required NLTK resources if necessary."""
            import nltk
            try:
                from nltk.tokenize import word_tokenize
                return word_tokenize(text)
            except LookupError:
                # Download required NLTK data
                nltk.download('punkt', quiet=True)
                nltk.download('averaged_perceptron_tagger', quiet=True)
                nltk.download('wordnet', quiet=True)
                from nltk.tokenize import word_tokenize
                return word_tokenize(text)
            except Exception as e:
                # Fallback to simple space-based tokenization if NLTK fails
                return text.split()

        # Simple keyword extraction (could be enhanced with NLP)
        words = safe_word_tokenize(query.lower())
        keywords = []
        
        for word in words:
            if (
                len(word) >= self.min_word_length
                and not word.isnumeric()
                and word not in self.stopwords  # Use our own stopwords set
            ):
                keywords.append(word)
        
        return keywords
    
    def get_query_metadata(self, query: str) -> Dict[str, Any]:
        """
        Generate metadata about the query.
        
        Args:
            query: Query text
            
        Returns:
            Dictionary of metadata
        """
        preprocessed = self.preprocess_query(query)
        keywords = self.extract_keywords(preprocessed)
        
        return {
            "original_query": query,
            "preprocessed_query": preprocessed,
            "keywords": keywords,
            "query_length": len(query),
            "keyword_count": len(keywords)
        }
    
    def validate_query(self, query: str) -> Dict[str, Any]:
        """
        Validate query and provide feedback.
        
        Args:
            query: Query text
            
        Returns:
            Dictionary with validation results
        """
        if not query:
            return {
                "is_valid": False,
                "message": "Query is empty",
                "suggestions": ["Please provide a search query"]
            }
        
        metadata = self.get_query_metadata(query)
        
        if metadata["keyword_count"] == 0:
            return {
                "is_valid": False,
                "message": "No meaningful keywords found",
                "suggestions": ["Add more specific terms to your query"]
            }
        
        if metadata["query_length"] < 3:
            return {
                "is_valid": False,
                "message": "Query too short",
                "suggestions": ["Please provide a longer search query"]
            }
        
        return {
            "is_valid": True,
            "message": "Query is valid",
            "metadata": metadata
        } 