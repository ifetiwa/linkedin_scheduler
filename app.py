#!/usr/bin/env python3
"""
LinkedIn Scheduler - Web Dashboard
A beautiful dashboard for managing posts, job applications, and analytics.
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os
import sqlite3
import requests
from datetime import datetime, date, timedelta
from pathlib import Path
import threading
import time
from scheduler import (
    POSTS, RESUME_PROFILE, generate_cover_letter,
    search_and_apply_easy_apply_jobs, LINKEDIN_TOKEN, LINKEDIN_URN,
    get_posts, save_post_override, is_published,
)

# State directory — env-overridable so prod (Render persistent disk) can
# mount writable storage outside the repo. Locally falls back to repo dir.
DATA_DIR = Path(os.getenv("DATA_DIR") or Path(__file__).parent)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# In-memory cache for external job listings (Remotive API)
_external_jobs_cache = {"data": None, "fetched_at": None}
EXTERNAL_JOBS_CACHE_TTL = timedelta(minutes=10)

# Tracker for external (Remotive / non-LinkedIn) applications
EXTERNAL_APPLIED_FILE = DATA_DIR / "external_applied_jobs.json"
_external_applied_lock = threading.Lock()


def _load_external_applied():
    if not EXTERNAL_APPLIED_FILE.exists():
        return {}
    try:
        with open(EXTERNAL_APPLIED_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_external_applied(data):
    with open(EXTERNAL_APPLIED_FILE, "w") as f:
        json.dump(data, f, indent=2)


def record_external_apply(job, cover_letter=None):
    """Record an external (Remotive) apply intent. Returns (already_applied, entry).

    If cover_letter is omitted, one is auto-generated from RESUME_PROFILE +
    the job's description so every tracked apply has a draft attached.
    """
    job_id = str(job.get("id") or f"{job.get('title','')}|{job.get('company','')}").strip().lower()
    with _external_applied_lock:
        store = _load_external_applied()
        already = job_id in store
        if not already:
            if not cover_letter:
                try:
                    cover_letter = generate_cover_letter(
                        job.get("title") or "Engineer",
                        job.get("company") or "the company",
                        job.get("description") or "",
                    )
                except Exception as e:
                    log_error(f"Cover letter draft failed: {e}", "Cover Letter Generation Error")
                    cover_letter = ""
            store[job_id] = {
                "id": job.get("id"),
                "title": job.get("title"),
                "company": job.get("company"),
                "location": job.get("location"),
                "category": job.get("category"),
                "url": job.get("url"),
                "salary": job.get("salary"),
                "tags": job.get("tags", []),
                "cover_letter": cover_letter,
                "timestamp": datetime.now().isoformat(),
            }
            _save_external_applied(store)
        return already, store[job_id]

app = Flask(__name__)
CORS(app)

# SQLite analytics DB lives on the same persistent volume as the JSON trackers
DB_PATH = DATA_DIR / "scheduler_analytics.db"

def init_db():
    """Initialize the database with required tables."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Posts table
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY,
        post_id INTEGER,
        title TEXT,
        date TEXT,
        time TEXT,
        status TEXT,
        published_at TIMESTAMP,
        views INTEGER DEFAULT 0,
        engagement INTEGER DEFAULT 0
    )''')
    
    # Jobs table
    c.execute('''CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY,
        job_id TEXT UNIQUE,
        title TEXT,
        company TEXT,
        location TEXT,
        applied_at TIMESTAMP,
        status TEXT,
        cover_letter TEXT
    )''')
    
    # Errors table
    c.execute('''CREATE TABLE IF NOT EXISTS errors (
        id INTEGER PRIMARY KEY,
        error_message TEXT,
        error_type TEXT,
        occurred_at TIMESTAMP
    )''')
    
    # Jobs Applied In Real-Time table
    c.execute('''CREATE TABLE IF NOT EXISTS jobs_live (
        id INTEGER PRIMARY KEY,
        job_id TEXT UNIQUE,
        title TEXT,
        company TEXT,
        location TEXT,
        country TEXT,
        visa_sponsorship BOOLEAN,
        applied_at TIMESTAMP,
        source TEXT
    )''')
    
    # Application runs table
    c.execute('''CREATE TABLE IF NOT EXISTS application_runs (
        id INTEGER PRIMARY KEY,
        started_at TIMESTAMP,
        ended_at TIMESTAMP,
        applications_submitted INTEGER,
        duplicates_avoided INTEGER,
        errors INTEGER
    )''')
    
    conn.commit()
    conn.close()

init_db()

# Global state for live job tracking
live_jobs_queue = []
applying_lock = threading.Lock()

# ─── External Job Search Functions ────────────────────────────────────────────

VISA_TERMS = ("visa", "sponsorship", "sponsor", "work permit", "relocate", "relocation")
TECH_KEYWORDS = (
    "engineer", "developer", "software", "fullstack", "full stack", "backend", "frontend",
    "devops", "sre", "platform", "data", "ml", "ai ", "machine learning", "security",
    "react", "node", "python", "typescript", "java ", "golang", "rust ", "infrastructure",
    "cloud", "kubernetes", "qa", "tester", "designer", "product", "tech lead", "architect",
)


def _is_tech_role(text):
    t = (text or "").lower()
    return any(k in t for k in TECH_KEYWORDS)


def fetch_external_jobs_with_visa(country="Canada", keywords=None):
    """
    Aggregate remote jobs from Remotive + Arbeitnow.
    Returns 50+ tech roles daily under normal conditions.
    """
    jobs = []
    seen = set()

    # ─── Remotive (~22/day) ───
    try:
        resp = requests.get(
            "https://remotive.com/api/remote-jobs",
            params={"limit": 100, "category": "software-dev"},
            timeout=15,
        )
        if resp.status_code == 200:
            for job in resp.json().get("jobs", []):
                jid = f"rmt_{job.get('id')}"
                if jid in seen:
                    continue
                seen.add(jid)
                desc = (job.get("description") or "")
                jobs.append({
                    "id": jid,
                    "title": job.get("title"),
                    "company": job.get("company_name"),
                    "location": job.get("candidate_required_location") or "Remote",
                    "country": country,
                    "visa_sponsorship": any(t in desc.lower() for t in VISA_TERMS),
                    "url": job.get("url"),
                    "category": job.get("category"),
                    "tags": job.get("tags", []),
                    "salary": job.get("salary"),
                    "description": desc[:600],
                    "publication_date": job.get("publication_date"),
                    "source": "Remotive",
                })
    except Exception as e:
        log_error(f"Remotive fetch failed: {e}", "External Search Error")

    # ─── Arbeitnow (~100/page, mixed roles, filter to tech) ───
    try:
        resp = requests.get("https://www.arbeitnow.com/api/job-board-api", timeout=15)
        if resp.status_code == 200:
            from datetime import datetime as _dt
            for job in resp.json().get("data", []):
                slug = job.get("slug") or ""
                jid = f"arb_{slug}"
                if jid in seen:
                    continue
                # Skip non-remote and non-tech postings
                title = job.get("title") or ""
                if not _is_tech_role(title) and not _is_tech_role(' '.join(job.get("tags", []))):
                    continue
                seen.add(jid)
                desc = (job.get("description") or "")
                created_ts = job.get("created_at")
                pub = None
                if created_ts:
                    try:
                        pub = _dt.fromtimestamp(int(created_ts)).isoformat()
                    except Exception:
                        pub = None
                jobs.append({
                    "id": jid,
                    "title": title,
                    "company": job.get("company_name"),
                    "location": job.get("location") or "Remote",
                    "country": country,
                    "visa_sponsorship": any(t in desc.lower() for t in VISA_TERMS),
                    "url": job.get("url"),
                    "category": ", ".join(job.get("job_types", []) or []),
                    "tags": job.get("tags", []),
                    "salary": None,
                    "description": (desc[:600] if desc else ""),
                    "publication_date": pub,
                    "source": "Arbeitnow",
                })
    except Exception as e:
        log_error(f"Arbeitnow fetch failed: {e}", "External Search Error")

    # Optional keyword narrowing — only narrow if it doesn't shrink below 50
    if keywords:
        kw = [k.lower() for k in keywords]
        narrowed = [j for j in jobs if any(
            k in (j.get("title") or "").lower() or
            k in (j.get("description") or "").lower()
            for k in kw
        )]
        if len(narrowed) >= 50:
            jobs = narrowed

    jobs.sort(key=lambda j: j.get("publication_date") or "", reverse=True)
    return jobs

def check_duplicate_application(title, company):
    """Check if we've already applied to this job."""
    applied_jobs_file = Path(__file__).parent / "applied_jobs.json"
    
    if not applied_jobs_file.exists():
        return False
    
    try:
        with open(applied_jobs_file, "r") as f:
            jobs = json.load(f)
        
        job_key = f"{title.lower()}|{company.lower()}"
        return job_key in jobs
    except:
        return False

def add_live_job(job_data):
    """Add a job to the live tracking queue."""
    global live_jobs_queue
    with applying_lock:
        live_jobs_queue.append({
            **job_data,
            "timestamp": datetime.now().isoformat()
        })
        # Keep only last 100 in queue
        if len(live_jobs_queue) > 100:
            live_jobs_queue.pop(0)

def get_live_jobs():
    """Get recently applied jobs from live queue."""
    global live_jobs_queue
    with applying_lock:
        return list(reversed(live_jobs_queue[:50]))  # Return last 50

# ─── Analytics & Data Functions ───────────────────────────────────────────────

def get_posts_data():
    """Get all posts (POSTS merged with user overrides) plus computed status."""
    posts_data = []
    today = date.today().isoformat()

    for post in get_posts():
        if is_published(post["id"]):
            status = "Published"
        elif post["date"] < today:
            status = "Past Due"
        elif post["date"] == today:
            status = "Today"
        else:
            status = "Scheduled"

        posts_data.append({
            "id": post["id"],
            "title": post["title"],
            "body": post.get("body", ""),
            "date": post["date"],
            "time": post["time"],
            "status": status,
            "image": post["image"],
            "hashtags": post.get("hashtags", ""),
            "first_comment": post.get("first_comment", ""),
        })

    # Sort by date+time so newly-edited dates land in the right place
    posts_data.sort(key=lambda p: (p["date"], p["time"]))
    return posts_data

def get_jobs_data():
    """Get all applied jobs from tracker."""
    applied_jobs_file = Path(__file__).parent / "applied_jobs.json"
    
    if not applied_jobs_file.exists():
        return []
    
    try:
        with open(applied_jobs_file, "r") as f:
            jobs = json.load(f)
        
        jobs_list = []
        for key, job_data in jobs.items():
            jobs_list.append({
                "title": job_data.get("title"),
                "company": job_data.get("company"),
                "location": job_data.get("location"),
                "timestamp": job_data.get("timestamp"),
                "status": "Applied"
            })
        
        return sorted(jobs_list, key=lambda x: x["timestamp"], reverse=True)
    except:
        return []

def get_analytics():
    """Get analytics data."""
    posts_data = get_posts_data()
    jobs_data = get_jobs_data()
    
    published = len([p for p in posts_data if p["status"] == "Published"])
    scheduled = len([p for p in posts_data if p["status"] in ["Scheduled", "Today"]])
    
    return {
        "total_posts": len(posts_data),
        "published_posts": published,
        "scheduled_posts": scheduled,
        "total_jobs_applied": len(jobs_data),
        "profile_name": RESUME_PROFILE["name"],
        "years_experience": RESUME_PROFILE["years_experience"]
    }

def log_error(message, error_type="General"):
    """Log an error to the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO errors (error_message, error_type, occurred_at) 
                 VALUES (?, ?, ?)''',
              (message, error_type, datetime.now()))
    conn.commit()
    conn.close()

