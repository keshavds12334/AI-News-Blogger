import streamlit as st
import requests
import json
import re
from datetime import datetime
import time

st.set_page_config(
    page_title="AI News Auto-Blogger",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;1,400&family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #fafaf9; color: #1c1917; }

.hero {
    background: linear-gradient(135deg, #1c1917 0%, #292524 60%, #1c1917 100%);
    border-radius: 20px; padding: 2.5rem 3rem; margin-bottom: 1.5rem; color: white;
    position: relative; overflow: hidden;
}
.hero::after { content: '📰'; position:absolute; right:2rem; top:1rem; font-size:6rem; opacity:0.06; }
.hero-title { font-family:'Lora',serif; font-size:2.6rem; font-weight:600; color:#fff; line-height:1.1; }
.hero-sub   { color:#a8a29e; font-size:0.88rem; margin-top:6px; letter-spacing:0.05em; }
.hero-badge { display:inline-block; background:rgba(251,191,36,0.15); color:#fbbf24;
              border:1px solid rgba(251,191,36,0.3); border-radius:50px;
              padding:3px 12px; font-size:11px; font-weight:500; margin-top:10px; }

.workflow-strip {
    display:flex; align-items:center; gap:6px; flex-wrap:wrap;
    background: rgba(255,255,255,0.04); border-radius:12px; padding:10px 14px; margin-top:14px;
}
.wf-step { background:rgba(251,191,36,0.12); border:1px solid rgba(251,191,36,0.25);
           border-radius:6px; padding:4px 12px; font-size:11px; color:#fbbf24; font-weight:500; }
.wf-arr  { color:#57534e; font-size:12px; }

.news-card {
    background: white; border: 1px solid #e7e5e4; border-radius: 16px;
    padding: 1.4rem 1.6rem; margin-bottom: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    transition: box-shadow 0.2s;
}
.news-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); }
.news-tag  { display:inline-block; background:#fef3c7; color:#92400e;
             border-radius:4px; padding:2px 8px; font-size:10px; font-weight:600;
             text-transform:uppercase; letter-spacing:0.08em; margin-bottom:8px; }
.news-title { font-family:'Lora',serif; font-size:1.05rem; font-weight:600;
              color:#1c1917; margin-bottom:6px; line-height:1.3; }
.news-meta  { font-size:11px; color:#a8a29e; margin-bottom:10px; }
.news-body  { font-size:13px; color:#44403c; line-height:1.7; }

.blog-post  { background: white; border-radius: 20px; padding: 2.5rem 3rem;
              box-shadow: 0 4px 24px rgba(0,0,0,0.08); margin-top:1rem; }
.blog-title { font-family:'Lora',serif; font-size:2rem; font-weight:600;
              color:#1c1917; line-height:1.2; margin-bottom:0.5rem; }
.blog-meta  { color:#a8a29e; font-size:12px; border-bottom:1px solid #e7e5e4;
              padding-bottom:1rem; margin-bottom:1.5rem; }
.blog-body  { font-size:15px; color:#292524; line-height:1.9; white-space:pre-wrap; }
.blog-tag   { display:inline-block; background:#f5f5f4; color:#57534e;
              border-radius:50px; padding:4px 14px; font-size:11px; margin:3px; }

.email-preview {
    background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 16px;
    overflow: hidden; margin-top: 1rem;
}
.email-header { background: #1c1917; color: white; padding: 1rem 1.5rem; font-size: 13px; }
.email-field  { display:flex; gap:10px; align-items:baseline;
                border-bottom:1px solid #e5e7eb; padding:8px 16px; font-size:12px; }
.email-label  { color:#6b7280; min-width:50px; font-weight:500; }
.email-val    { color:#1c1917; }
.email-body-box { padding: 1.5rem; font-size:13px; color:#374151; line-height:1.8; white-space:pre-wrap; }

.stat-card { background:white; border:1px solid #e7e5e4; border-radius:14px;
             padding:1rem 1.2rem; text-align:center;
             box-shadow:0 1px 4px rgba(0,0,0,0.04); }
.stat-val  { font-size:1.8rem; font-weight:700; color:#1c1917; }
.stat-lab  { font-size:0.72rem; color:#a8a29e; text-transform:uppercase;
             letter-spacing:0.08em; margin-top:2px; }

div[data-testid="stSidebar"] { background: #fafaf9; border-right: 1px solid #e7e5e4; }
.stButton > button {
    background: linear-gradient(135deg, #1c1917, #292524) !important;
    color: white !important; border: none !important; border-radius: 10px !important;
    font-weight: 600 !important; padding: 0.65rem 1.5rem !important;
}
.stButton > button:hover { opacity: 0.9; }
</style>
""", unsafe_allow_html=True)

# ── Session State ─────────────────────────────────────────────────
for k, v in [('articles',None),('blog_post',None),('email_draft',None),
               ('groq_key', st.secrets.get('GROQ_API_KEY','')),
               ('serp_key', st.secrets.get('SERP_API_KEY',''))]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Groq LLM Call ─────────────────────────────────────────────────
def call_groq(system: str, user: str, api_key: str, model="llama-3.3-70b-versatile", max_tokens=2048) -> str:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role":"system","content":system}, {"role":"user","content":user}],
        "max_tokens": max_tokens, "temperature": 0.7
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                          headers=headers, json=payload, timeout=40)
        if r.status_code != 200:
            try:
                err_body = r.json()
                err_msg = err_body.get("error", {}).get("message", r.text)
            except:
                err_msg = r.text
            return f"ERROR {r.status_code}: {err_msg}"
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"ERROR: {str(e)}"

# ── SerpAPI News Fetch ────────────────────────────────────────────
def fetch_ai_news(query: str, serp_key: str, num: int = 6) -> list:
    url = "https://serpapi.com/search"
    params = {"q": query, "tbm": "nws", "num": num,
               "api_key": serp_key, "hl": "en", "gl": "us"}
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        results = r.json().get("news_results", [])
        articles = []
        for item in results[:num]:
            articles.append({
                "title":   item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "source":  item.get("source", ""),
                "date":    item.get("date", ""),
                "link":    item.get("link", "")
            })
        return articles
    except Exception as e:
        return [{"error": str(e)}]

# ── Demo Articles (when no API key) ──────────────────────────────
DEMO_ARTICLES = [
    {"title":"GPT-5 Rumoured to Launch With Real-Time Multimodal Reasoning","snippet":"OpenAI's next flagship model is expected to feature dramatically improved reasoning capabilities and native multimodal understanding, according to industry sources familiar with the project.","source":"TechCrunch","date":"2 hours ago","link":"#"},
    {"title":"Google DeepMind Releases Gemini 2.0 Ultra — Beats All Benchmarks","snippet":"Google's DeepMind division has released Gemini 2.0 Ultra, claiming state-of-the-art performance on 28 out of 32 industry benchmarks including coding, mathematics, and scientific reasoning.","source":"The Verge","date":"4 hours ago","link":"#"},
    {"title":"Meta Announces Open-Source LLaMA 4 with 400B Parameters","snippet":"Meta has announced LLaMA 4, its largest open-source model yet, promising performance competitive with proprietary models while remaining freely available for research and commercial use.","source":"Wired","date":"6 hours ago","link":"#"},
    {"title":"AI Agents Are Replacing Software Engineers at 12% of Fortune 500 Companies","snippet":"A new McKinsey survey finds that 12% of Fortune 500 companies are now using AI coding agents to handle routine software development tasks, raising new questions about the future of tech employment.","source":"Bloomberg","date":"8 hours ago","link":"#"},
    {"title":"Anthropic Raises $4B in New Funding Round — Valuation Hits $61.5B","snippet":"Anthropic, the AI safety company behind Claude, has secured another $4 billion in funding led by Google, pushing its valuation to $61.5 billion as competition in the AI industry intensifies.","source":"Reuters","date":"10 hours ago","link":"#"},
]

# ── Summarise Articles ────────────────────────────────────────────
def summarise_articles(articles: list, api_key: str) -> str:
    if not api_key:
        return "API key required for summarisation."
    combined = "\n\n".join([f"Title: {a['title']}\nSnippet: {a['snippet']}\nSource: {a['source']}"
                             for a in articles if 'error' not in a])
    system = "You are a professional AI news summariser. Create a concise summary of the key themes across these news articles."
    user   = f"Summarise these AI news articles:\n\n{combined}"
    return call_groq(system, user, api_key, max_tokens=600)

# ── Generate Blog Post ────────────────────────────────────────────
def generate_blog(articles: list, topic: str, tone: str, api_key: str) -> dict:
    combined = "\n\n".join([f"[{i+1}] {a['title']}\n{a['snippet']}" for i,a in enumerate(articles) if 'error' not in a])
    system = f"""You are an expert AI technology blogger who writes engaging, well-structured blog posts.
Write in a {tone} tone. The blog must have:
- A compelling title
- An engaging introduction
- 3-4 main sections with subheadings
- A conclusion with key takeaways
- Be 600-900 words
Return a JSON object with keys: "title", "content", "tags", "summary"
The content should use plain text with section headers marked as ## Header"""

    user = f"""Topic: {topic}
Based on these recent AI news articles, write a comprehensive blog post:

{combined}"""

    raw = call_groq(system, user, api_key, max_tokens=2000)

    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass

    # Fallback: parse manually
    lines   = raw.strip().split('\n')
    title   = lines[0].replace('#','').strip() if lines else "AI Weekly Roundup"
    content = '\n'.join(lines[1:]) if len(lines) > 1 else raw
    return {"title": title, "content": content, "tags": ["AI","Technology","Weekly"], "summary": content[:200]}

# ── Generate Email ────────────────────────────────────────────────
def generate_email(blog: dict, recipient: str, sender: str, api_key: str) -> dict:
    system = "You are an expert email marketer. Write a professional newsletter email to share a blog post. Include subject line, preview text, and email body. Return JSON with keys: subject, preview, body"
    user   = f"Blog title: {blog['title']}\nBlog summary: {blog.get('summary','')}\nRecipient: {recipient}\nSender: {sender}"
    raw    = call_groq(system, user, api_key, max_tokens=800)
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass
    return {"subject": f"📰 {blog['title']}", "preview": blog.get('summary','')[:100], "body": raw}

# ── SIDEBAR ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ API Configuration")
    st.markdown("---")

    groq_key = st.text_input("🔑 Groq API Key", value=st.session_state.groq_key, type="password", placeholder="gsk_...")
    serp_key = st.text_input("🔎 SerpAPI Key", value=st.session_state.serp_key, type="password", placeholder="your_serpapi_key",
                              help="Get free key at serpapi.com · 100 searches/month free")

    if groq_key: st.session_state.groq_key = groq_key
    if serp_key: st.session_state.serp_key = serp_key

    status_groq = "✅ Set" if st.session_state.groq_key else "❌ Missing"
    status_serp = "✅ Set" if st.session_state.serp_key else "⚠️ Using demo articles"
    st.markdown(f"<small>Groq: {status_groq} · SerpAPI: {status_serp}</small>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### ✍️ Blog Settings")
    topic  = st.text_input("Topic / Search Query", value="artificial intelligence latest news 2025")
    tone   = st.selectbox("Writing Tone", ["Professional","Casual and friendly","Technical","Enthusiastic"])
    n_arts = st.slider("Number of articles to fetch", 3, 8, 5)

    st.markdown("---")
    st.markdown("### 📧 Email Settings")
    recipient = st.text_input("Recipient Name", value="AI Enthusiasts Newsletter")
    sender    = st.text_input("Sender Name", value="AI Weekly Digest Team")

    st.markdown("---")
    st.markdown("""<div style="font-size:11px; color:#a8a29e; line-height:1.9">
    <b>Workflow:</b><br>
    Cron Trigger → SerpAPI News<br>
    → Filter AI Articles<br>
    → Groq LLM Summarise<br>
    → Blog Generator<br>
    → Email Formatter → Gmail
    </div>""", unsafe_allow_html=True)

# ── HERO ──────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-title">📰 AI News Auto-Blogger<br>& Email Automation</div>
    <div class="hero-sub">Fetch AI News → Summarise → Generate Blog → Format Email · Powered by Groq + SerpAPI</div>
    <span class="hero-badge">⚡ n8n Workflow Architecture</span>
    <div class="workflow-strip">
        <span class="wf-step">⏰ Cron Trigger</span><span class="wf-arr">→</span>
        <span class="wf-step">🔎 SerpAPI News</span><span class="wf-arr">→</span>
        <span class="wf-step">🔍 Filter AI News</span><span class="wf-arr">→</span>
        <span class="wf-step">🧠 Groq LLM Agent</span><span class="wf-arr">→</span>
        <span class="wf-step">✍️ Blog Generator</span><span class="wf-arr">→</span>
        <span class="wf-step">📧 Email Formatter</span><span class="wf-arr">→</span>
        <span class="wf-step">📮 Gmail Send</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── STEP 1: FETCH NEWS ────────────────────────────────────────────
st.markdown("## Step 1 — Fetch Latest AI News")
col_fetch, col_demo = st.columns([2,1])

with col_fetch:
    fetch_btn = st.button("🔎 Fetch AI News", use_container_width=True)

with col_demo:
    demo_btn  = st.button("📋 Use Demo Articles (no SerpAPI key needed)", use_container_width=True)

if fetch_btn:
    if not st.session_state.serp_key:
        st.warning("No SerpAPI key — loading demo articles instead.")
        st.session_state.articles = DEMO_ARTICLES
    else:
        with st.spinner("Fetching latest AI news from SerpAPI..."):
            arts = fetch_ai_news(topic, st.session_state.serp_key, n_arts)
            if arts and 'error' in arts[0]:
                st.error(f"SerpAPI error: {arts[0]['error']} — using demo articles")
                st.session_state.articles = DEMO_ARTICLES
            else:
                st.session_state.articles = arts
                st.success(f"✅ Fetched {len(arts)} articles!")
    st.session_state.blog_post   = None
    st.session_state.email_draft = None

if demo_btn:
    st.session_state.articles    = DEMO_ARTICLES
    st.session_state.blog_post   = None
    st.session_state.email_draft = None
    st.success("✅ Demo articles loaded!")

# ── DISPLAY ARTICLES ──────────────────────────────────────────────
if st.session_state.articles:
    arts = st.session_state.articles

    c1,c2,c3 = st.columns(3)
    for col, val, lab in zip([c1,c2,c3],
        [str(len(arts)), len(set(a.get('source','') for a in arts)), "AI / Tech"],
        ["Articles","Sources","Category"]):
        with col:
            st.markdown(f'<div class="stat-card"><div class="stat-val">{val}</div><div class="stat-lab">{lab}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    for i, art in enumerate(arts):
        if 'error' in art: continue
        st.markdown(f"""<div class="news-card">
            <div class="news-tag">AI NEWS · {art.get('source','Unknown')}</div>
            <div class="news-title">{art.get('title','')}</div>
            <div class="news-meta">🕐 {art.get('date','Recent')} · {art.get('source','')}</div>
            <div class="news-body">{art.get('snippet','')}</div>
        </div>""", unsafe_allow_html=True)

    # ── STEP 2: GENERATE BLOG ──────────────────────────────────────
    st.markdown("---")
    st.markdown("## Step 2 — Generate Blog Post")

    gen_btn = st.button("✍️ Generate Blog with Groq LLaMA 3", use_container_width=True)

    if gen_btn:
        if not st.session_state.groq_key:
            st.error("⚠️ Please enter your Groq API key in the sidebar.")
        else:
            with st.spinner("🧠 Groq LLaMA 3 is writing your blog post..."):
                blog = generate_blog(arts, topic, tone, st.session_state.groq_key)
                st.session_state.blog_post   = blog
                st.session_state.email_draft = None
            st.success("✅ Blog post generated!")

    if st.session_state.blog_post:
        blog = st.session_state.blog_post

        st.markdown('<div class="blog-post">', unsafe_allow_html=True)
        st.markdown(f'<div class="blog-title">{blog.get("title","AI Weekly Roundup")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="blog-meta">📅 {datetime.now().strftime("%B %d, %Y")} · ✍️ AI Auto-Generated · 🤖 Powered by Groq LLaMA 3</div>', unsafe_allow_html=True)

        content = blog.get("content","")
        # Render headers
        rendered = ""
        for line in content.split('\n'):
            if line.startswith('## '):
                rendered += f'<h3 style="font-family:Lora,serif;color:#1c1917;margin:1.5rem 0 0.5rem;font-size:1.1rem">{line[3:]}</h3>'
            elif line.startswith('# '):
                rendered += f'<h2 style="font-family:Lora,serif;color:#1c1917;margin:1.5rem 0 0.5rem;font-size:1.3rem">{line[2:]}</h2>'
            else:
                rendered += f'<p style="font-size:15px;color:#292524;line-height:1.9;margin:0.4rem 0">{line}</p>'

        st.markdown(f'<div class="blog-body">{rendered}</div>', unsafe_allow_html=True)

        tags = blog.get("tags", ["AI","Technology"])
        if isinstance(tags, list):
            tags_html = " ".join([f'<span class="blog-tag">#{t}</span>' for t in tags])
        else:
            tags_html = f'<span class="blog-tag">#{tags}</span>'
        st.markdown(f'<div style="margin-top:1.5rem">{tags_html}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # ── STEP 3: GENERATE EMAIL ─────────────────────────────────
        st.markdown("---")
        st.markdown("## Step 3 — Generate & Preview Email")

        email_btn = st.button("📧 Generate Email Draft", use_container_width=True)

        if email_btn:
            if not st.session_state.groq_key:
                st.error("⚠️ Please enter your Groq API key.")
            else:
                with st.spinner("📧 Formatting email..."):
                    email = generate_email(blog, recipient, sender, st.session_state.groq_key)
                    st.session_state.email_draft = email
                st.success("✅ Email draft ready!")

        if st.session_state.email_draft:
            email = st.session_state.email_draft

            st.markdown('<div class="email-preview">', unsafe_allow_html=True)
            st.markdown(f"""<div class="email-header">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
                    <span style="font-size:16px;">📮</span>
                    <span style="font-weight:600;font-size:13px">Gmail — Email Preview</span>
                </div>
                <div style="font-size:10px;color:#a8a29e">This is how your automated email will look</div>
            </div>""", unsafe_allow_html=True)

            for lab, val in [("From:", f"{sender} <newsletter@ai-weekly.com>"),
                              ("To:", f"{recipient}"),
                              ("Subject:", email.get("subject","AI Weekly Newsletter")),
                              ("Preview:", email.get("preview","")[:100])]:
                st.markdown(f'<div class="email-field"><div class="email-label">{lab}</div><div class="email-val">{val}</div></div>', unsafe_allow_html=True)

            body = email.get("body","")
            st.markdown(f'<div class="email-body-box">{body}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Download buttons
            st.markdown("<br>", unsafe_allow_html=True)
            dl1, dl2 = st.columns(2)
            with dl1:
                st.download_button("📥 Download Blog Post (.txt)",
                                   data=f"{blog.get('title','')}\n\n{blog.get('content','')}",
                                   file_name="blog_post.txt", use_container_width=True)
            with dl2:
                email_txt = f"Subject: {email.get('subject','')}\n\n{email.get('body','')}"
                st.download_button("📥 Download Email Draft (.txt)",
                                   data=email_txt,
                                   file_name="email_draft.txt", use_container_width=True)

            st.markdown("---")
            st.markdown("""
            <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;padding:1rem 1.2rem;font-size:13px;color:#14532d">
                <b>🔄 To fully automate this as a daily n8n workflow:</b><br><br>
                1. In n8n — Add <b>Schedule Trigger</b> (Cron: 0 8 * * * for 8 AM daily)<br>
                2. Add <b>HTTP Request node</b> → SerpAPI endpoint with your query<br>
                3. Add <b>Groq/OpenAI node</b> → paste the summarise + blog prompt<br>
                4. Add <b>Gmail node</b> → connect your Google account → map subject + body<br>
                5. Click <b>Activate workflow</b> → runs automatically every day!
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")
st.markdown('<p style="color:#d6d3d1; font-size:0.75rem; text-align:center;">Final Project Task 2 · AI News Auto-Blogger · Groq LLaMA 3 + SerpAPI + n8n Architecture · Streamlit</p>', unsafe_allow_html=True)
