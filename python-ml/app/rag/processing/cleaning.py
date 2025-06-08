"""
Data cleaning utilities for text preprocessing.
"""

import re
from typing import List, Dict, Any, Optional
import pandas as pd
import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

class DataCleaner:
    """Handles text cleaning and normalization."""
    
    def __init__(
        self,
        remove_stopwords: bool = False,
        remove_punctuation: bool = True,
        lowercase: bool = True,
        normalize_whitespace: bool = True
    ):
        """
        Initialize the cleaner.
        
        Args:
            remove_stopwords: Whether to remove stopwords
            remove_punctuation: Whether to remove punctuation
            lowercase: Whether to convert text to lowercase
            normalize_whitespace: Whether to normalize whitespace
        """
        self.remove_stopwords = remove_stopwords
        self.remove_punctuation = remove_punctuation
        self.lowercase = lowercase
        self.normalize_whitespace = normalize_whitespace
        
        if remove_stopwords:
            self.stopwords = set(stopwords.words('english'))
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Convert to string if needed
        if not isinstance(text, str):
            text = str(text)
        
        # Lowercase
        if self.lowercase:
            text = text.lower()
        
        # Remove punctuation
        if self.remove_punctuation:
            text = re.sub(r'[^\w\s]', ' ', text)
        
        # Remove stopwords
        if self.remove_stopwords:
            words = text.split()
            words = [w for w in words if w not in self.stopwords]
            text = ' '.join(words)
        
        # Normalize whitespace
        if self.normalize_whitespace:
            text = ' '.join(text.split())
        
        return text
    
    def clean_structured_data(
        self,
        data: Any,
        text_columns: Optional[List[str]] = None
    ) -> Any:
        """
        Clean structured data (DataFrame or dict).
        
        Args:
            data: Data to clean
            text_columns: Columns to treat as text
            
        Returns:
            Cleaned data
        """
        if isinstance(data, pd.DataFrame):
            df = data.copy()
            
            if text_columns is None:
                # Guess text columns (object dtype)
                text_columns = df.select_dtypes(include=['object']).columns
            
            for col in text_columns:
                if col in df.columns:
                    df[col] = df[col].apply(self.clean_text)
            
            return df
        
        elif isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                if isinstance(value, str):
                    cleaned[key] = self.clean_text(value)
                else:
                    cleaned[key] = value
            return cleaned
        
        elif isinstance(data, list):
            return [self.clean_structured_data(item) for item in data]
        
        else:
            return data
    
    def split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using NLTK.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        return sent_tokenize(text)
    
    def normalize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize metadata values.
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            Normalized metadata
        """
        normalized = {}
        for key, value in metadata.items():
            if isinstance(value, str):
                normalized[key] = self.clean_text(value)
            elif isinstance(value, (list, dict)):
                normalized[key] = self.clean_structured_data(value)
            else:
                normalized[key] = value
        return normalized 