def get_errors():
    """Get recent errors."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT error_message, error_type, occurred_at FROM errors 
                 ORDER BY occurred_at DESC LIMIT 20''')
    errors = c.fetchall()
    conn.close()
    
    return [{"message": e[0], "type": e[1], "time": e[2]} for e in errors]

# ─── API Routes ───────────────────────────────────────────────────────────────

@app.route('/')
def dashboard():
    """Render the main dashboard."""
    return render_template('dashboard.html')

@app.route('/api/posts')
def api_posts():
    """Get all posts data."""
    return jsonify(get_posts_data())

@app.route('/api/jobs')
def api_jobs():
    """Get applied jobs, optionally filtered by date range.

    Query params:
        range: today | 7d | 30d | all  (default: all)
        q:     optional substring search across title/company/location
    """
    jobs = get_jobs_data()
    date_range = (request.args.get('range') or 'all').lower()
    query = (request.args.get('q') or '').strip().lower()

    now = datetime.now()
    cutoff = None
    if date_range == 'today':
        cutoff = datetime(now.year, now.month, now.day)
    elif date_range == '7d':
        cutoff = now - timedelta(days=7)
    elif date_range == '30d':
        cutoff = now - timedelta(days=30)

    def in_range(job):
        if cutoff is None:
            return True
        ts = job.get('timestamp')
        if not ts:
            return False
        try:
            t = datetime.fromisoformat(ts.replace('Z', '+00:00').split('+')[0])
        except Exception:
            return False
        return t >= cutoff

    def matches(job):
        if not query:
            return True
        haystack = ' '.join(str(job.get(k, '')) for k in ('title', 'company', 'location')).lower()
        return query in haystack

    return jsonify([j for j in jobs if in_range(j) and matches(j)])

@app.route('/api/analytics')
def api_analytics():
    """Get analytics summary."""
    return jsonify(get_analytics())

@app.route('/api/errors')
def api_errors():
    """Get recent errors."""
    return jsonify(get_errors())

@app.route('/api/cron/apply-jobs', methods=['POST'])
def api_cron_apply_jobs():
    """Cron-triggered apply campaign. Requires CRON_SECRET env var match."""
    expected = os.getenv("CRON_SECRET")
    if not expected:
        return jsonify({"status": "error", "message": "CRON_SECRET not configured"}), 503
    body = request.json or {}
    if body.get("secret") != expected:
        return jsonify({"status": "error", "message": "invalid secret"}), 403
    count = int(body.get("count", 100))
    # Run synchronously — cron container has the time budget.
    try:
        results = search_and_apply_easy_apply_jobs(max_applications=count)
        return jsonify({
            "status": "ok",
            "applied": results.get("applied"),
            "duplicates": results.get("duplicate_avoided"),
            "errors": results.get("errors"),
        })
    except Exception as e:
        log_error(str(e), "Cron Apply Error")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/apply-jobs', methods=['POST'])
def api_apply_jobs():
    """Start job application process."""
    try:
        data = request.json
        count = data.get('count', 100)
        
        # Run in background thread
        thread = threading.Thread(target=run_job_applications, args=(count,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "status": "started",
            "message": f"Starting job applications for {count} positions",
            "count": count
        })
    except Exception as e:
        log_error(str(e), "Job Application Error")
        return jsonify({"status": "error", "message": str(e)}), 500

def run_job_applications(count):
    """Run job applications in background."""
    try:
        # Record start
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        run_id = c.execute(
            'INSERT INTO application_runs (started_at) VALUES (?)',
            (datetime.now(),)
        ).lastrowid
        conn.commit()
        conn.close()
        
        # Run applications
        results = search_and_apply_easy_apply_jobs(max_applications=count)
        
        # Add jobs to live queue and save to database
        for app in results['applications']:
            # Add to live queue for real-time display
            add_live_job({
                "job_id": app['job_id'],
                "title": app['title'],
                "company": app['company'],
                "location": app['location'],
                "country": app.get('country', 'Canada'),
                "visa_sponsorship": app.get('visa_sponsorship', False),
                "source": "LinkedIn"
            })
            
            # Save to database
            c = sqlite3.connect(DB_PATH)
            cursor = c.cursor()
            cursor.execute('''INSERT OR IGNORE INTO jobs 
                         (job_id, title, company, location, applied_at, status) 
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (app['job_id'], app['title'], app['company'], 
                       app['location'], app['timestamp'], 'Applied'))
            c.commit()
            c.close()
        
        # Record end
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''UPDATE application_runs 
                     SET ended_at=?, applications_submitted=?, duplicates_avoided=?, errors=?
                     WHERE id=?''',
                  (datetime.now(), results['applied'], results['duplicate_avoided'], 
                   results['errors'], run_id))
        conn.commit()
        conn.close()
        
    except Exception as e:
        log_error(f"Background job application error: {str(e)}", "Job Application Error")

@app.route('/api/posts/<int:post_id>', methods=['GET'])
def api_get_single_post(post_id):
    """Return the full editable record for a post (used by the edit modal)."""
    post = next((p for p in get_posts_data() if p["id"] == post_id), None)
    if not post:
        return jsonify({"status": "error", "message": "Not found"}), 404
    return jsonify(post)


@app.route('/api/posts/<int:post_id>', methods=['PUT'])
def api_update_post(post_id):
    """Persist an edited post. Fields not provided are left alone."""
    try:
        body = request.json or {}
        # Whitelist what UI can change; ignore everything else
        allowed = ("title", "body", "date", "time", "hashtags", "first_comment")
        patch = {k: body[k] for k in allowed if k in body}
        if not patch:
            return jsonify({"status": "error", "message": "No editable fields supplied"}), 400
        # Basic validation
        if "date" in patch and len(patch["date"]) != 10:
            return jsonify({"status": "error", "message": "date must be YYYY-MM-DD"}), 400
        if "time" in patch and len(patch["time"]) != 5:
            return jsonify({"status": "error", "message": "time must be HH:MM"}), 400
        # Verify the post exists in the base list
        if not any(p["id"] == post_id for p in get_posts()):
            return jsonify({"status": "error", "message": "Post not found"}), 404
        saved = save_post_override(post_id, patch)
        # Re-register the schedule so the time/date change takes effect now
        try:
            from scheduler import schedule_all
            schedule_all()
        except Exception as e:
            log_error(f"schedule_all after edit failed: {e}", "Schedule Reload Error")
        return jsonify({"status": "ok", "override": saved})
    except Exception as e:
        log_error(str(e), "Post Edit Error")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/posts/<int:post_id>/publish', methods=['POST'])
def publish_post_now(post_id):
    """Manually publish a specific post."""
    try:
        from scheduler import run_now
        run_now(post_id)
        return jsonify({"status": "success", "message": f"Post {post_id} published"})
    except Exception as e:
        log_error(str(e), "Post Publishing Error")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/cover-letter', methods=['POST'])
def generate_cover_letter_preview():
    """Generate a tailored cover letter from RESUME_PROFILE + the job's description."""
    try:
        data = request.json or {}
        job_title = data.get('job_title') or data.get('title') or 'Senior Engineer'
        company = data.get('company') or 'Tech Company'
        description = data.get('job_description') or data.get('description') or ''
        cover_letter = generate_cover_letter(job_title, company, description)
        return jsonify({
            "cover_letter": cover_letter,
            "job_title": job_title,
            "company": company,
        })
    except Exception as e:
        log_error(str(e), "Cover Letter Generation Error")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/live-jobs')
