#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template_string
import threading
import webbrowser
import random

# ---------------- MB Tracking ----------------
MB_TOTAL = 400_000_000.0
MB_USED_TOTAL = 0.0

def bytes_to_mb(byte_count):
    return byte_count / (1024 * 1024)

# ---------------- Flask Web Display ----------------
app = Flask(__name__)
current_url = None

@app.route('/')
def render_page():
    global current_url
    if current_url:
        try:
            r = requests.get(current_url)
            content = r.text
        except Exception as e:
            content = f"<p>Could not fetch URL: {e}</p>"
    else:
        content = "<p>No URL selected. Enter a URL in the terminal search.</p>"

    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head><meta charset="UTF-8"><title>Local Page Preview</title></head>
    <body>{{ content|safe }}</body>
    </html>
    """
    return render_template_string(template, content=content)

def start_flask():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# ---------------- Bing & Mayan Weather ----------------
def extract_location(query):
    words = query.lower().split()
    if 'weather' in words:
        idx = words.index('weather')
        location = ' '.join(words[idx+1:idx+4])
        return location.strip()
    return None

def fetch_bing_results(query, max_results=5):
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
            title = title_tag.get_text(strip=True)
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else "No snippet available."
            link = link_tag['href'] if link_tag else "No link"
            results.append({'title': title, 'snippet': snippet, 'link': link})
    return results

def mayan_weather_interpretation(location):
    symbols = ["☀️ Sun", "🌧️ Rain", "🌪️ Storm", "🌙 Moon", "🌿 Fertility"]
    description = f"Mayan reading for {location}: {random.choice(symbols)}"
    return description

# ---------------- Terminal ----------------
def run_internet_terminal():
    global current_url, MB_USED_TOTAL
    flask_thread_started = False

    print("🍫 Willy Wonka Internet Terminal 🍫")
    print("Type a URL to preview in local web display.")

    while True:
        query = input("\nEnter search query or URL (or 'exit'): ").strip()
        if query.lower() == 'exit':
            break

        # URL case
        if query.startswith("http://") or query.startswith("https://"):
            current_url = query
            if not flask_thread_started:
                threading.Thread(target=start_flask, daemon=True).start()
                flask_thread_started = True
            print(f"Opening {query} in local Flask preview...")
            webbrowser.open("http://localhost:5000/")
            continue

        # Weather query
        location = extract_location(query)
        if location:
            results = fetch_bing_results(f"weather {location}")
            mayan_reading = mayan_weather_interpretation(location)
            print(f"\nMB used: {MB_USED_TOTAL:.6f} | MB remaining: {MB_TOTAL - MB_USED_TOTAL:.2f}\n")
            print(mayan_reading)
            for i, r in enumerate(results, 1):
                print(f"{i}. {r['title']}\n   {r['snippet']}\n   {r['link']}\n")
        else:
            results = fetch_bing_results(query)
            print(f"\nMB used: {MB_USED_TOTAL:.6f} | MB remaining: {MB_TOTAL - MB_USED_TOTAL:.2f}\n")
            for i, r in enumerate(results, 1):
                print(f"{i}. {r['title']}\n   {r['snippet']}\n   {r['link']}\n")

        input("Press Enter for new search...")

# ---------------- Run ----------------
if __name__ == "__main__":
    run_internet_terminal()
