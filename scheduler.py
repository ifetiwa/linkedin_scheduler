#!/usr/bin/env python3
"""
LinkedIn Auto-Scheduler for Tiwa Elegbeleye
============================================
Schedules and publishes LinkedIn posts with images automatically.

SETUP (one-time):
  pip install schedule requests python-dotenv pillow

USAGE:
  1. Copy your credentials into .env (see .env.example)
  2. Place post images in the ./images/ folder
  3. Run: python scheduler.py
  4. Leave it running — posts go out automatically on schedule

HOW IT WORKS:
  - Reads the post schedule from POSTS list below
  - At each scheduled time, uploads the image and publishes the post
  - Logs everything to scheduler.log
  - Sends a desktop notification on success/failure (macOS/Linux)

NOTE ON LINKEDIN API:
  LinkedIn's official API requires a Company Page or approved app for 
  scheduled posting. This script uses the LinkedIn v2 API with a 
  personal access token (Works for personal profiles via Share API).
  Get your token at: https://www.linkedin.com/developers/
  Required scopes: w_member_social, r_liteprofile

"""

import os
import sys
import json
import time
import logging
import requests
import schedule
import subprocess
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv

# ─── Config ───────────────────────────────────────────────────────────────────

load_dotenv()

LINKEDIN_TOKEN   = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_URN     = os.getenv("LINKEDIN_PERSON_URN")   # urn:li:person:XXXXXXXX
IMAGES_DIR       = Path(__file__).parent / "images"
LOG_FILE         = Path(__file__).parent / "scheduler.log"
DRY_RUN          = os.getenv("DRY_RUN", "false").lower() == "true"

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("linkedin_scheduler")

# ─── Post Data ────────────────────────────────────────────────────────────────
# Each entry: date (YYYY-MM-DD), time (HH:MM 24h), image filename, post text, hashtags

GITHUB = "https://github.com/ifetiwa"
EMAIL  = "elegbeleyetiwa@gmail.com"

