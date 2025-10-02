#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import random
from datetime import datetime, timedelta

# ---------- Global Variables ----------
MB_USED_TOTAL = 0

# ---------- Helper Functions ----------
def bytes_to_mb(byte_count):
    return byte_count / (1024 * 1024)

def extract_location(query):
    """Extracts the main location keyword from a weather query."""
    words = query.lower().split()
    if 'weather' in words:
        idx = words.index('weather')
        location = ' '.join(words[idx+1:idx+4])
        return location.strip()
    return None

def infer_search(query):
    """Expands one-word queries to more relevant searches."""
    intent_keywords = {
        "cookies": "peanut butter cookie recipe",
        "gamestop": "GameStop stock price",
        "weather": query
    }
    for key, suggestion in intent_keywords.items():
        if key.lower() in query.lower():
            return suggestion
    return query

def fetch_bing_results(query, max_results=5):
    """Fetches Bing search results for a query."""
    global MB_USED_TOTAL
    url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
    response = requests.get(url)
    MB_USED_TOTAL += bytes_to_mb(len(response.content))

    soup = BeautifulSoup(response.text, 'html.parser')
    results = []

    for li in soup.find_all('li', {'class': 'b_algo'})[:max_results]:
        title_tag = li.find('h2')
        snippet_tag = li.find('p')
        link_tag = title_tag.find('a') if title_tag else None

        if title_tag:
            title = title_tag.get_text(separator=' ', strip=True)
            snippet = snippet_tag.get_text(separator=' ', strip=True) if snippet_tag else "No snippet available."
            link = link_tag['href'] if link_tag else "No link"
            results.append({'title': title, 'snippet': snippet, 'link': link})
    return results

def fetch_wikipedia_summary(term):
    """Fetches the Wikipedia summary of a term."""
    global MB_USED_TOTAL
    api_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{term.replace(' ', '_')}"
    response = requests.get(api_url)
    MB_USED_TOTAL += bytes_to_mb(len(response.content))

    if response.status_code == 200:
        data = response.json()
        return data.get("extract", "No summary found.")
    else:
        return "No summary found."

def mayan_weather_interpretation(location):
    """Returns a symbolic Mayan-style weather reading."""
    symbols = ["☀️ Sun", "🌧️ Rain", "🌪️ Storm", "🌙 Moon", "🌿 Fertility"]
    return f"Mayan reading for {location}: {random.choice(symbols)}"

def simulate_weather(location):
    """Simulates hourly and 15-minute weather forecasts."""
    hourly = []
    min15 = []
    now = datetime.now()
    for h in range(10):  # next 10 hours
        t = now + timedelta(hours=h)
        temp_c = random.randint(16, 30)
        temp_f = int(temp_c * 9/5 + 32)
        emoji = random.choice(["🌤", "🌧", "🌪", "⛅", "🌙", "❄️"])
        comment = random.choice([
            "Beware the flying cocoa beans!",
            "Perfect for chocolate factory experiments!",
            "A sweet breeze is in the air.",
            "Time to dance among candy machines!",
            "Chocolate river flowing smoothly.",
            "Cocoa beans falling gently."
        ])
        hourly.append(f"{t.strftime('%H:%M')} → {temp_c}°C / {temp_f}°F {emoji} | {comment}")

    for i in range(40):  # 15-minute intervals (~10 hours)
        t = now + timedelta(minutes=15*i)
        temp_c = random.randint(16, 30)
        temp_f = int(temp_c * 9/5 + 32)
        emoji = random.choice(["🌤", "🌧", "🌪", "⛅", "🌙", "❄️"])
        comment = random.choice([
            "Cocoa beans falling gently.",
            "Marshmallow clouds overhead.",
            "Chocolate river flowing smoothly.",
            "Candy wrappers may fly around."
        ])
        min15.append(f"{t.strftime('%H:%M')} → {temp_c}°C / {temp_f}°F {emoji} | {comment}")

    return hourly, min15

# ---------- Main Terminal ----------
def run_internet_terminal():
    print("🍫 Willy Wonka Internet Feed with Wikipedia & Mayan Calendar 🍫")
    while True:
        query = input("\nEnter search query (or 'exit'): ").strip()
        if query.lower() == 'exit':
            break

        location = extract_location(query)
        if location:
            # Weather query
            hourly, min15 = simulate_weather(location)
            mayan_reading = mayan_weather_interpretation(location)
            results = fetch_bing_results(f"weather {location}")

            print(f"\nMB used: {MB_USED_TOTAL:.6f}\n")
            print(f"🌆 Local simulated weather for {query} 🌆")
            print("\nHourly forecast:")
            for h in hourly:
                print(h)
            print("\n15-minute forecast:")
            for m in min15:
                print(m)
            print("\n" + mayan_reading + "\n")
        else:
            # General search
            real_query = infer_search(query)
            summary = fetch_wikipedia_summary(real_query)
            results = fetch_bing_results(real_query)

            print(f"\nMB used: {MB_USED_TOTAL:.6f}\n")
            print(f"📚 Wikipedia summary for '{real_query}':\n{summary}\n")
            print("🔗 Bing search results:")
            for i, r in enumerate(results, 1):
                print(f"{i}. {r['title']}\n   {r['snippet']}\n   {r['link']}\n")

        input("Press Enter for new search...")

# ---------- Run ----------
if __name__ == "__main__":
    run_internet_terminal()
