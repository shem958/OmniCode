import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
api_key = os.getenv("OPENAI_API_KEY")
print("API Key loaded:", api_key[:15] + "..." if api_key else "None")

try:
    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(
        input=["Hello world"],
        model="text-embedding-3-small"
    )
    print("Success: Embedding generated successfully! Size:", len(response.data[0].embedding))
except Exception as e:
    print("Error during embedding generation:", str(e))
    sys.exit(1)