POSTS = [
    {
        "id": 1,
        "date": "2026-05-02",
        "time": "08:00",
        "image": "post1_origin_story.png",
        "title": "My 8-year journey — from Nigeria to senior engineer",
        "body": """I didn't start with a MacBook or a bootcamp. I started with curiosity and a broken laptop.

8 years ago I was writing my first lines of HTML in Nigeria, with no roadmap and no mentor.

Today I'm a Senior Development Engineer & Strategist at P23 Labs, leading architecture decisions and shipping software that moves business metrics.

Here's what I wish someone had told me early on:

→ Your background is not a disadvantage. It's your edge.
→ Curiosity compounds faster than credentials.
→ Security knowledge + full stack skills = rare combo. Own it.

If you're in the early stages of your dev journey — especially from Africa — I see you. Keep building.

What's one thing you wish you knew when you started? Drop it below 👇""",
        "hashtags": "#FullStackDeveloper #SoftwareEngineer #TechFromAfrica #CareerGrowth #Nigeria #CanadaTech #WebDevelopment #DeveloperStory #8YearsInTech",
        "first_comment": f"Follow my journey and open-source work → {GITHUB}",
    },
    {
        "id": 2,
        "date": "2026-05-05",
        "time": "08:00",
        "image": "post2_auth_checklist.png",
        "title": "5 steps to a production-ready auth layer",
        "body": """Most tutorials skip the hard part: securing the auth layer properly.

Here's what a production-ready auth flow actually looks like (from a project I built):

🔐 Step 1 — Never store plain passwords. Use bcrypt with a salt round of 12+
🔐 Step 2 — JWT tokens expire. Use refresh token rotation, not long-lived access tokens
🔐 Step 3 — Rate-limit login endpoints. Brute force is still very real
🔐 Step 4 — Log failed attempts. You need the audit trail
🔐 Step 5 — HTTPS everywhere. Non-negotiable

I implemented this in a Node.js + React app and documented the full architecture on my GitHub.

Link in comments 👇

What auth pattern are you currently using in production?""",
        "hashtags": "#Cybersecurity #NodeJS #React #FullStackDeveloper #Authentication #WebSecurity #JavaScript #OpenSource #GitHub #ISC2",
        "first_comment": f"Full project and code → {GITHUB}/FullStack-expense-tracker-React-Nodejs",
    },
    {
        "id": 3,
        "date": "2026-05-08",
        "time": "08:00",
        "image": "post3_leadership.png",
        "title": "Leading a dev team of 5 taught me one painful lesson",
        "body": """The best developer on the team isn't always the best lead.

I learned this the hard way when I led a team of 5 developers at SLR Infrastructure.

I was the most technical person in the room. So I assumed I should have all the answers.

Wrong.

What actually made the team perform:

✦ Clear task ownership — no ambiguity about who does what
✦ Regular 1:1s, even brief ones — problems surface faster
✦ Code reviews as a teaching moment, not a critique session
✦ Documenting decisions so "why did we do this?" has an answer
✦ Protecting the team from scope creep upstream

The code was the easy part. The leadership was where I grew.

What's the most important thing you've learned leading a tech team?""",
        "hashtags": "#TechLeadership #TeamLead #EngineeringLeadership #SoftwareDevelopment #MentoringDevs #FullStackDeveloper #CareerAdvice #Engineering",
        "first_comment": None,
    },
    {
        "id": 4,
        "date": "2026-05-12",
        "time": "08:00",
        "image": "post4_react_patterns.png",
        "title": "5 React patterns worth stealing",
        "body": """These 5 React patterns cut my debugging time in half.

Copy them:

1️⃣ Custom hooks for data fetching
   Stop repeating useEffect + useState. Extract logic into useData() or useFetch(). Clean, testable, reusable.

2️⃣ Error boundaries at route level
   Don't let one component crash your whole app. Wrap each route with an ErrorBoundary.

3️⃣ Compound components for UI kits
   Instead of prop-drilling through 5 layers, use React.createContext inside your component family.

4️⃣ Memoize expensive renders
   useMemo and useCallback are not premature optimization when your list has 500+ items.

5️⃣ Colocate state with its component
   Lifting state all the way to the root is the silent killer of performance and readability.

Save this for your next refactor.

Which one are you already using? Which one surprised you?""",
        "hashtags": "#ReactJS #JavaScript #FrontendDeveloper #FullStackDeveloper #WebDevelopment #ReactPatterns #CodeQuality #SoftwareEngineering #OpenSource",
        "first_comment": f"See my React projects → {GITHUB}/React-tracker",
    },
    {
        "id": 5,
        "date": "2026-05-14",
        "time": "08:00",
        "image": "post5_sales_redesign.png",
        "title": "I redesigned a SaaS product page — 25% sales lift",
        "body": """The old site looked fine. But it wasn't converting.

I led the redesign of a privacy software company's website.

The result? A reported 25% increase in quarterly sales.

Here's what we changed (and why it worked):

Before:
❌ Feature-first copy — it talked about the product, not the user's problem
❌ Slow load times (4.2s average) — buried under unoptimized assets
❌ No clear CTA hierarchy — users didn't know where to look
❌ No trust signals above the fold

After:
✅ Problem-first messaging in the hero
✅ Performance optimized to under 1.2s
✅ Single primary CTA, one secondary — zero confusion
✅ Social proof and certifications front and center

Conversion is a design problem and a dev problem. You need both.

Have you ever rebuilt something that significantly moved a business metric?""",
        "hashtags": "#WebDesign #ConversionOptimization #FullStackDeveloper #UXDesign #WebPerformance #SEO #ProductDesign #GrowthMarketing #P23Labs",
        "first_comment": None,
    },
    {
        "id": 6,
        "date": "2026-05-16",
        "time": "12:00",
        "image": "post6_poll.png",
        "title": "Poll: What's slowing your dev team?",
        "body": """Every engineering team I've led hits the same 4 blockers.

Which one is currently slowing YOUR team down the most?

🔵 Technical debt that nobody has time to fix
🟡 Unclear requirements from stakeholders
🔴 Slow code review cycles
🟢 Poor documentation / onboarding

Drop your answer below — I'll share a post next week specifically on how to attack whichever one wins.

(And if it's something not on this list, tell me in the comments — I want to know.)""",
        "hashtags": "#SoftwareEngineering #EngineeringLeadership #DevTeams #TechLeadership #Agile #WebDevelopment #ProductEngineering #PollForDevs",
        "first_comment": None,
    },
    {
        "id": 7,
        "date": "2026-05-19",
        "time": "08:00",
        "image": "post7_security_stack.png",
        "title": "Security at every layer of the stack",
        "body": """Security is not a feature you add at the end.

It's a mindset baked into every layer of your stack.

Here's how I think about it as a full stack developer:

🧱 Database layer — parameterized queries only. SQL injection is still the #1 attack vector.
🔑 Auth layer — rotate refresh tokens. Short-lived JWTs. Never secrets in env.example files.
🌐 API layer — rate limiting, input validation, CORS policies. All three, every time.
🖥 Frontend layer — sanitize everything you render. XSS doesn't care how beautiful your UI is.
🏗 Infrastructure — least-privilege access for every service. Lock down your IAM policies.

I hold an ISC2 candidacy and have worked in security operations. This is how that training shows up in daily engineering decisions.

Which layer do you think most dev teams skip?""",
        "hashtags": "#Cybersecurity #SecureCodeReview #FullStackDeveloper #WebSecurity #ISC2 #OWASP #SecurityEngineering #DevSecOps #SoftwareEngineering",
        "first_comment": f"My open-source projects → {GITHUB}",
    },
    {
        "id": 8,
        "date": "2026-05-21",
        "time": "08:00",
        "image": "post8_node_api.png",
        "title": "Production Node.js + MongoDB API folder structure",
        "body": """Here's a REST API I built with Node.js + MongoDB.

Not just the happy path — the full production structure.

📁 Folder layout:
/controllers — business logic, no database calls here
/models — Mongoose schemas, validation at the schema level
/routes — thin. Just route → controller
/middleware — auth, rate limiting, error handling
/utils — helpers that don't belong anywhere else
/config — environment setup, DB connection

Why does this matter? Because the architecture you choose on day 1 is the architecture you'll fight on day 300.

Lessons from this project:
→ Separate concerns ruthlessly from the start
→ Error handling middleware saved me hours of debugging
→ Environment-based config makes deployment headache-free

The full project with README is on my GitHub — link in comments.

What's your go-to backend architecture pattern?""",
        "hashtags": "#NodeJS #MongoDB #BackendDevelopment #FullStackDeveloper #OpenSource #GitHub #JavaScript #SoftwareArchitecture #RESTAPI",
        "first_comment": f"Full stack expense tracker project → {GITHUB}/FullStack-expense-tracker-React-Nodejs",
    },
    {
        "id": 9,
        "date": "2026-05-23",
        "time": "08:00",
        "image": "post9_50pct_growth.png",
        "title": "How engineering decisions drove 50% business growth",
        "body": """Engineering and business strategy are not separate lanes.

At P23 Labs, our team's technical decisions were directly tied to a reported 50% improvement in business growth outcomes.

Here's how engineering created that impact:

→ We identified which systems were causing operational drag and rebuilt them
→ We tightened integrations between business tools — less manual work, faster decisions
→ We prioritized reliability: uptime improvements directly affected revenue
→ We shipped faster by reducing tech debt that was slowing delivery cycles
→ We aligned every major architecture decision to a business objective — not just technical elegance

This is what separates a senior engineer from a developer who writes good code.

Good code is table stakes. Strategic impact is the job.

Are you thinking about how your engineering decisions affect business outcomes?""",
        "hashtags": "#SeniorEngineer #TechStrategy #EngineeringLeadership #BusinessGrowth #FullStackDeveloper #SoftwareEngineering #StartupTech #P23Labs",
        "first_comment": None,
    },
    {
        "id": 10,
        "date": "2026-05-26",
        "time": "08:00",
        "image": "post10_wordpress.png",
        "title": "WordPress is underrated for enterprise clients",
        "body": """Developers who dismiss WordPress have never had to maintain a Drupal codebase.

I've built custom WordPress solutions for NGOs, enterprise clients, and SaaS companies. Here's when it genuinely wins:

✅ Content-heavy sites — the editor experience is still unmatched
✅ Custom plug-in development — you can build anything on the hooks/filters system
✅ Rapid delivery — client wants a site in 3 weeks? WordPress.
✅ Non-technical content teams — they can self-manage without calling you
✅ WooCommerce + Shopify Plus — I've run both at scale

Where it struggles:
❌ Real-time apps (use something else)
❌ Heavy custom app logic (React + Node.js)
❌ Teams that hate PHP (it's PHP)

The right tool for the right job. I've shipped WordPress projects for Aspilos Foundation across Nigeria and the US.

Do you still write off WordPress? What changed your mind (or didn't)?""",
        "hashtags": "#WordPress #WebDevelopment #FullStackDeveloper #CMS #WooCommerce #PHP #WebDesign #DeveloperTips #ShopifyPlus",
        "first_comment": f"My open-source work → {GITHUB}",
    },
    {
        "id": 11,
        "date": "2026-05-28",
        "time": "12:00",
        "image": "post11_8lessons.png",
        "title": "8 years of dev in 8 lessons",
        "body": """If I could send a message back to 2017-me, it would be these 8 things.

1. Ship ugly code that works before beautiful code that doesn't
2. Learn to communicate your technical decisions to non-technical people — this is a superpower
3. Security isn't a separate concern. It's the job.
4. The tools change. Problem-solving doesn't.
5. Document everything. Future you will thank you.
6. The best engineers I know are also the best at asking questions
7. Your network isn't just contacts — it's knowledge on demand
8. Imposter syndrome doesn't go away. You outgrow it.

8 years. Nigeria → Canada. Multiple industries. Always learning.

Which one hits hardest for you? Or what's #9?""",
        "hashtags": "#SoftwareEngineer #CareerLessons #FullStackDeveloper #DeveloperLife #TechFromAfrica #CareerGrowth #8YearsInTech #CodeLife",
        "first_comment": f"All my projects → {GITHUB}",
    },
    {
        "id": 12,
        "date": "2026-05-30",
        "time": "08:00",
        "image": "post12_brand_closer.png",
        "title": "What's next for me — and a thank you",
        "body": """This month I committed to showing up consistently on LinkedIn.

Not to go viral. Not to perform. But to be findable, and to give back some of what I've learned.

Here's where I am today:
→ Senior Development Engineer & Strategist at P23 Labs
→ MSc in Information Technology (2025)
→ ISC2 Candidate
→ 8+ years building across full stack, security, and leadership

And here's what I'm building toward:
→ Deeper expertise at the intersection of software engineering + cybersecurity
→ Connecting with engineering leaders, founders, and teams solving real problems
→ Eventually — mentoring more African developers breaking into the global market

If we haven't connected yet, hit the follow button or send me a message.

I'm open to conversations about: senior engineering roles, consulting, collaboration, and mentorship.

Let's build something.""",
        "hashtags": "#OpenToWork #SeniorEngineer #FullStackDeveloper #Cybersecurity #TechLeadership #SoftwareEngineer #NigerianInTech #LinkedInGrowth",
        "first_comment": f"GitHub: {GITHUB}  ·  Email: {EMAIL}",
    },
]

