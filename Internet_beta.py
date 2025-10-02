#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import time
import os
import datetime
import random

# ---------------- MB simulation ----------------
MB_STORAGE = 1000
AMPLIFIER = 132_000
BW_PER_MB = ((2.71828 ** (2*3.14159)) + (3.14159 ** (2*2*2.71828))) * AMPLIFIER
MB_USED_TOTAL = 0

def mb_bandwidth_delay(size_mb):
    """Simulate bandwidth delay and track MB used"""
    global MB_USED_TOTAL
    bw = MB_STORAGE * BW_PER_MB
    transfer_time = size_mb / bw
    if transfer_time > 0:
        time.sleep(min(transfer_time, 0.05))
    MB_USED_TOTAL += size_mb

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

# ---------------- Mayan calendar ----------------
def get_mayan_calendar(day_query=None):
    day_signs = [
        "Imix", "Ik'", "Ak'b'al", "K'an", "Chikchan",
        "Kimi", "Manik'", "Lamat", "Muluk", "Ok",
        "Chuwen", "Eb'", "B'en", "Ix", "Men",
        "Kib'", "Kab'an", "Etz'nab'", "Kawak", "Ajaw"
    ]
    today = datetime.date.today()
    tzolkin_number = (today.toordinal() % 13) + 1
    tzolkin_sign = day_signs[today.toordinal() % 20]
    return f"Mayan Calendar for {today}: {tzolkin_number} {tzolkin_sign}"

# ---------------- weather ----------------
def real_weather(city="Flint"):
    now = datetime.datetime.now()
    output = f"🌆 Local weather for {city} 🌆\n\n"
    
    # Hourly forecast for next 6 hours
    output += "Hourly forecast:\n"
    for i in range(6):
        hour = now + datetime.timedelta(hours=i)
        temp_c = random.randint(15, 30)
        temp_f = int(temp_c * 9/5 + 32)
        emoji = random.choice(["🌞","🌤","⛅","🌧","⛈","🌫","❄️"])
        activity = random.choice([
            "Perfect for chocolate factory experiments!",
            "Beware the flying cocoa beans!",
            "A sweet breeze is in the air.",
            "Time to dance among candy machines!",
            "Tiny chocolate rain expected."
        ])
        output += f"{hour.strftime('%H:%M')} → {temp_c}°C / {temp_f}°F {emoji} | {activity}\n"
    
    # 15-minute forecast for next 2 hours
    output += "\n15-minute forecast:\n"
    for i in range(8):  # 2 hours / 15 min intervals
        quarter = now + datetime.timedelta(minutes=15*i)
        temp_c = random.randint(15, 30)
        temp_f = int(temp_c * 9/5 + 32)
        emoji = random.choice(["🌞","🌤","⛅","🌧","⛈","🌫","❄️"])
        activity = random.choice([
            "Chocolate river flowing smoothly.",
            "Candy wrappers may fly around.",
            "Perfect time to invent new sweets.",
            "Cocoa beans falling gently.",
            "Marshmallow clouds overhead."
        ])
        output += f"{quarter.strftime('%H:%M')} → {temp_c}°C / {temp_f}°F {emoji} | {activity}\n"
    
    return output

# ---------------- Bing search feed ----------------
def fetch_bing_links(query, max_links=5):
    url = f"https://www.bing.com/search?q={query.replace(' ','+')}"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=8)
    mb_bandwidth_delay(len(resp.content)/(1024*1024))
    soup = BeautifulSoup(resp.text, 'html.parser')
    results = []
    for item in soup.find_all('li', class_='b_algo')[:max_links]:
        link_tag = item.find('a')
        title_tag = item.find('h2')
        if link_tag and title_tag:
            results.append({
                'title': title_tag.get_text().strip(),
                'link': link_tag.get('href')
            })
    return results

def fetch_page_content(url, max_chars=300):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=5)
        mb_bandwidth_delay(len(resp.content)/(1024*1024))
        soup = BeautifulSoup(resp.text, 'html.parser')
        paragraphs = soup.find_all('p')
        text = ' '.join([p.get_text().strip() for p in paragraphs])
        return text[:max_chars] + '...' if text else "No content available."
    except:
        return "Failed to fetch content."

def display_feed(results, query):
    clear_screen()
    print(f"Search: {query}  |  MB used: {MB_USED_TOTAL:.6f}\n")
    for i, r in enumerate(results, 1):
        content = fetch_page_content(r['link'])
        print(f"{i}. {r['title']}\n   {content}\n   {r['link']}\n")

# ---------------- Main interactive loop ----------------
def main():
    global MB_USED_TOTAL
    clear_screen()
    print("🍫 Willy Wonka Internet Feed with Weather 🍫")
    while True:
        query = input("\nEnter search query (or 'exit'): ").strip()
        if query.lower() in ('exit','quit'):
            break

        MB_USED_TOTAL = 0

        # Repurpose 'weather' queries for simulated weather
        if "weather" in query.lower():
            city = query.lower().replace("weather", "").strip() or "Flint"
            print(simulate_weather(city))
            input("\nPress Enter for new search...")
            continue

        # Repurpose 'mayan' queries for calendar
        if "mayan" in query.lower():
            print(get_mayan_calendar())
            input("\nPress Enter for new search...")
            continue

        # Bing feed for other searches
        links = fetch_bing_links(query, max_links=5)
        if not links:
            print("No results found.")
            input("\nPress Enter for new search...")
            continue
        display_feed(links, query)
        input("\nPress Enter for new search...")

if __name__ == "__main__":
    main()
