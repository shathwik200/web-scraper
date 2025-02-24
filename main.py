import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from groq import Groq
import os

def is_valid_url(url):
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)

def get_page(url, headers):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

def scrape_page(url, headers):
    response = get_page(url, headers)
    if not response:
        return ""

    soup = BeautifulSoup(response.content, 'html.parser')
    return soup.get_text(separator=' ', strip=True)

def chunk_text(text, max_chunk_size):
    words = text.split()
    for i in range(0, len(words), max_chunk_size):
        yield ' '.join(words[i:i + max_chunk_size])

def summarize_text_with_groq(text, api_key, max_words_per_chunk=1000):
    if not text:
        print("No content to summarize.")
        return ""

    client = Groq(api_key=api_key)
    chunks = list(chunk_text(text, max_words_per_chunk))
    summary_chunks = []

    for index, chunk in enumerate(chunks, 1):
        print(f"Summarizing chunk {index}/{len(chunks)}...")
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are an assistant that summarizes web page content."},
                    {"role": "user", "content": f"Summarize the following content:\n{chunk}"}
                ],
                temperature=0.7,
                max_completion_tokens=1024,
                top_p=1,
                stream=False,
            )
            summary_text = completion.choices[0].message.content.strip()
            print(summary_text)
            summary_chunks.append(summary_text)
        except Exception as e:
            print(f"Error during summarization of chunk {index}: {e}")
            summary_chunks.append("[Error in this chunk]")

    return "\n".join(summary_chunks)

def save_to_file(content, summary, content_filename='page_content.txt', summary_filename='summary.txt'):
    with open(content_filename, 'w', encoding='utf-8') as content_file:
        content_file.write(content)

    with open(summary_filename, 'w', encoding='utf-8') as summary_file:
        summary_file.write(summary)

    print(f"Content saved to '{content_filename}' and summary to '{summary_filename}'.")

def main():
    url = input("Enter the website URL to scrape: ")
    api_key = os.getenv("GROQ_API_KEY")  # Replace with your API key or prompt for input

    if not urlparse(url).scheme:
        url = "http://" + url

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }

    content = scrape_page(url, headers)
    summary = summarize_text_with_groq(content, api_key)
    save_to_file(content, summary)
    print("\nScraping and summarization complete.")

if __name__ == "__main__":
    main()