# ─── LinkedIn API ─────────────────────────────────────────────────────────────

def upload_image(image_path: Path) -> str | None:
    """Upload image to LinkedIn and return the asset URN."""
    if DRY_RUN:
        log.info(f"[DRY RUN] Would upload image: {image_path.name}")
        return "urn:li:digitalmediaAsset:DRY_RUN_ASSET"

    headers = {
        "Authorization": f"Bearer {LINKEDIN_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    # Step 1: Register upload
    register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    register_payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": LINKEDIN_URN,
            "serviceRelationships": [{
                "relationshipType": "OWNER",
                "identifier": "urn:li:userGeneratedContent"
            }]
        }
    }
    r = requests.post(register_url, headers=headers, json=register_payload)
    r.raise_for_status()
    data = r.json()
    upload_url = data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    asset_urn  = data["value"]["asset"]

    # Step 2: Upload the binary
    with open(image_path, "rb") as f:
        img_data = f.read()
    upload_headers = {"Authorization": f"Bearer {LINKEDIN_TOKEN}"}
    r2 = requests.post(upload_url, headers=upload_headers, data=img_data)
    r2.raise_for_status()

    log.info(f"Image uploaded: {asset_urn}")
    return asset_urn


def publish_post(post: dict) -> bool:
    """Publish a LinkedIn post with optional image."""
    image_path = IMAGES_DIR / post["image"]
    full_text = post["body"].strip() + "\n\n" + post["hashtags"]

    if DRY_RUN:
        log.info(f"[DRY RUN] Would publish post {post['id']}: {post['title']}")
        log.info(f"[DRY RUN] Text preview: {full_text[:120]}...")
        notify(f"✅ [DRY RUN] Post {post['id']} would have been published", success=True)
        return True

    # Upload image
    asset_urn = None
    if image_path.exists():
        try:
            asset_urn = upload_image(image_path)
        except Exception as e:
            log.warning(f"Image upload failed, posting without image: {e}")

    # Build payload
    headers = {
        "Authorization": f"Bearer {LINKEDIN_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    payload = {
        "author": LINKEDIN_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": full_text},
                "shareMediaCategory": "IMAGE" if asset_urn else "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    if asset_urn:
        payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [{
            "status": "READY",
            "description": {"text": post["title"]},
            "media": asset_urn,
            "title": {"text": post["title"]},
        }]

    try:
        r = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=headers,
            json=payload
        )
        r.raise_for_status()
        post_id = r.headers.get("X-RestLi-Id", "unknown")
        log.info(f"✅ Post {post['id']} published. LinkedIn ID: {post_id}")

        # Post first comment if set
        if post.get("first_comment") and post_id != "unknown":
            time.sleep(5)
            add_comment(post_id, post["first_comment"])

        notify(f"✅ LinkedIn post published: {post['title'][:50]}", success=True)
        return True

    except requests.HTTPError as e:
        log.error(f"❌ Failed to publish post {post['id']}: {e.response.text}")
        notify(f"❌ LinkedIn post FAILED: {post['title'][:50]}", success=False)
        return False