def api_live_jobs():
    """Get real-time live jobs being applied to."""
    return jsonify(get_live_jobs())

@app.route('/api/external-jobs-visa')
def api_external_jobs_visa():
    """Get remote jobs with visa sponsorship opportunities.

    Query params:
        country: Canada | USA | Australia  (default: Canada)
        visa:    true | false  (default: true — show only visa sponsorship jobs)
        applied: all | true | false  (default: all)
    """
    country = (request.args.get('country') or 'Canada').strip()
    show_visa = request.args.get('visa', 'true').lower() != 'false'
    applied_filter = (request.args.get('applied') or 'all').lower()

    jobs = fetch_external_jobs_with_visa(country=country)

    if show_visa:
        jobs = [j for j in jobs if j.get('visa_sponsorship')]

    # Annotate each job with apply state from the external tracker
    applied_store = _load_external_applied()
    applied_ids = {str(k) for k in applied_store.keys()}
    for j in jobs:
        jid = str(j.get('id'))
        j['applied'] = jid in applied_ids
        j['applied_at'] = applied_store.get(jid, {}).get('timestamp')

    if applied_filter in ('true', 'false'):
        want = applied_filter == 'true'
        jobs = [j for j in jobs if j['applied'] == want]

    return jsonify({
        "country": country,
        "visa_filter": show_visa,
        "applied_filter": applied_filter,
        "total": len(jobs),
        "applied_count": sum(1 for j in jobs if j['applied']),
        "jobs": jobs[:200]  # cap response payload but allow well over 50/day
    })

