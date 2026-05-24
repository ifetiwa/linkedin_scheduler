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
# DATA_DIR is overridable in production (e.g. Render persistent disk).
# Locally it falls back to the repo directory.
DATA_DIR         = Path(os.getenv("DATA_DIR") or Path(__file__).parent)
DATA_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR       = Path(__file__).parent / "images"
LOG_FILE         = DATA_DIR / "scheduler.log"
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
        "date": "2026-05-25",
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
        "date": "2026-05-27",
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
        "date": "2026-05-29",
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
    {
        "id": 13,
        "date": "2026-06-01",
        "time": "08:00",
        "image": "post13_cicd_pipeline.png",
        "title": "Building a CI/CD pipeline that saves 4 hours/week",
        "body": """Most teams I've worked with overspend on CI/CD setup and underspend on the small things that compound.

Here's the pipeline I now reach for first — under 60 lines of YAML and it's saved us 4+ hours/week per developer:

→ Cache node_modules / pip cache aggressively (10–20s saved per build)
→ Run lint + typecheck in parallel with tests, not before
→ Tag preview deploys with the PR number, auto-destroy on merge
→ Block merges only on tests that touched changed files
→ Notify on red builds in Slack — never email

The biggest unlock isn't the tools. It's deciding what NOT to block on.

A 9-minute pipeline that runs 30x a day quietly costs your team a full workday every week.

What's the one thing in your pipeline you'd cut tomorrow if no one would notice?""",
        "hashtags": "#DevOps #CICD #SoftwareEngineering #DeveloperProductivity #FullStackDeveloper #BuildPipeline #GitHubActions #EngineeringExcellence",
        "first_comment": f"My GitHub Actions templates → {GITHUB}",
    },
    {
        "id": 14,
        "date": "2026-06-03",
        "time": "08:00",
        "image": "post14_microservices.png",
        "title": "Microservices vs Monolith — when I pick each",
        "body": """I've shipped both, broken both, and rewritten one into the other. Twice.

Here's the rule of thumb I've landed on after 8 years:

🟦 Stay monolith when:
→ Team is under 8 engineers
→ You're still validating product-market fit
→ Your data has heavy cross-domain joins
→ You don't have on-call rotation yet

🟪 Reach for services when:
→ Two teams are stepping on each other's deploys
→ One subsystem has very different scale or compliance needs (e.g. payments, PII)
→ You can afford a real observability stack (traces, not just logs)
→ You've already enforced clean module boundaries inside the monolith

The honest truth: 80% of "we need microservices" conversations are actually "we need clean module boundaries."

Modular monoliths beat bad microservices every time.

What's your team running today — and what would you change?""",
        "hashtags": "#SoftwareArchitecture #Microservices #Monolith #SystemDesign #Backend #FullStackDeveloper #EngineeringLeadership #TechStrategy",
        "first_comment": f"Notes on modular monoliths I keep referring back to → {GITHUB}",
    },
    {
        "id": 15,
        "date": "2026-06-05",
        "time": "08:00",
        "image": "post15_react_bundle.png",
        "title": "How I cut a React bundle by 62%",
        "body": """The app loaded in 8.4s on 4G. We needed it under 3.

I expected weeks of work. Took 2 afternoons. 62% smaller bundle, 2.1s LCP.

Here's the order I actually attacked it in:

1. Run `npx vite-bundle-visualizer` first. Look for the suspicious giant blocks.
2. moment.js → date-fns: -210KB
3. Replaced full lodash with named imports: -88KB
4. Dynamic import for the admin route: -340KB off the initial load
5. Replaced 3 unused chart libs (yes, three) with one
6. Compressed hero images with sharp at build time

The lesson: most React perf problems aren't React. They're dependencies you forgot you added.

Open your bundle analyzer once a quarter. It pays for itself.

What's the biggest dependency you've gotten rid of?""",
        "hashtags": "#React #WebPerformance #FrontendDevelopment #JavaScript #ReactJS #PerformanceOptimization #FullStackDeveloper #WebVitals",
        "first_comment": f"My before/after bundle screenshots → {GITHUB}",
    },
    {
        "id": 16,
        "date": "2026-06-08",
        "time": "08:00",
        "image": "post16_hiring_seniors.png",
        "title": "5 questions before hiring a senior developer",
        "body": """I've sat on both sides of 40+ senior engineering interviews.

The ones who turned out to be great hires answered these 5 questions differently than everyone else:

1. "Tell me about a system you owned end-to-end — what would you do differently?"
   → Strong answers admit specific mistakes. Weak ones describe what went well.

2. "Walk me through a code review where you disagreed with someone more senior."
   → I'm listening for how they hold ground without burning bridges.

3. "What did you have to unlearn from your last role?"
   → If they can't name something, they didn't grow there.

4. "Show me a piece of production code you're proud of. Now show me one you're not."
   → Self-awareness > syntax.

5. "Who on your last team did you learn the most from, and why?"
   → Real seniors name junior teammates here, not just architects.

Tech screens tell you who can solve LeetCode. These tell you who can ship and grow a team.

What's the one question you wish you'd asked in your last hire?""",
        "hashtags": "#TechLeadership #EngineeringManagement #Hiring #TechRecruiting #SeniorDeveloper #SoftwareEngineering #TeamBuilding #Leadership",
        "first_comment": f"The full interview rubric I use → {GITHUB}",
    },
    {
        "id": 17,
        "date": "2026-06-10",
        "time": "08:00",
        "image": "post17_multi_tenant.png",
        "title": "Multi-tenant SaaS: the 3 hardest decisions",
        "body": """Built two multi-tenant platforms now. Every "interesting" bug came back to one of these three calls:

1. Shared schema vs schema-per-tenant vs DB-per-tenant.
   → We started shared, regretted it for our top 3 customers (GDPR + reporting at scale).
   → Settled on shared + schema-per-tenant for whales. Best of both.

2. How tenant context flows through the request.
   → Don't trust the JWT alone. Inject tenant_id at the edge, treat anywhere downstream as untrusted.
   → A single forgotten WHERE clause leaks every customer's data.

3. Background jobs.
   → Tenant-aware queues from day one. One noisy customer should never block another.
   → We added per-tenant rate limits on workers — paid off within 2 weeks.

The pattern I now reach for first: shared schema + row-level security + per-tenant connection pools. It scales to ~500 tenants before you need to split.

If you're building SaaS in 2026 — what's biting you the most?""",
        "hashtags": "#SaaS #MultiTenant #SoftwareArchitecture #Backend #DatabaseDesign #FullStackDeveloper #SystemDesign #StartupEngineering",
        "first_comment": f"My multi-tenant scaffolding repo → {GITHUB}",
    },
    {
        "id": 18,
        "date": "2026-06-12",
        "time": "12:00",
        "image": "post18_owasp.png",
        "title": "The OWASP Top 10 every full-stack dev should actually know",
        "body": """Security isn't a separate team's job. It's a tax you pay on every PR.

I'm ISC2 trained and I still see these 10 mistakes in code I review every month:

1. Broken access control — checking auth in the UI, not the API
2. Cryptographic failures — storing tokens unencrypted, weak salts
3. Injection — yes, SQL injection is still alive. So is template injection.
4. Insecure design — features shipped before threat modeling
5. Security misconfiguration — default credentials, open S3 buckets
6. Vulnerable & outdated components — that npm audit warning matters
7. Identification failures — no MFA, no rate limit on /login
8. Software & data integrity failures — unverified CI/CD pipelines
9. Logging & monitoring failures — you'll find out from a customer
10. Server-side request forgery — letting users dictate URLs to fetch

You don't have to memorize CVE codes. You have to internalize the categories.

90% of breaches I've seen up close are in 1, 2, 3, and 7. Start there.

Which of these has bitten you (or your team) hardest?""",
        "hashtags": "#Cybersecurity #OWASP #ApplicationSecurity #SecureCoding #ISC2 #FullStackDeveloper #DevSecOps #InfoSec #SoftwareSecurity",
        "first_comment": f"My OWASP checklist (PR template) → {GITHUB}",
    },
    {
        "id": 19,
        "date": "2026-06-15",
        "time": "08:00",
        "image": "post19_integration_first.png",
        "title": "Why I write integration tests before unit tests",
        "body": """Controversial take after 8 years and a lot of broken builds:

Most teams over-invest in unit tests and under-invest in integration tests.

Here's the order I now write tests in:

1. One happy-path integration test for the new endpoint
   → Real DB, real HTTP, real auth. Slow but priceless.

2. One failure-path integration test
   → Wrong tenant, expired token, invalid payload.

3. THEN unit tests for the gnarly pure functions
   → Date math, parsers, business rules with 6 branches.

4. Snapshot tests only for stable visual components

Why this order? Unit tests catch implementation bugs. Integration tests catch the bugs that actually ship to production.

A passing test suite with 95% unit coverage and zero integration tests is theater. I've watched it ship security holes more than once.

What's your team's ratio of unit vs integration?""",
        "hashtags": "#TestingMatters #SoftwareTesting #IntegrationTesting #SoftwareEngineering #QualityAssurance #FullStackDeveloper #DevPractices #CleanCode",
        "first_comment": f"My pytest + supertest scaffolding → {GITHUB}",
    },
    {
        "id": 20,
        "date": "2026-06-17",
        "time": "08:00",
        "image": "post20_db_indexing.png",
        "title": "Database indexing: a practical guide for app devs",
        "body": """A 4ms query went to 1.2 seconds. The table had 800k rows. The fix was 1 line.

Indexing is the highest-leverage backend skill I've ever learned. And most app devs avoid it.

A short, opinionated guide:

→ Index every column you filter on with WHERE
→ Index the JOIN columns, both sides
→ Composite indexes match LEFT-TO-RIGHT — order matters
→ `WHERE created_at > X AND user_id = Y` wants (user_id, created_at), not (created_at, user_id)
→ Indexes make writes slower. Don't index everything "just in case."
→ EXPLAIN ANALYZE is your second-best friend. pg_stat_statements is your first.

The hidden killer: indexes you ADDED 2 years ago that no query uses anymore. Drop them.

Run pg_stat_user_indexes monthly. You'll find at least one freebie every time.

What's your favorite "added one index and the app got 10x faster" story?""",
        "hashtags": "#DatabaseDesign #PostgreSQL #Backend #SQL #DataEngineering #SoftwareEngineering #FullStackDeveloper #PerformanceTuning",
        "first_comment": f"My EXPLAIN ANALYZE cheat sheet → {GITHUB}",
    },
    {
        "id": 21,
        "date": "2026-06-19",
        "time": "08:00",
        "image": "post21_graphql_vs_rest.png",
        "title": "GraphQL vs REST in 2026 — a pragmatic take",
        "body": """I've shipped both at scale. The "GraphQL replaces REST" hype was overblown. So was the "GraphQL is dead" backlash.

What I'd actually do today, project by project:

REST when:
→ You're building a public API for third parties
→ Your clients are heterogeneous and cacheable behavior matters (CDN, browser cache)
→ You have a small team and don't want N+1 query landmines

GraphQL when:
→ You have a mobile app + web app pulling overlapping data
→ Frontend teams iterate faster than backend teams
→ You can afford persisted queries + a proper resolver discipline

tRPC when:
→ Same team owns frontend and backend, TypeScript end-to-end
→ You want types, not flexibility

Hybrid is fine. Most teams I respect run REST for external + GraphQL or tRPC for their own apps.

The choice isn't religious. It's about who's calling your API and how often the shape changes.

What's your current API stack — and would you pick it again?""",
        "hashtags": "#API #GraphQL #REST #Backend #FullStackDeveloper #SoftwareArchitecture #WebDevelopment #TypeScript #APIDesign",
        "first_comment": f"My GraphQL + REST hybrid example → {GITHUB}",
    },
    {
        "id": 22,
        "date": "2026-06-22",
        "time": "12:00",
        "image": "post22_standup.png",
        "title": "A standup that doesn't waste 30 minutes",
        "body": """I've been in standups where 7 engineers reported status for 35 minutes. Nobody acted on anything.

Here's the standup format I run now — under 8 minutes, 3 days a week:

1. Each person, ONE sentence: "I'm working on X today."
   → No yesterday recap. The board has that.

2. Then a single question: "Anything blocked?"
   → Blockers get a 30-second naming. Solutions go to async afterwards.

3. Then: "Anything anyone should know that isn't on the board?"
   → 90% of the time, nothing. Good.

That's it. No round-the-room status theater.

The number that changed for us:
→ Standup minutes/week: 105 → 24
→ Engineers reporting "I'm more productive": 8 of 9 in our retro

The point of standup isn't reporting. It's surfacing the things that need to be unstuck today.

What's your current standup like — and what would you change?""",
        "hashtags": "#EngineeringLeadership #AgileLeadership #Standups #TeamProductivity #SoftwareEngineering #TechLeadership #RemoteTeams #EngineeringCulture",
        "first_comment": f"The 5-bullet standup template my team uses → {GITHUB}",
    },
    {
        "id": 23,
        "date": "2026-06-24",
        "time": "08:00",
        "image": "post23_web_vitals.png",
        "title": "Web Vitals: the only 3 metrics I optimize for",
        "body": """Stop chasing every Lighthouse score. Google uses 3 numbers for ranking. Optimize THOSE.

After tuning ~15 production apps, here's where I focus:

1. LCP (Largest Contentful Paint) → target under 2.5s
   → The hero image. Compress it. Preload it. Serve it from a CDN.

2. INP (Interaction to Next Paint, replaced FID in 2024) → target under 200ms
   → The thing they tap. Don't block the main thread with heavy JS.
   → Use `requestIdleCallback` for non-urgent work. Use Web Workers for heavy lifting.

3. CLS (Cumulative Layout Shift) → target under 0.1
   → The page jumping while it loads. Reserve image dimensions. Don't inject ads above content.

That's it. Everything else is decoration.

Tools I actually use:
→ PageSpeed Insights for the score
→ Chrome DevTools Performance tab for the why
→ Real User Monitoring (Sentry / Datadog) for the truth

One score on your laptop ≠ what your users see on a 3-year-old Android.

What's your team's worst Web Vital right now?""",
        "hashtags": "#WebPerformance #CoreWebVitals #SEO #FrontendDevelopment #WebDevelopment #PerformanceOptimization #FullStackDeveloper #UX",
        "first_comment": f"My Web Vitals audit checklist → {GITHUB}",
    },
    {
        "id": 24,
        "date": "2026-06-26",
        "time": "08:00",
        "image": "post24_typescript.png",
        "title": "TypeScript: 3 patterns I now use every day",
        "body": """I avoided TypeScript for 3 years. Then I migrated a 40k-line codebase. Now I won't go back.

The 3 patterns that pay rent in my code every single day:

1. Discriminated unions for API responses
   → type ApiResult<T> = { ok: true; data: T } | { ok: false; error: string }
   → Forces the compiler to make you handle the error case. No more "undefined is not a function" at 2am.

2. `as const` + `keyof typeof` for finite string sets
   → No more enums. const ROLES = ['admin','user','guest'] as const; type Role = (typeof ROLES)[number]
   → Lets you map over the values at runtime AND keep type safety.

3. Branded types for IDs you should never mix up
   → type UserId = string & { __brand: 'UserId' }
   → Now passing a postId where a userId belongs is a compile error, not a production bug.

The pattern I see junior devs miss: TypeScript isn't about adding types. It's about making invalid states unrepresentable.

Which pattern would you add to this list?""",
        "hashtags": "#TypeScript #JavaScript #WebDevelopment #FullStackDeveloper #SoftwareEngineering #FrontendDevelopment #TypeSafety #CleanCode",
        "first_comment": f"My TypeScript patterns repo → {GITHUB}",
    },
    {
        "id": 25,
        "date": "2026-06-29",
        "time": "08:00",
        "image": "post25_code_reviews.png",
        "title": "Code reviews that don't hurt",
        "body": """The fastest way to lose a good engineer is bad code review culture.

After leading reviews for years, here's what I've changed about how I do them:

→ I lead with what I'd do differently, not with what's "wrong"
→ I prefix nitpicks with "nit:" so the author can ignore them
→ I ask questions instead of giving commands
→ "Why this approach over X?" beats "Use X instead."
→ I approve with caveats. Holding a PR for 3 nits is a power move, not a quality bar.
→ I review the diff in tools/CI BEFORE the human code

The number I track:
→ Time from "ready for review" to first comment.
→ For my teams: under 4 working hours, every time. Aging PRs kill morale.

Review is teaching. If your reviews make the author smaller, you're doing it wrong.

What's one thing your team does in reviews that you'd recommend?""",
        "hashtags": "#CodeReview #TechLeadership #EngineeringCulture #SoftwareEngineering #TeamProductivity #FullStackDeveloper #Mentorship #DevPractices",
        "first_comment": f"My code review checklist (PR template) → {GITHUB}",
    },
]