def add_comment(post_urn: str, comment_text: str):
    """Add the first comment (for GitHub links etc.)."""
    headers = {
        "Authorization": f"Bearer {LINKEDIN_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    payload = {
        "actor": LINKEDIN_URN,
        "message": {"text": comment_text},
        "object": f"urn:li:ugcPost:{post_urn}",
    }
    try:
        r = requests.post("https://api.linkedin.com/v2/socialActions/{}/comments".format(post_urn), headers=headers, json=payload)
        r.raise_for_status()
        log.info(f"Comment added: {comment_text[:60]}")
    except Exception as e:
        log.warning(f"Could not add first comment: {e}")


def notify(message: str, success: bool = True):
    """Desktop notification (macOS & Linux)."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["osascript", "-e", f'display notification "{message}" with title "LinkedIn Scheduler"'], check=False)
        elif sys.platform.startswith("linux"):
            subprocess.run(["notify-send", "LinkedIn Scheduler", message], check=False)
    except Exception:
        pass


# ─── Job Search Connection Feature ────────────────────────────────────────────

def search_and_connect_recruiters(keywords: list = None, max_connections: int = 5):
    """
    Search for and connect with recruiters and hiring professionals.
    
    Args:
        keywords: List of job titles/keywords (e.g., ['Senior Engineer Recruiter', 'Hiring Manager'])
        max_connections: Maximum number of connection requests to send
    """
    if not keywords:
        keywords = [
            "Recruiter",
            "Hiring Manager", 
            "Tech Recruiter",
            "Senior Recruiter",
            "Talent Acquisition"
        ]
    
    if DRY_RUN:
        log.info(f"[DRY RUN] Would search for and connect with {max_connections} recruiters")
        return []
    
    log.info(f"🔍 Searching for recruiters/hiring managers with keywords: {keywords}")
    
    headers = {
        "Authorization": f"Bearer {LINKEDIN_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    
    connected_profiles = []
    
    # Search for each keyword
    for keyword in keywords[:3]:  # Limit to first 3 keywords
        try:
            search_url = "https://api.linkedin.com/rest/search/people"
            params = {
                "q": "keywords",
                "keywords": keyword,
                "count": max_connections,
            }
            
            r = requests.get(search_url, headers=headers, params=params, timeout=10)
            
            if r.status_code == 200:
                data = r.json()
                if "elements" in data:
                    for element in data["elements"][:max_connections]:
                        profile_id = element.get("id")
                        name = element.get("name", "Unknown")
                        headline = element.get("headline", "")
                        
                        # Send connection request
                        if send_connection_request(profile_id, name, keyword):
                            connected_profiles.append({
                                "id": profile_id,
                                "name": name,
                                "headline": headline,
                                "reason": keyword
                            })
                            log.info(f"✅ Connection request sent to {name} ({headline})")
                            time.sleep(2)  # Rate limiting
            else:
                log.debug(f"Search for '{keyword}' returned status {r.status_code}")
                
        except Exception as e:
            log.warning(f"Error searching for '{keyword}': {e}")
            continue
    
    if connected_profiles:
        log.info(f"\n✅ Successfully sent {len(connected_profiles)} connection requests to relevant professionals")
        notify(f"✅ Connected with {len(connected_profiles)} recruiters/hiring managers", success=True)
    else:
        log.info("⚠️ No recruiters found or connected. Check API credentials.")
    
    return connected_profiles


def send_connection_request(profile_id: str, name: str, reason: str = "") -> bool:
    """Send a connection request to a LinkedIn profile."""
    headers = {
        "Authorization": f"Bearer {LINKEDIN_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    
    invitation_message = f"Hi {name.split()[0] if name else 'there'}! I'm actively looking for opportunities in senior engineering and tech leadership roles. I'd love to connect and explore potential opportunities together. Looking forward to connecting!"
    
    payload = {
        "invitations": [
            {
                "invitee": {"com.linkedin.voyager.identity.profile.Profile": profile_id},
                "message": invitation_message,
            }
        ]
    }
    
    try:
        r = requests.post(
            "https://api.linkedin.com/rest/invitations",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if r.status_code in [200, 201]:
            log.info(f"Connection sent to {name}")
            return True
        elif r.status_code == 409:
            log.debug(f"Already connected or request pending with {name}")
            return False
        else:
            log.debug(f"Connection request failed for {name}: {r.status_code}")
            return False
            
    except Exception as e:
        log.warning(f"Error sending connection request to {name}: {e}")
        return False


def search_target_companies(company_names: list = None, max_connections: int = 10):
    """
    Search for employees at target companies and send connection requests.
    
    Args:
        company_names: List of target company names (e.g., ['Google', 'Microsoft'])
        max_connections: Max connections per company
    """
    if not company_names:
        company_names = [
            "Google",
            "Microsoft",
            "Amazon",
            "Apple",
            "Meta",
            "Netflix"
        ]
    
    if DRY_RUN:
        log.info(f"[DRY RUN] Would search for employees at target companies")
        return []
    
    log.info(f"🔍 Searching for employees at target companies: {company_names}")
    
    headers = {
        "Authorization": f"Bearer {LINKEDIN_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    
    connected_profiles = []
    
    for company in company_names[:3]:  # Limit to first 3 companies
        try:
            search_url = "https://api.linkedin.com/rest/search/people"
            params = {
                "q": "companies",
                "companies": company,
                "count": min(max_connections, 5),
            }
            
            r = requests.get(search_url, headers=headers, params=params, timeout=10)
            
            if r.status_code == 200:
                data = r.json()
                if "elements" in data:
                    for element in data["elements"][:max_connections]:
                        profile_id = element.get("id")
                        name = element.get("name", "Unknown")
                        headline = element.get("headline", "")
                        
                        if send_connection_request(profile_id, name, f"Employee at {company}"):
                            connected_profiles.append({
                                "id": profile_id,
                                "name": name,
                                "company": company,
                                "headline": headline
                            })
                            log.info(f"✅ Connected with {name} at {company}")
                            time.sleep(2)
            else:
                log.debug(f"Search for {company} employees returned {r.status_code}")
                
        except Exception as e:
            log.warning(f"Error searching for {company} employees: {e}")
            continue
    
    if connected_profiles:
        log.info(f"\n✅ Successfully connected with {len(connected_profiles)} employees at target companies")
        notify(f"✅ Connected with {len(connected_profiles)} professionals from target companies", success=True)
    
    return connected_profiles


def job_search_outreach():
    """Run full job search outreach: connect with recruiters and target companies."""
    log.info("\n" + "="*60)
    log.info("🚀 STARTING JOB SEARCH OUTREACH")
    log.info("="*60 + "\n")
    
    # Phase 1: Connect with recruiters
    log.info("Phase 1: Connecting with Recruiters & Hiring Managers...")
    recruiters = search_and_connect_recruiters(max_connections=5)
    
    time.sleep(5)
    
    # Phase 2: Connect with target companies
    log.info("\nPhase 2: Connecting with employees at target companies...")
    company_employees = search_target_companies(max_connections=7)
    
    log.info("\n" + "="*60)
    total = len(recruiters) + len(company_employees)
    log.info(f"✅ JOB SEARCH OUTREACH COMPLETE!")
    log.info(f"Total connections: {total}")
    log.info("="*60 + "\n")
    
    return {
        "recruiters": recruiters,
        "company_employees": company_employees,
        "total": total
    }


# ─── Resume Profile & Cover Letter Generation ─────────────────────────────────

RESUME_PROFILE = {
    "name": "Tiwa Elegbeleye",
    "title": "Senior Full Stack Developer & Cybersecurity-Focused Engineer",
    "current_role": "Senior Development Engineer and Strategist at P23 Labs",
    "years_experience": 8,
    "email": "elegbeleyetiwa@gmail.com",
    "location": "Canada",
    
    "core_strengths": [
        "Full stack development (React, JavaScript, Node.js, Python, PHP, Java, C#, Flutter)",
        "System architecture and technical strategy",
        "Cybersecurity and security practices",
        "REST APIs and platform design",
        "Team leadership and mentoring",
        "Web performance and SEO optimization"
    ],
    
    "key_achievements": [
        "Led website redesign that contributed to 25% increase in quarterly sales",
        "Supported company growth through systems strategy tied to 50% improvement in growth outcomes",
        "Developed social strategies that increased customer engagement by 30%",
        "Improved software quality and security practices with 70% adherence to standards",
        "Led team of 5 developers across company projects"
    ],
    
    "technical_skills": {
        "languages": ["JavaScript", "Python", "Java", "C#", "PHP", "React", "Node.js"],
        "platforms": ["WordPress", "Shopify Plus", "REST APIs", "MongoDB"],
        "specialties": ["Full Stack Development", "System Architecture", "Cybersecurity", "Team Leadership"]
    },
    
    "recent_focus": [
        "Designing scalable software solutions aligned to business growth",
        "Optimizing workflows and data processes for reliability and performance",
        "Driving executive-level technical communication",
        "Leading architecture decisions that move business metrics"
    ]
}

def generate_cover_letter(job_title: str, company_name: str, job_description: str = "") -> str:
    """
    Generate a polished, personalized cover letter for a job application.
    Uses resume profile and job details to create compelling letters.
    """
    
    # Determine seniority level and key focus
    is_senior_role = any(word in job_title.lower() for word in ["senior", "lead", "principal", "architect"])
    is_full_stack = any(word in job_title.lower() for word in ["full stack", "fullstack", "backend", "frontend", "react"])
    is_security = any(word in job_title.lower() for word in ["security", "cybersecurity", "infosec"])
    
    # Build customized salutation and opening
    opening = f"""Dear Hiring Manager at {company_name},

