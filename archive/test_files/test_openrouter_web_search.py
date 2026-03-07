"""
OpenRouter Web Search Plugin Examples
Based on: https://openrouter.ai/docs/guides/features/plugins/web-search.md
"""

import requests
import json
from typing import Optional, Dict, List, Any

class OpenRouterWebSearch:
    def __init__(self, api_key: str):
        """
        Initialize OpenRouter client with API key

        Args:
            api_key: Your OpenRouter API key
        """
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def chat_with_web_search_shortcut(
        self,
        messages: List[Dict[str, str]],
        model: str = "openai/gpt-4o"
    ) -> Dict[str, Any]:
        """
        Example 1: Using :online shortcut to enable web search

        Args:
            messages: List of chat messages
            model: Base model name (will append :online)

        Returns:
            API response
        """
        payload = {
            "model": f"{model}:online",
            "messages": messages
        }

        response = requests.post(self.base_url, headers=self.headers, json=payload)
        return response.json()

    def chat_with_web_plugin(
        self,
        messages: List[Dict[str, str]],
        model: str = "openrouter/auto"
    ) -> Dict[str, Any]:
        """
        Example 2: Using web plugin explicitly (equivalent to :online)

        Args:
            messages: List of chat messages
            model: Model name

        Returns:
            API response
        """
        payload = {
            "model": model,
            "messages": messages,
            "plugins": [{"id": "web"}]
        }

        response = requests.post(self.base_url, headers=self.headers, json=payload)
        return response.json()

    def chat_with_custom_web_plugin(
        self,
        messages: List[Dict[str, str]],
        model: str = "openai/gpt-4o",
        engine: Optional[str] = None,
        max_results: int = 5,
        search_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Example 3: Customizing the web plugin

        Args:
            messages: List of chat messages
            model: Model name
            engine: "native", "exa", or None (auto-select)
            max_results: Maximum number of search results (default: 5)
            search_prompt: Custom prompt for search results

        Returns:
            API response
        """
        plugin_config = {
            "id": "web",
            "max_results": max_results
        }

        if engine:
            plugin_config["engine"] = engine

        if search_prompt:
            plugin_config["search_prompt"] = search_prompt

        payload = {
            "model": model,
            "messages": messages,
            "plugins": [plugin_config]
        }

        response = requests.post(self.base_url, headers=self.headers, json=payload)
        return response.json()

    def chat_with_native_search_context(
        self,
        messages: List[Dict[str, str]],
        model: str = "openai/gpt-4.1",
        search_context_size: str = "medium"
    ) -> Dict[str, Any]:
        """
        Example 4: Using native search with specific context size

        Args:
            messages: List of chat messages
            model: Model name
            search_context_size: "low", "medium", or "high"

        Returns:
            API response
        """
        payload = {
            "model": model,
            "messages": messages,
            "web_search_options": {
                "search_context_size": search_context_size
            }
        }

        response = requests.post(self.base_url, headers=self.headers, json=payload)
        return response.json()

    def parse_web_citations(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse web search citations from the response

        Args:
            response: API response

        Returns:
            List of citations with URL, title, content, and positions
        """
        citations = []

        if "choices" in response and len(response["choices"]) > 0:
            message = response["choices"][0].get("message", {})
            annotations = message.get("annotations", [])

            for annotation in annotations:
                if annotation.get("type") == "url_citation":
                    citation_data = annotation.get("url_citation", {})
                    citations.append({
                        "url": citation_data.get("url"),
                        "title": citation_data.get("title"),
                        "content": citation_data.get("content"),
                        "start_index": citation_data.get("start_index"),
                        "end_index": citation_data.get("end_index")
                    })

        return citations


# Example usage
def main():
    import os
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    # Get API key from environment
    API_KEY = os.getenv("OPENROUTER_API_KEY")

    if not API_KEY:
        print("ERROR: OPENROUTER_API_KEY not found in environment variables!")
        print("Please set it in your .env file")
        return

    client = OpenRouterWebSearch(API_KEY)

    # Example messages
    messages = [
        {
            "role": "user",
            "content": "What are the latest developments in quantum computing in 2025?"
        }
    ]

    print("=" * 80)
    print("Example 1: Using :online shortcut with GPT-4o")
    print("=" * 80)
    try:
        response1 = client.chat_with_web_search_shortcut(messages, model="openai/gpt-4o")
        if "error" in response1:
            print(f"ERROR: {response1['error']}")
        else:
            print("Response:")
            print(response1["choices"][0]["message"]["content"])
    except Exception as e:
        print(f"ERROR: {e}")

    print("\n" + "=" * 80)
    print("Example 2: Using web plugin explicitly with DeepSeek")
    print("=" * 80)
    try:
        response2 = client.chat_with_web_plugin(messages, model="deepseek/deepseek-chat")
        if "error" in response2:
            print(f"ERROR: {response2['error']}")
        else:
            print("Response:")
            print(response2["choices"][0]["message"]["content"])
    except Exception as e:
        print(f"ERROR: {e}")

    print("\n" + "=" * 80)
    print("Example 3: Custom web plugin with native engine, 3 results")
    print("=" * 80)
    try:
        response3 = client.chat_with_custom_web_plugin(
            messages,
            model="deepseek/deepseek-chat",
            engine="native",
            max_results=3,
            search_prompt="Here are the relevant search results:"
        )
        if "error" in response3:
            print(f"ERROR: {response3['error']}")
        else:
            print("Response:")
            print(response3["choices"][0]["message"]["content"])
    except Exception as e:
        print(f"ERROR: {e}")

    print("\n" + "=" * 80)
    print("Example 4: Testing website analysis (like our endpoint)")
    print("=" * 80)
    website_messages = [
        {
            "role": "user",
            "content": """Analyze the website at https://www.airbnb.com/ and extract key business information.

Please provide in JSON format:
{
  "company_name": "The company or product name",
  "company_description": "A comprehensive 4-5 sentence description",
  "value_proposition": "A concise statement explaining unique value",
  "business_niche": "The specific industry or market segment",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}

Provide ONLY valid JSON, no additional text."""
        }
    ]

    try:
        response4 = client.chat_with_custom_web_plugin(
            website_messages,
            model="deepseek/deepseek-chat",
            engine="native",
            max_results=5
        )
        if "error" in response4:
            print(f"ERROR: {response4['error']}")
        else:
            print("Response:")
            content = response4["choices"][0]["message"]["content"]
            print(content)

            # Try to parse JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                print("\n\nParsed JSON:")
                print(json.dumps(parsed, indent=2))
    except Exception as e:
        print(f"ERROR: {e}")

    print("\n" + "=" * 80)
    print("Example 5: Parsing web citations (if available)")
    print("=" * 80)
    try:
        if 'response2' in locals() and "error" not in response2:
            citations = client.parse_web_citations(response2)
            if citations:
                for i, citation in enumerate(citations, 1):
                    print(f"\nCitation {i}:")
                    print(f"  URL: {citation['url']}")
                    print(f"  Title: {citation['title']}")
                    if citation['content']:
                        print(f"  Content: {citation['content'][:100]}...")
                    print(f"  Position: {citation['start_index']} - {citation['end_index']}")
            else:
                print("No citations found in response")
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    main()
