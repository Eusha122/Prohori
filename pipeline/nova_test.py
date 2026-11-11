"""Quick check that Amazon Nova on Bedrock works with the keys in .env."""
from pathlib import Path
import boto3
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

client = boto3.client("bedrock-runtime", region_name="us-east-1")
for model in ["us.amazon.nova-2-lite-v1:0", "us.amazon.nova-micro-v1:0"]:
    try:
        r = client.converse(
            modelId=model,
            messages=[{"role": "user", "content": [{"text": "এক বাক্যে বলুন: সরকারি কেনাকাটায় স্বচ্ছতা কেন জরুরি?"}]}],
            inferenceConfig={"maxTokens": 120},
        )
        print("OK  ", model, "->", r["output"]["message"]["content"][0]["text"].strip())
    except Exception as e:
        print("FAIL", model, "->", type(e).__name__, str(e)[:200])
