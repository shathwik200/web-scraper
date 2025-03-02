import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import google.generativeai as genai

def is_valid_url(url):
    parsed = urlparse(url)
    return bool(parsed.scheme and parsed.netloc)

def get_page(url, headers):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response
    except requests.RequestException:
        return None

def scrape_page(url, headers):
    response = get_page(url, headers)
    if not response:
        return ""
    soup = BeautifulSoup(response.content, 'html.parser')
    return soup.get_text(separator=' ', strip=True)

def chunk_text(text, max_chunk_size):
    words = text.split()
    return [' '.join(words[i:i+max_chunk_size]) for i in range(0, len(words), max_chunk_size)]

def summarize_text_with_gemini(text, max_words_per_chunk=1000):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "[API key not configured.]"
    if not text.strip():
        return "[No content provided for summarization.]"
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    chunks = chunk_text(text, max_words_per_chunk)
    summary_chunks = []
    for chunk in chunks:
        try:
            prompt = f"Summarize the following content in markdown format:\n{chunk}"
            response = model.generate_content(prompt)
            summary_chunks.append(response.text.strip() if response.text else "[No summary generated.]")
        except Exception:
            summary_chunks.append("[Error summarizing this chunk]")
    return "\n".join(summary_chunks)

def save_to_file(content, summary, content_filename='page_content.txt', summary_filename='summary.txt'):
    with open(content_filename, 'w', encoding='utf-8') as content_file:
        content_file.write(content)
    with open(summary_filename, 'w', encoding='utf-8') as summary_file:
        summary_file.write(summary)

def main():
    url = input("Enter the website URL to scrape: ").strip()
    if not urlparse(url).scheme:
        url = "http://" + url
    headers = {'User-Agent': 'Mozilla/5.0'}
    content = scrape_page(url, headers)
    summary = summarize_text_with_gemini(content)
    save_to_file(content, summary)
    print("Scraping and summarization complete.")

if __name__ == "__main__":
    main()
