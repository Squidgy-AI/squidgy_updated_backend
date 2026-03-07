#!/usr/bin/env python3
"""
Test what OpenRouter AI actually returns for jackwacker.com
"""
import httpx
import asyncio
import json
import re
import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

async def test_analysis():
    url = "https://www.jackwacker.com"

    analysis_prompt = f"""Analyze the website at {url} and extract key business information.

Please provide in JSON format:
{{
  "company_name": "The company or product name",
  "company_description": "A comprehensive 8-10 sentence description covering: what the company does, their main products/services, who they serve, what makes them notable or unique in their space, their key features, target audience, competitive advantages, and business model",
  "value_proposition": "A concise statement (1-2 sentences) explaining the unique value or benefit this company/product offers",
  "business_niche": "The specific industry or market segment (e.g., 'E-commerce Platform', 'SaaS Analytics', 'Fintech')",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}

Guidelines:
- company_description should be detailed (8-10 complete sentences)
- Focus on WHAT they offer and WHY it matters
- Be specific about their market/industry
- Use 3-5 relevant keywords as tags
- If any field cannot be determined, use null

Provide ONLY valid JSON, no additional text."""

    print("Testing OpenRouter Web Search API for jackwacker.com...")
    print("=" * 80)

    async with httpx.AsyncClient() as http_client:
        response = await http_client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://app.squidgy.ai",
                "X-Title": "Squidgy AI Website Analyzer Test"
            },
            json={
                "model": "deepseek/deepseek-chat",
                "plugins": [{"id": "web", "engine": "native", "max_results": 5}],
                "messages": [{
                    "role": "user",
                    "content": analysis_prompt
                }],
                "temperature": 0.3,
                "max_tokens": 1500
            },
            timeout=30.0
        )

        response.raise_for_status()
        data = response.json()

    print("\nAPI Response Structure:")
    print(f"- Has 'choices': {('choices' in data)}")
    if 'choices' in data:
        print(f"- Number of choices: {len(data['choices'])}")

    ai_response = data['choices'][0]['message']['content'].strip()

    print("\nRaw AI Response:")
    print("=" * 80)
    print(ai_response)
    print("=" * 80)

    # Try to parse JSON
    json_match = re.search(r'```json\s*(.*?)\s*```', ai_response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = ai_response

    print("\nExtracted JSON:")
    print("=" * 80)
    print(json_str)
    print("=" * 80)

    try:
        parsed = json.loads(json_str)
        print("\nParsed Data:")
        print("=" * 80)
        print(json.dumps(parsed, indent=2))
        print("=" * 80)

        print("\n🔍 ANALYSIS:")
        print(f"Company Name: {parsed.get('company_name')}")
        print(f"Business Niche: {parsed.get('business_niche')}")
        print(f"\nDescription: {parsed.get('company_description')}")

        if "digital marketing" in parsed.get('company_description', '').lower():
            print("\n❌ ERROR: AI incorrectly identified as digital marketing agency!")
        elif "fishing" in parsed.get('company_description', '').lower():
            print("\n✅ SUCCESS: AI correctly identified as fishing gear company!")
        else:
            print("\n⚠️ UNKNOWN: AI response doesn't mention digital marketing or fishing")

    except Exception as e:
        print(f"\n❌ Failed to parse JSON: {e}")

if __name__ == "__main__":
    asyncio.run(test_analysis())