@app.route('/api/jobs/check-duplicate', methods=['POST'])
def check_duplicate():
    """Check if job application is a duplicate."""
    data = request.json
    title = data.get('title', '')
    company = data.get('company', '')
    
    is_duplicate = check_duplicate_application(title, company)
    return jsonify({
        "is_duplicate": is_duplicate,
        "title": title,
        "company": company
    })

@app.route('/api/stats')
def stats():
    """Get comprehensive stats."""
    posts_data = get_posts_data()
    jobs_data = get_jobs_data()
    live_jobs = get_live_jobs()
    
    # Group posts by status
    status_breakdown = {
        "published": len([p for p in posts_data if p["status"] == "Published"]),
        "today": len([p for p in posts_data if p["status"] == "Today"]),
        "scheduled": len([p for p in posts_data if p["status"] == "Scheduled"])
    }
    
    # Jobs by company
    companies = {}
    for job in jobs_data:
        company = job["company"]
        companies[company] = companies.get(company, 0) + 1
    
    return jsonify({
        "posts": {
            "total": len(posts_data),
            "breakdown": status_breakdown
        },
        "jobs": {
            "total": len(jobs_data),
            "live": len(live_jobs),
            "top_companies": sorted(companies.items(), key=lambda x: x[1], reverse=True)[:5]
        },
        "errors": len(get_errors())
    })

