import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from flask import Flask, render_template, request, redirect, url_for, flash
import markdown
from dotenv import load_dotenv
import google.generativeai as genai

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
    except requests.RequestException:
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
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64)'
        }
        content = scrape_page(url, headers)
        if not content:
            flash("Failed to retrieve any content.", "danger")
            return redirect(url_for("index"))
        summary = summarize_text_with_gemini(content)
        rendered_summary = markdown.markdown(summary)
        return render_template("result.html", url=url, summary=rendered_summary)
    return render_template("index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
