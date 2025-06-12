import json
from decimal import Decimal
from datetime import datetime, date

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Decimal and datetime objects."""
    
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj) 