@app.route('/api/external-jobs')
def api_external_jobs():
    """Proxy and filter remote-job listings from the public Remotive API.

    Query params:
        category: software-dev | design | marketing | customer-support | ... (default: software-dev)
        q:        keyword filter (matches title / company / description tags)
        range:    today | 7d | 30d | all  (default: all) — based on publication date
        location: substring match on candidate_required_location (e.g., "Canada", "USA")
        refresh:  if "1", bypass the cache
    """
    category = (request.args.get('category') or 'software-dev').strip().lower()
    query = (request.args.get('q') or '').strip().lower()
    date_range = (request.args.get('range') or 'all').lower()
    location = (request.args.get('location') or '').strip().lower()
    force_refresh = request.args.get('refresh') == '1'

    cache_key = f"{category}"
    cached = _external_jobs_cache.get(cache_key)
    fresh = (
        cached
        and not force_refresh
        and (datetime.now() - cached['fetched_at']) < EXTERNAL_JOBS_CACHE_TTL
    )

    if not fresh:
        try:
            url = f"https://remotive.com/api/remote-jobs?category={category}&limit=100"
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            payload = resp.json()
            _external_jobs_cache[cache_key] = {
                'data': payload.get('jobs', []),
                'fetched_at': datetime.now(),
            }
        except Exception as e:
            log_error(f"Remotive fetch failed: {e}", "External Jobs Error")
            if not cached:
                return jsonify({"jobs": [], "error": str(e), "fetched_at": None}), 502

    cached = _external_jobs_cache[cache_key]
    jobs = cached['data'] or []

    now = datetime.now()
    cutoff = None
    if date_range == 'today':
        cutoff = datetime(now.year, now.month, now.day)
    elif date_range == '7d':
        cutoff = now - timedelta(days=7)
    elif date_range == '30d':
        cutoff = now - timedelta(days=30)

    def in_range(job):
        if cutoff is None:
            return True
        pub = job.get('publication_date')
        if not pub:
            return False
        try:
            t = datetime.fromisoformat(pub.replace('Z', ''))
        except Exception:
            return False
        return t >= cutoff

    def matches(job):
        if query:
            haystack = ' '.join(str(job.get(k, '')) for k in (
                'title', 'company_name', 'tags', 'job_type', 'category'
            )).lower()
            if query not in haystack:
                return False
        if location:
            loc_field = (job.get('candidate_required_location') or '').lower()
            if location not in loc_field:
                return False
        return True

    filtered = [j for j in jobs if in_range(j) and matches(j)]

    # Look up which jobs we've already applied to (Remotive tracker)
    applied_store = _load_external_applied()
    applied_ids = {str(k) for k in applied_store.keys()}

    # Trim payload to keep responses small
    slim = []
    for j in filtered:
        jid = str(j.get('id'))
        slim.append({
            'id': j.get('id'),
            'title': j.get('title'),
            'company': j.get('company_name'),
            'company_logo': j.get('company_logo'),
            'category': j.get('category'),
            'tags': j.get('tags', []),
            'job_type': j.get('job_type'),
            'location': j.get('candidate_required_location'),
            'salary': j.get('salary'),
            'url': j.get('url'),
            'publication_date': j.get('publication_date'),
            'applied': jid in applied_ids,
            'applied_at': applied_store.get(jid, {}).get('timestamp'),
        })

    # Optional filter: applied=true|false to show only one bucket
    applied_filter = request.args.get('applied')
    if applied_filter in ('true', 'false'):
        want = applied_filter == 'true'
        slim = [j for j in slim if j['applied'] == want]

    return jsonify({
        'jobs': slim,
        'fetched_at': cached['fetched_at'].isoformat() if cached['fetched_at'] else None,
        'total': len(slim),
        'applied_count': sum(1 for j in slim if j['applied']),
        'category': category,
    })