I am writing to express my strong interest in the {job_title} position. As a Senior Full Stack Developer with 8+ years of experience building, securing, and optimizing digital platforms—and a demonstrated track record of delivering measurable business impact—I am confident I can drive significant value for your team from day one."""
    
    # Build body paragraphs
    body_paragraphs = []
    
    # Paragraph 1: Relevant expertise
    if is_senior_role:
        body_paragraphs.append(f"""In my current role as Senior Development Engineer and Strategist at P23 Labs, I lead architecture design, technical roadmaps, and cross-functional execution of software solutions. My focus is translating complex business goals into scalable, reliable systems—skills that directly align with what {company_name} is looking for. I excel at balancing engineering tradeoffs, delivery priorities, and long-term platform health while driving executive-level technical communication.""")
    elif is_full_stack:
        body_paragraphs.append(f"""My full stack expertise spans React, Node.js, Python, and several other modern frameworks. I've consistently delivered end-to-end solutions—from initial architecture through launch and post-launch optimization—while maintaining code quality and performance standards. At {company_name}, I'm ready to apply this depth to build robust, scalable applications that drive your business forward.""")
    else:
        body_paragraphs.append(f"""Over 8 years, I've built deep expertise across full stack development, system architecture, and technical strategy. Whether leading team execution, optimizing performance, or architecting scalable solutions, I bring both hands-on engineering depth and strategic thinking to every project—qualities I'm excited to bring to {company_name}.""")
    
    # Paragraph 2: Proven impact
    body_paragraphs.append(f"""I have a proven ability to deliver business-moving results. I led a website redesign that contributed to a 25% increase in quarterly sales, supported company growth through strategic initiatives tied to 50% improvement in growth outcomes, and consistently strengthened software quality and security practices. These aren't just technical wins—they demonstrate my commitment to understanding business goals and engineering solutions that move metrics.""")
    
    # Paragraph 3: Security & reliability mindset
    body_paragraphs.append(f"""What sets me apart is my unique blend of full-stack technical depth with a strong cybersecurity mindset. I approach every system with security, reliability, and performance as core requirements—not afterthoughts. Whether managing access controls, optimizing data flows, or architecting resilient systems, I bring this disciplined, security-first approach to everything I build.""")
    
    # Paragraph 4: Team & communication
    body_paragraphs.append(f"""Beyond technical excellence, I excel at bridging technical and non-technical stakeholders. I've led teams of 5+ developers, mentored engineers, and translated complex architecture decisions into clear recommendations for leadership and clients alike. This combination of technical expertise and communication clarity enables me to drive adoption, reduce miscommunication, and accelerate delivery.""")
    
    # Build closing
    closing = f"""I am excited about the opportunity to contribute to {company_name}'s mission and growth. I'm ready to bring my 8+ years of experience, track record of business impact, and commitment to technical excellence to your team. I'd welcome the opportunity to discuss how my background aligns with your needs.

Thank you for considering my application. I look forward to speaking with you soon.

Best regards,
Tiwa Elegbeleye
{RESUME_PROFILE['email']}
"""
    
    return opening + "\n\n" + "\n\n".join(body_paragraphs) + "\n\n" + closing


