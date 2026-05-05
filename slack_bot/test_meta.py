import os
from dotenv import load_dotenv
from services.meta import get_account_summary

load_dotenv()

print(f"Testing Meta API with Account ID from .env...")
data, error = get_account_summary()

if error:
    print(f"Error: {error}")
else:
    print(f"Success! Fetched {len(data)} campaigns.")
    print(data)