@app.route('/api/external-jobs/apply', methods=['POST'])
def api_external_jobs_apply():
    """Record that the user opened/applied to an external job. Idempotent.

    Body: { ...job fields..., cover_letter?: str }
    A cover letter is auto-drafted from RESUME_PROFILE + job description if omitted.
    """
    try:
        body = request.json or {}
        cover_letter = body.pop('cover_letter', None) if isinstance(body, dict) else None
        if not body.get('url'):
            return jsonify({"status": "error", "message": "Missing job url"}), 400
        already, entry = record_external_apply(body, cover_letter=cover_letter)
        return jsonify({
            "status": "duplicate" if already else "recorded",
            "entry": entry,
        })
    except Exception as e:
        log_error(str(e), "External Apply Error")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/external-jobs/auto-apply', methods=['POST'])
def api_external_jobs_auto_apply():
    """Auto-apply to N external jobs in one call.

    For each job we (a) draft a cover letter from RESUME_PROFILE + description,
    (b) record it in the applied tracker. The frontend is responsible for
    opening each job's URL in a tab — auto-submission to arbitrary ATSes
    isn't safe to do server-side without per-vendor integration.

    Body: { jobs: [...job objects...] }
    """
    try:
        body = request.json or {}
        jobs = body.get('jobs') or []
        results = []
        recorded = 0
        for job in jobs:
            if not job.get('url'):
                results.append({"id": job.get('id'), "status": "skipped", "reason": "no url"})
                continue
            already, entry = record_external_apply(job)
            results.append({
                "id": job.get('id'),
                "status": "duplicate" if already else "recorded",
                "url": entry.get('url'),
                "cover_letter_preview": (entry.get('cover_letter') or '')[:160],
            })
            if not already:
                recorded += 1
        return jsonify({"recorded": recorded, "total": len(jobs), "results": results})
    except Exception as e:
        log_error(str(e), "External Auto-Apply Error")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/external-jobs/applied/<job_id>/cover-letter')
def api_external_cover_letter_get(job_id):
    """Read the saved cover letter for an applied external job."""
    store = _load_external_applied()
    entry = store.get(str(job_id).strip().lower())
    if not entry:
        return jsonify({"status": "not_found"}), 404
    return jsonify({
        "job_id": job_id,
        "title": entry.get('title'),
        "company": entry.get('company'),
        "cover_letter": entry.get('cover_letter') or '',
    })


