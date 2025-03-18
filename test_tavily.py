from tavily import TavilyClient
import os

# Set the API key
os.environ['TAVILY_API_KEY'] = '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'

# Create client
client = TavilyClient(api_key=os.environ['TAVILY_API_KEY'])

try:
    # Test basic search
    print("Testing basic search...")
    result = client.search(query='test query')
    print('Search successful:', bool(result))
    print('Result keys:', result.keys())
    
    # Test with parameters
    print("\nTesting search with parameters...")
    result = client.search(
        query='test query',
        search_depth="basic",
        include_answer=True,
        include_images=False,
        max_results=5
    )
    print('Search with parameters successful:', bool(result))
    
except Exception as e:
    print('Error:', e)
