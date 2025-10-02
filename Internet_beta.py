#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup

MB_USED_TOTAL = 0

def bytes_to_mb(byte_count):
    return byte_count / (1024 * 1024)

def fetch_bing_results(query, max_results=5):
    global MB_USED_TOTAL
    url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
    response = requests.get(url)
    MB_USED_TOTAL += bytes_to_mb(len(response.content))

    soup = BeautifulSoup(response.text, 'html.parser')
    results = []

    # Only extract clean text: title, snippet, link
    for li in soup.find_all('li', {'class': 'b_algo'})[:max_results]:
        title_tag = li.find('h2')
        if title_tag:
            link_tag = title_tag.find('a')
            snippet_tag = li.find('p')

            # Clean the text
            title = title_tag.get_text(separator=' ', strip=True)
            link = link_tag['href'] if link_tag else "No link"
            snippet = snippet_tag.get_text(separator=' ', strip=True) if snippet_tag else "No content available."

            results.append({'title': title, 'snippet': snippet, 'link': link})

    return results

def search_terminal():
    print("🍫 Willy Wonka Internet Terminal 🍫")
    while True:
        query = input("\nEnter your search query (or 'exit' to quit): ").strip()
        if query.lower() == 'exit':
            break

        results = fetch_bing_results(query)
        if not results:
            print(f"No results found for '{query}'\n")
            continue

        print(f"\nMB used: {MB_USED_TOTAL:.6f}\n")
        for i, r in enumerate(results, 1):
            print(f"{i}. {r['title']}")
            print(f"   {r['snippet']}")
            print(f"   Link: {r['link']}\n")

        input("Press Enter for new search...")

if __name__ == "__main__":
    search_terminal()