@app.route('/api/external-jobs/applied')
def api_external_jobs_applied():
    """List external jobs the user has applied to, with same filters as LinkedIn applied list.

    Query params:
        range: today | 7d | 30d | all  (default: all)
        q:     substring search on title/company/category
    """
    store = _load_external_applied()
    rows = list(store.values())

    date_range = (request.args.get('range') or 'all').lower()
    query = (request.args.get('q') or '').strip().lower()

    now = datetime.now()
    cutoff = None
    if date_range == 'today':
        cutoff = datetime(now.year, now.month, now.day)
    elif date_range == '7d':
        cutoff = now - timedelta(days=7)
    elif date_range == '30d':
        cutoff = now - timedelta(days=30)

    def in_range(job):
        if cutoff is None:
            return True
        ts = job.get('timestamp')
        if not ts:
            return False
        try:
            t = datetime.fromisoformat(ts.split('+')[0].replace('Z', ''))
        except Exception:
            return False
        return t >= cutoff

    def matches(job):
        if not query:
            return True
        haystack = ' '.join(str(job.get(k, '')) for k in ('title', 'company', 'category', 'location')).lower()
        return query in haystack

    rows = [r for r in rows if in_range(r) and matches(r)]
    rows.sort(key=lambda r: r.get('timestamp', ''), reverse=True)
    return jsonify(rows)


@app.route('/api/external-jobs/applied/<job_id>', methods=['DELETE'])
def api_external_jobs_unapply(job_id):
    """Remove an external job from the applied tracker (un-apply / mistake undo)."""
    with _external_applied_lock:
        store = _load_external_applied()
        key = str(job_id).strip().lower()
        if key in store:
            del store[key]
            _save_external_applied(store)
            return jsonify({"status": "removed"})
    return jsonify({"status": "not_found"}), 404


@app.route('/api/external-jobs/categories')
def api_external_jobs_categories():
    """Return a curated list of Remotive categories matching our LinkedIn targeting."""
    return jsonify([
        {"slug": "software-dev", "label": "Software Development"},
        {"slug": "data", "label": "Data"},
        {"slug": "devops", "label": "DevOps / Sysadmin"},
        {"slug": "design", "label": "Design"},
        {"slug": "product", "label": "Product"},
        {"slug": "qa", "label": "QA"},
        {"slug": "marketing", "label": "Marketing"},
        {"slug": "sales", "label": "Sales / Business"},
        {"slug": "customer-support", "label": "Customer Support"},
        {"slug": "all-others", "label": "All Others"},
    ])


@app.route('/api/posts/refresh')
def api_posts_refresh():
    """Return the current posts list with a fresh status computation."""
    return jsonify({"status": "success", "posts": get_posts_data()})


# ─── Content Generation APIs ──────────────────────────────────────
@app.route('/api/generate-blog', methods=['POST'])
def api_generate_blog():
    """Generate a blog post using AI."""
    try:
        data = request.json
        topic = data.get('topic', '').strip()
        tone = data.get('tone', 'professional')
        length = data.get('length', 'medium')
        
        if not topic:
            return jsonify({"status": "error", "message": "Topic required"}), 400
        
        # Generate blog content using simple AI prompt
        # In production, you'd use OpenAI, Claude, or similar
        blog_content = generate_ai_blog(topic, tone, length)
        
        return jsonify({
            "status": "success",
            "content": blog_content,
            "summary": f"Blog post about {topic} ({tone} tone)"
        })
    except Exception as e:
        log_error(str(e), "Blog Generation Error")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/generate-image', methods=['POST'])
def api_generate_image():
    """Generate an image using AI."""
    try:
        data = request.json
        desc = data.get('desc', '').strip()
        style = data.get('style', 'professional')
        ratio = data.get('ratio', '16:9')
        
        if not desc:
            return jsonify({"status": "error", "message": "Description required"}), 400
        
        # Generate image URL (using Unsplash or similar API)
        # In production, you'd use DALL-E, Midjourney, or similar
        image_url = generate_ai_image(desc, style, ratio)
        
        return jsonify({
            "status": "success",
            "url": image_url,
            "prompt": f"{desc} ({style} style, {ratio})"
        })
    except Exception as e:
        log_error(str(e), "Image Generation Error")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/schedule-post', methods=['POST'])