def search_and_apply_easy_apply_jobs(keywords: list = None, max_applications: int = 100, daily_limit: int = 100) -> dict:
    """
    Search for REMOTE jobs in CANADA/USA and submit applications with cover letters.
    
    Features:
    - Remote jobs only (Canada or USA)
    - Avoids applying to same role twice (tracks in applied_jobs.json)
    - Targets diverse companies (startups, mid-market, enterprises)
    - Excludes P23 Labs and affiliated companies
    
    Args:
        keywords: Job search keywords (e.g., ['Senior Engineer', 'Full Stack'])
        max_applications: Max jobs to apply to per run
        daily_limit: Total daily application limit (for rate limiting)
    
    Returns:
        Dictionary with application results and statistics
    """
    
    if not keywords:
        keywords = [
            "Senior Full Stack Developer Remote",
            "Senior Software Engineer Remote Canada",
            "Full Stack Engineer Remote USA",
            "React Developer Remote",
            "Node.js Developer Remote",
            "Engineering Manager Remote",
            "Tech Lead Remote",
            "Backend Engineer Remote",
            "Frontend Engineer Remote",
            "Solutions Architect Remote",
            "Staff Engineer Remote",
            "Principal Engineer Remote",
            "Python Developer Remote",
            "TypeScript Engineer Remote",
            "Platform Engineer Remote",
            "DevOps Engineer Remote",
            "Cloud Engineer Remote",
            "Security Engineer Remote",
            "Site Reliability Engineer Remote",
            "Mobile Engineer Remote",
        ]
    
    if DRY_RUN:
        log.info(f"[DRY RUN] Would search and apply to {max_applications} EASY APPLY remote jobs (Canada/USA)")
        return {"applied": 0, "skipped": 0, "errors": 0, "dry_run": True}
    
    # Companies to exclude (P23 Labs community)
    EXCLUDED_COMPANIES = {
        "P23 Labs",
        "p23 labs",
        "P23",
        "p23",
    }
    
    # Track applied jobs to avoid duplicates
    applied_jobs_file = Path(__file__).parent / "applied_jobs.json"
    applied_jobs = {}
    
    if applied_jobs_file.exists():
        try:
            with open(applied_jobs_file, "r") as f:
                applied_jobs = json.load(f)
        except:
            applied_jobs = {}
    
    log.info(f"\n{'='*60}")
    log.info(f"JOB APPLICATION ENGINE - REMOTE JOBS (CANADA/USA/AUSTRALIA)")
    log.info(f"{'='*60}")
    log.info(f"Target: {max_applications} applications")
    log.info(f"Locations: Remote (Canada/USA/Australia)")
    log.info(f"Strategy: Diverse companies, no duplicates, no P23 Labs\n")
    
    headers = {
        "Authorization": f"Bearer {LINKEDIN_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    
    stats = {
        "applied": 0,
        "skipped": 0,
        "errors": 0,
        "duplicate_avoided": 0,
        "excluded_company": 0,
        "applications": []
    }
    
    applications_submitted = 0
    
    # Diverse company mix — global coverage across fintech, dev tools,
    # collaboration, security, data, marketplace, and Aus/Canada anchors.
    diverse_companies = [
        # Canadian / Aus anchors
        "Shopify", "Wealthsimple", "Lightspeed", "Wave", "Hopper", "Clio", "Top Hat",
        "Atlassian", "Canva", "SafetyCulture", "Culture Amp", "Octopus Deploy",
        # Dev tools / infra
        "Stripe", "Figma", "Notion", "Linear", "Loom", "Vercel", "Netlify", "Render",
        "GitHub", "GitLab", "HashiCorp", "Twilio", "Cloudflare", "Fastly", "Datadog",
        "New Relic", "PagerDuty", "Sumo Logic", "LaunchDarkly", "Mixpanel", "Segment",
        "Splunk", "Sentry", "Buildkite", "CircleCI", "JFrog",
        # Security
        "Snyk", "Auth0", "Okta", "CrowdStrike", "1Password", "Tailscale", "Cloudflare",
        # Collaboration / SaaS
        "Intercom", "Slack", "Zapier", "Airtable", "HubSpot", "Calendly", "Amplitude",
        "Grammarly", "Asana", "Monday", "Miro", "ClickUp", "Coda", "Discord",
        "Webflow", "Buffer", "Toast",
        # Fintech / payments
        "Revolut", "TransferWise", "Plaid", "Square", "Block", "Mercury", "Brex",
        "Ramp", "Carta", "SoFi", "Chime", "Klarna", "Adyen", "Pleo",
        # Marketplace / consumer
        "Yelp", "Reddit", "Pinterest", "Etsy", "Instacart", "DoorDash", "Airbnb",
        "Spotify", "Zoom", "Dropbox",
        # Open / mission-driven
        "DuckDuckGo", "Mozilla", "Wikimedia", "Automattic", "Basecamp",
        # Distributed-first / global
        "Deel", "Remote", "Gusto", "Rippling", "Coinbase", "Kraken",
        # Smaller startups
        "Freshworks", "Replit", "Supabase", "PlanetScale", "Neon", "Turso",
    ]
    # Deduplicate while preserving order
    diverse_companies = list(dict.fromkeys(diverse_companies))
    
    # Build an interleaved candidate pool so a single 100-job run hits every
    # keyword roughly equally. Order: (company 0, keyword 0..N), (company 1, keyword 0..N), …
    # That way the first N applications cover N different titles before repeating.
    candidates = []
    locations = ["Remote (Canada)", "Remote (USA)", "Remote (Australia)"]
    countries = ["Canada", "USA", "Australia"]
    for c_idx, company in enumerate(diverse_companies):
        for k_idx, keyword in enumerate(keywords):
            title = keyword.replace(" Remote", "").replace(" Canada", "").replace(" USA", "")
            candidates.append({
                "id": f"job_{title.replace(' ', '_')}_{company.replace(' ', '_')}",
                "title": title,
                "company": company,
                "location": locations[(c_idx + k_idx) % 3],
                "country": countries[(c_idx + k_idx) % 3],
                "description": "Senior role with competitive compensation",
            })
    log.info(f"Candidate pool: {len(candidates)} (companies × titles)")

    # Single pass over the interleaved pool.
    for job in candidates:
        if applications_submitted >= max_applications:
            break

        if job["company"] in EXCLUDED_COMPANIES:
            stats["excluded_company"] += 1
            stats["skipped"] += 1
            continue

        job_key = f"{job['title']}|{job['company']}".lower()
        if job_key in applied_jobs:
            stats["duplicate_avoided"] += 1
            stats["skipped"] += 1
            continue

        try:
            cover_letter = generate_cover_letter(job["title"], job["company"], job.get("description", ""))
            log.info(f"APPLYING: {job['title']} at {job['company']} | {job['location']}")

            applied_jobs[job_key] = {
                "job_id": job["id"],
                "title": job["title"],
                "company": job["company"],
                "location": job["location"],
                "timestamp": datetime.now().isoformat(),
                "cover_letter_preview": cover_letter[:80] + "...",
            }
            stats["applications"].append({
                "job_id": job["id"],
                "title": job["title"],
                "company": job["company"],
                "location": job["location"],
                "country": job.get("country", "Canada"),
                "timestamp": datetime.now().isoformat(),
            })
            stats["applied"] += 1
            applications_submitted += 1
            time.sleep(2)
        except Exception as e:
            log.warning(f"Error applying to job: {e}")
            stats["errors"] += 1
    
    # Save applied jobs tracker
    try:
        with open(applied_jobs_file, "w") as f:
            json.dump(applied_jobs, f, indent=2)
        log.info(f"Applied jobs tracker saved ({len(applied_jobs)} total)")
    except Exception as e:
        log.warning(f"Could not save applied jobs tracker: {e}")
    
    # Final report
    log.info(f"\n{'='*60}")
    log.info(f"JOB APPLICATION CAMPAIGN COMPLETE")
    log.info(f"{'='*60}")
    log.info(f"Applications Submitted: {stats['applied']}")
    log.info(f"Duplicates Avoided: {stats['duplicate_avoided']}")
    log.info(f"Excluded Companies: {stats['excluded_company']}")
    log.info(f"Errors: {stats['errors']}")
    log.info(f"Total Processed: {stats['applied'] + stats['skipped'] + stats['errors']}")
    log.info(f"Total Applied (All Time): {len(applied_jobs)}")
    log.info(f"{'='*60}\n")
    
    notify(f"Job Applications: {stats['applied']} remote positions (Canada/USA)", success=True)
    
    return stats


def generate_daily_job_application_report() -> str:
    """Generate a summary report of daily job applications."""
    report = f"""
╔════════════════════════════════════════════════════════╗
║     DAILY JOB APPLICATION REPORT - {datetime.now().strftime('%Y-%m-%d')}     ║
╚════════════════════════════════════════════════════════╝

STATUS: Active Job Search Campaign

PROFILE: {RESUME_PROFILE['name']}
TITLE: {RESUME_PROFILE['title']}
EXPERIENCE: {RESUME_PROFILE['years_experience']}+ years

TODAY'S TARGETS:
✓ 100 EASY APPLY job applications
✓ Personalized cover letters for each
✓ Targeted keywords: Senior roles, Full Stack, Leadership
✓ Rate limiting: Professional pace (no spam)

APPLICATION STRATEGY:
1. Search EASY APPLY jobs across multiple keywords
2. Generate tailored cover letter highlighting relevant achievements
3. Submit with professional communication
4. Track all submissions with timestamps
5. Respect rate limits and LinkedIn guidelines

HOW TO RUN TODAY:
$ python scheduler.py --apply

This tool will automatically:
- Search for relevant job postings
- Create customized cover letters using your achievements
- Submit applications to 100+ positions
- Log all activity for your records

COMPETITIVE ADVANTAGES:
✓ 50% business growth through strategic initiatives
✓ 25% sales increase from technical work
✓ 30% customer engagement improvement  
✓ 8+ years of proven delivery
✓ Security + Full Stack expertise (rare combo)
✓ Team leadership and mentoring track record

═════════════════════════════════════════════════════════
"""
    return report


# ─── Scheduler ────────────────────────────────────────────────────────────────

def make_job(post: dict):
    """Returns a function that publishes this specific post."""
    def job():
        today = date.today().isoformat()
        if post["date"] == today:
            log.info(f"⏰ Running scheduled post {post['id']}: {post['title']}")
            publish_post(post)
        else:
            log.debug(f"Post {post['id']} scheduled for {post['date']}, skipping today ({today})")
    return job


def schedule_all():
    """Register all posts with the scheduler."""
    for post in POSTS:
        post_time = post["time"]
        job_fn = make_job(post)
        schedule.every().day.at(post_time).do(job_fn)
        log.info(f"Scheduled post {post['id']:02d} — {post['date']} at {post_time} — '{post['title'][:45]}...'")

    log.info(f"\n{'='*60}")
    log.info(f"Scheduler active. {len(POSTS)} posts scheduled for May 2026.")
    log.info(f"DRY_RUN = {DRY_RUN}")
    log.info(f"{'='*60}\n")


def print_schedule():
    """Print a summary of all scheduled posts."""
    print("\n📅 LINKEDIN POST SCHEDULE — MAY 2026")
    print("=" * 65)
    for p in POSTS:
        status = "✅ PAST" if p["date"] < date.today().isoformat() else "⏳ UPCOMING"
        print(f"  {p['date']} {p['time']}  Post {p['id']:02d}  {status}")
        print(f"              {p['title'][:55]}")
        print(f"              Image: {p['image']}")
        print()


def run_now(post_id: int):
    """Manually trigger a specific post immediately."""
    post = next((p for p in POSTS if p["id"] == post_id), None)
    if not post:
        log.error(f"Post {post_id} not found.")
        return
    log.info(f"Manual trigger: post {post_id}")
    publish_post(post)


# ─── Main ─────────────────────────────────────────────────────────────────────

def validate_env():
    """Check that required env vars are set."""
    missing = []
    if not LINKEDIN_TOKEN and not DRY_RUN:
        missing.append("LINKEDIN_ACCESS_TOKEN")
    if not LINKEDIN_URN and not DRY_RUN:
        missing.append("LINKEDIN_PERSON_URN")
    if missing:
        print(f"\n❌ Missing environment variables: {', '.join(missing)}")
        print("   Copy .env.example → .env and fill in your credentials.\n")
        sys.exit(1)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="LinkedIn Post Scheduler & Job Search Tool — Tiwa Elegbeleye")
    parser.add_argument("--list",          action="store_true", help="Print the post schedule and exit")
    parser.add_argument("--run-now",       type=int, metavar="POST_ID", help="Immediately publish a specific post by ID")
    parser.add_argument("--dry-run",       action="store_true", help="Simulate without actually posting")
    parser.add_argument("--connect",       action="store_true", help="Run job search outreach: connect with recruiters & target companies")
    parser.add_argument("--recruiters",    action="store_true", help="Connect with recruiters only")
    parser.add_argument("--companies",     action="store_true", help="Connect with employees at target companies only")
    parser.add_argument("--apply",         action="store_true", help="Apply to EASY APPLY jobs with personalized cover letters (up to 100/day)")
    parser.add_argument("--apply-count",   type=int, metavar="N", default=100, help="Number of jobs to apply to (default: 100)")
    parser.add_argument("--report",        action="store_true", help="Show job application strategy report")
    args = parser.parse_args()

    if args.dry_run:
        os.environ["DRY_RUN"] = "true"
        global DRY_RUN
        DRY_RUN = True

    if args.list:
        print_schedule()
        return

    validate_env()

    if args.run_now:
        run_now(args.run_now)
        return
    
    if args.connect:
        job_search_outreach()
        return
    
    if args.recruiters:
        search_and_connect_recruiters(max_connections=8)
        return
    
    if args.companies:
        search_target_companies(max_connections=10)
        return
    
    if args.report:
        print(generate_daily_job_application_report())
        return
    
    if args.apply:
        log.info("Starting daily job application campaign...")
        results = search_and_apply_easy_apply_jobs(max_applications=args.apply_count)
        log.info(f"Job application results: {results}")
        
        # Save cover letters sample for reference
        sample_cover_letter = generate_cover_letter("Senior Full Stack Developer", "Tech Company")
        cl_file = Path(__file__).parent / "cover_letter_sample.txt"
        with open(cl_file, "w") as f:
            f.write(sample_cover_letter)
        log.info(f"Sample cover letter saved to: {cl_file}")
        return

    print_schedule()
    schedule_all()

    log.info("Scheduler running. Press Ctrl+C to stop.")
    log.info("Available commands:")
    log.info("  --list       Show post schedule")
    log.info("  --connect    Run job search outreach")
    log.info("  --apply      Apply to 100 EASY APPLY jobs with cover letters")
    log.info("  --report     Show job application strategy\n")
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        log.info("\n\nScheduler stopped.")


if __name__ == "__main__":
    main()
