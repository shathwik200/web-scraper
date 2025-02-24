import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from groq import Groq
from flask import Flask, render_template, request, redirect, url_for, flash
import markdown
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")

def is_valid_url(url):
    parsed = urlparse(url)
    return bool(parsed.scheme and parsed.netloc)

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
    text = soup.get_text(separator=' ', strip=True)
    return text if text else "[No text content found on the page.]"

def chunk_text(text, max_chunk_size):
    words = text.split()
    return [' '.join(words[i:i + max_chunk_size]) for i in range(0, len(words), max_chunk_size)]

def summarize_text_with_groq(text, max_words_per_chunk=1000):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY not found in environment variables.")
        return "[API key not configured.]"
    
    if not text.strip():
        return "[No content provided for summarization.]"
    
    client = Groq(api_key=api_key)
    chunks = chunk_text(text, max_chunk_size=max_words_per_chunk)
    summary_chunks = []
    
    for index, chunk in enumerate(chunks, 1):
        print(f"Summarizing chunk {index}/{len(chunks)}...")
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are an assistant that summarizes web page content in markdown format."},
                    {"role": "user", "content": f"Summarize the following content in markdown format:\n{chunk}"}
                ],
                temperature=0.7,
                max_completion_tokens=1024,
                top_p=1,
                stream=False,
            )
            summary_text = completion.choices[0].message.content.strip()
            summary_chunks.append(summary_text)
        except Exception as e:
            print(f"Error during summarization of chunk {index}: {e}")
            summary_chunks.append("[Error summarizing this chunk]")
    
    return "\n".join(summary_chunks)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url", "").strip()
        if not url:
            flash("URL is required.", "danger")
            return redirect(url_for("index"))
        
        if not urlparse(url).scheme:
            url = "http://" + url
        
        if not is_valid_url(url):
            flash("Invalid URL provided.", "danger")
            return redirect(url_for("index"))
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:119.0) Gecko/20100101 Firefox/119.0'
        }
        
        flash("Scraping the web page...", "info")
        content = scrape_page(url, headers)
        if not content:
            flash("Failed to retrieve any content from the page.", "danger")
            return redirect(url_for("index"))
        
        flash("Generating summary...", "info")
        summary = summarize_text_with_groq(content)
        rendered_summary = markdown.markdown(summary)
        
        return render_template("result.html", url=url, summary=rendered_summary)
    return render_template("index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