def api_schedule_post():
    """Schedule a new post to LinkedIn."""
    try:
        data = request.json
        date_str = data.get('date')
        time_str = data.get('time')
        caption = data.get('caption', '').strip()
        hashtags = data.get('hashtags', '').strip()
        
        if not all([date_str, time_str, caption]):
            return jsonify({"status": "error", "message": "Date, time, and caption required"}), 400
        
        # Parse datetime
        dt_str = f"{date_str}T{time_str}:00"
        scheduled_time = datetime.fromisoformat(dt_str)
        
        # Create new post entry
        new_post = {
            "id": len(POSTS) + 1,
            "title": caption[:50],
            "date": date_str,
            "time": time_str,
            "body": caption,
            "hashtags": hashtags.split() if hashtags else [],
            "cta": "Check it out →",
            "image": "/static/images/linkedin-banner.png",
            "status": "Scheduled"
        }
        
        # Save to database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO posts 
                     (post_id, title, date, time, status, published_at) 
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (new_post['id'], new_post['title'], date_str, time_str, 'Scheduled', None))
        conn.commit()
        conn.close()
        
        return jsonify({
            "status": "success",
            "post_id": new_post['id'],
            "scheduled_for": scheduled_time.isoformat()
        })
    except Exception as e:
        log_error(str(e), "Post Scheduling Error")
        return jsonify({"status": "error", "message": str(e)}), 500


# ─── AI Content Helpers ────────────────────────────────────────────
def generate_ai_blog(topic, tone, length):
    """Generate blog content. In production, call OpenAI or Claude."""
    lengths = {"short": 500, "medium": 1000, "long": 1500}
    word_count = lengths.get(length, 1000)
    
    tones = {
        "professional": "Write in a professional and formal tone",
        "casual": "Write in a casual and conversational tone",
        "technical": "Write in a technical and detailed tone",
        "inspirational": "Write in an inspirational and motivational tone"
    }
    tone_desc = tones.get(tone, "Write in a professional tone")
    
    # Simple template-based generation (replace with real API call)
    blog = f"""
# {topic.title()}

{tone_desc}. Here are some key insights about {topic}:

## Introduction
This article explores {topic} in depth. We'll cover various aspects and provide practical insights you can use immediately.

## Main Points

### Point 1: Understanding the Basics
{topic} is a fascinating subject that has gained significant attention recently. Understanding the fundamentals is crucial for success.

### Point 2: Best Practices
When working with {topic}, follow these best practices:
- Focus on quality over quantity
- Keep learning and adapting
- Engage with the community
- Document your progress

### Point 3: Advanced Techniques
Once you understand the basics, you can explore more advanced approaches to {topic}. This involves:
- Deep technical knowledge
- Creative problem-solving
- Continuous experimentation
- Sharing your knowledge with others

## Conclusion
{topic} is constantly evolving, and staying updated is essential. Keep practicing, learning, and sharing your experience with the community.

---

*This article contains approximately {word_count} words and is written in a {tone} tone.*
"""
    return blog.strip()


def generate_ai_image(description, style, ratio):
    """Generate image URL. In production, call DALL-E, Midjourney, or use Unsplash."""
    # For now, return a placeholder gradient image using a service
    # In production, use: OpenAI DALL-E, Midjourney API, or Unsplash API
    
    # Example using Unsplash API (requires API key)
    # You can replace this with actual image generation
    
    # For demo purposes, return a data URI with gradient
    return f"https://via.placeholder.com/{get_ratio_dimensions(ratio)}?text={description[:20]}"


def get_ratio_dimensions(ratio):
    """Convert ratio to standard dimensions."""
    ratios = {
        "1:1": "400x400",
        "16:9": "800x450",
        "4:3": "800x600"
    }
    return ratios.get(ratio, "800x450")


def _start_scheduler_thread():
    """Boot the in-process post-publishing loop.

    Disabled by default (off in dev so debug-reload doesn't double-publish).
    Enable in production by setting ENABLE_SCHEDULER=1 *and* running gunicorn
    with -w 1 so only one process owns the schedule.
    """
    if os.getenv("ENABLE_SCHEDULER", "0") != "1":
        return
    try:
        import schedule as _schedule
        from scheduler import schedule_all as _schedule_all
        _schedule_all()
    except Exception as e:
        log_error(f"Scheduler boot failed: {e}", "Scheduler Boot Error")
        return

    def _loop():
        while True:
            try:
                _schedule.run_pending()
            except Exception as e:
                log_error(f"Scheduler tick failed: {e}", "Scheduler Tick Error")
            time.sleep(30)

    t = threading.Thread(target=_loop, daemon=True, name="scheduler-loop")
    t.start()


# Run on import so gunicorn workers spin up the scheduler too (only worker 0
# should be configured to enable it — see DEPLOY.md / render.yaml).
_start_scheduler_thread()


if __name__ == '__main__':
    # Local dev — bind to 0.0.0.0 so it's reachable from other devices on the LAN.
    # Production (Render) uses gunicorn via render.yaml startCommand.
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