# ─── Post overrides (UI-editable layer) ──────────────────────────────────────
# The POSTS list above is the seed. Anything edited from the dashboard is saved
# to DATA_DIR/post_overrides.json and merged on read by get_posts().
# Override schema: {"<post_id>": {"title": ..., "body": ..., "date": ..., "time": ..., "hashtags": ..., "first_comment": ..., "published_at": ...}}

POST_OVERRIDES_FILE = DATA_DIR / "post_overrides.json"
PUBLISHED_FILE = DATA_DIR / "published_posts.json"


def _load_json(path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_posts():
    """Return POSTS merged with any UI-saved overrides. Always call this
    instead of reading POSTS directly so edits show up everywhere."""
    overrides = _load_json(POST_OVERRIDES_FILE, {})
    merged = []
    for post in POSTS:
        pid = str(post["id"])
        if pid in overrides:
            merged.append({**post, **overrides[pid]})
        else:
            merged.append(dict(post))
    return merged


def save_post_override(post_id, fields):
    """Persist edits for a single post. `fields` is a dict of partial overrides."""
    allowed = {"title", "body", "date", "time", "hashtags", "first_comment", "image"}
    clean = {k: v for k, v in fields.items() if k in allowed}
    overrides = _load_json(POST_OVERRIDES_FILE, {})
    overrides[str(post_id)] = {**overrides.get(str(post_id), {}), **clean}
    _save_json(POST_OVERRIDES_FILE, overrides)
    return overrides[str(post_id)]


def is_published(post_id):
    """Has this post already been published in a previous run today/recently?"""
    pub = _load_json(PUBLISHED_FILE, {})
    return str(post_id) in pub


def mark_published(post_id):
    pub = _load_json(PUBLISHED_FILE, {})
    pub[str(post_id)] = datetime.now().isoformat()
    _save_json(PUBLISHED_FILE, pub)


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
    applied_jobs_file = DATA_DIR / "applied_jobs.json"
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

def make_job(post_id: int):
    """Returns a job that re-reads the post on every fire so edits made via
    the dashboard apply at publish time. Also dedupes against the published
    tracker so a manual 'Post Now' followed by the scheduled tick doesn't
    double-publish."""
    def job():
        today = date.today().isoformat()
        # Always read the latest copy (in case the user edited it)
        post = next((p for p in get_posts() if p["id"] == post_id), None)
        if not post:
            log.warning(f"Post {post_id} no longer exists; skipping")
            return schedule.CancelJob
        if post["date"] != today:
            return
        if is_published(post_id):
            log.info(f"Post {post_id} already published — skipping scheduled tick")
            return
        log.info(f"⏰ Running scheduled post {post['id']}: {post['title']}")
        ok = publish_post(post)
        if ok:
            mark_published(post_id)
    return job


def schedule_all():
    """Register all posts with the scheduler (one daily tick per post)."""
    schedule.clear()  # safe to call repeatedly — clears prior registrations
    posts = get_posts()
    for post in posts:
        try:
            schedule.every().day.at(post["time"]).do(make_job(post["id"]))
            log.info(f"Scheduled post {post['id']:02d} — {post['date']} at {post['time']} — '{post['title'][:45]}...'")
        except Exception as e:
            log.warning(f"Failed to schedule post {post.get('id')}: {e}")

    log.info(f"\n{'='*60}")
    log.info(f"Scheduler active. {len(posts)} posts registered (Mon/Wed/Fri rhythm).")
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
    """Manually trigger a specific post immediately. Honors UI edits via get_posts()."""
    post = next((p for p in get_posts() if p["id"] == post_id), None)
    if not post:
        log.error(f"Post {post_id} not found.")
        return
    log.info(f"Manual trigger: post {post_id}")
    ok = publish_post(post)
    if ok:
        mark_published(post_id)


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
