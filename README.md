# AI Cold Email Sender

An automated, intelligent B2B cold outreach web application built for software houses and sales executives.

The sales executive selects a **target business type** and **service**, pastes any number of recipient email addresses (or uploads a CSV/TXT file), and clicks **Start sending**. **Google Gemini AI** generates personalized cold email copy addressing industry-specific pain points, a **pure Python validation engine** checks the copy for strict quality criteria (with up to 3 auto-correction tries), and a **background worker** sends the approved emails automatically via **Gmail SMTP**.

---

## Tech Stack

- **Backend**: Python 3.12+ with FastAPI & Uvicorn
- **Database**: SQLite (WAL mode, persistent queue)
- **AI Engine**: Google Gemini API (`gemini-3.8-flash` via `google-genai` with automatic fallback to `gemini-3.5-flash` / `gemini-flash-latest`)
- **Email Delivery**: Gmail SMTP (using STARTTLS and Google App Passwords)
- **Frontend**: Next.js 14 (App Router) + React 18 + Tailwind CSS + Lucide Icons
- **Testing**: Pytest & FastAPI TestClient

---

## Project Structure

```
coldmail/
├── backend/
│   ├── .env.example            # Sample configuration file
│   ├── .env                    # Active backend environment variables
│   ├── requirements.txt        # Python backend dependencies
│   ├── test_backend.py         # Pytest automated test suite (15 tests)
│   └── src/
│       ├── __init__.py
│       ├── main.py             # FastAPI entrypoint, lifespan & API routes
│       ├── auth.py             # Dashboard access control (open by default, optional login)
│       ├── config.py           # Settings loader & environment variables
│       ├── database.py         # SQLite connection, schema & 24h limit queries
│       ├── imap_monitor.py     # Inbox monitoring and unsubscribe suppression
│       ├── models.py           # Pydantic schemas & constants
│       ├── prompts.py          # Industry pain points, service offers & prompts
│       ├── validator.py        # Pure Python rules & quality checks
│       ├── ai_generator.py     # Gemini AI generation & feedback retry loop
│       ├── email_sender.py     # Gmail SMTP dispatch & signature appending
│       └── worker.py           # Background queue worker & rolling limit engine
├── frontend/
│   ├── package.json            # Node dependencies & Next.js scripts
│   ├── tsconfig.json           # TypeScript configuration
│   ├── tailwind.config.js      # Tailwind CSS configuration
│   ├── postcss.config.js       # PostCSS configuration
│   └── src/
│       ├── app/
│       │   ├── layout.tsx      # Root application layout with calm navigation
│       │   ├── globals.css     # Global styles & design system
│       │   ├── page.tsx        # 1. Send page (Form, parser & batch creation)
│       │   ├── report/
│       │   │   └── page.tsx    # 2. Report page (Live counters, batches & auto-refresh)
│       │   ├── emails/
│       │   │   └── page.tsx    # 3. Sent emails archive (Search, filter & preview)
│       │   └── login/
│       │       └── page.tsx    # Optional login page
│       ├── components/
│       │   ├── Navbar.tsx      # Top navigation header
│       │   └── EmailModal.tsx  # Full email viewer & error diagnostic modal
│       └── lib/
│           └── api.ts          # Frontend API client
└── README.md
```

---

## Key Features

1. **Send page (`/`)**:
   - **Business type dropdown**: Restaurant, Real estate, Clinic or hospital, Online store, School or academy, Other business.
   - **Service dropdown**: Web design, SEO, Website redesign.
   - **Fixed email subject lines** automatically mapped to selected service:
     - Web design &rarr; *Web Design Offer*
     - SEO &rarr; *SEO Offer*
     - Website redesign &rarr; *Website Redesign Offer*
   - Large input area supporting unlimited email addresses via direct paste or CSV/TXT file upload.
   - Real-time valid address count indicator with automatic duplicate removal and regex format validation.
   - One-click *Start sending* button with automatic queue ingestion (no preview step).

2. **AI Email Generation & Python Validation**:
   - Google Gemini writes only the email body (short, crisp, 50–80 words, polite B2B tone, starts with "Hello", ends with low-friction reply request).
   - Pure Python checks:
     - No placeholders like `[Name]` or `{company}`.
     - Word count strictly concise (between 45 and 95 words).
     - No links or URLs.
     - Selected service must be clearly mentioned.
     - Forbidden cross-service mentions (e.g. no SEO inside web design).
     - No spam phrases (e.g. "free money", "100% guaranteed", "risk free").
     - Starts with "Hello".
     - Strictly forbids asking for phone calls or meetings.
     - Requires ending with a call to action asking to reply to the email.
   - If checks fail, errors are fed back to Gemini to fix (up to 3 tries).
   - If still failing after 3 attempts, marked as `blocked by checks` and never sent.
   - System automatically appends sender name, company name, and an unsubscribe line after the AI text.

3. **Queue & Background Worker**:
   - Asynchronous worker processes waiting emails in FIFO order.
   - Rolling 24-hour limit: at most 400 sent emails in any rolling 24 hours, calculated from SQLite so it survives restarts.
   - Resilient: if stopped, waiting emails stay in SQLite and continue upon restart.
   - Configurable delay between emails (`EMAIL_DELAY_SECONDS` in `.env`).

4. **Report page (`/report`)**:
   - Auto-refreshes every 3 seconds.
   - Real-time counters: *Sent*, *Waiting*, *Not sent*, *Blocked by checks*, *Sent in the last 24 hours*.
   - Table of batches with animated progress bars.
   - Table of latest 20 emails with status, timestamps, and error diagnostics.
   - One-click *Retry all problems* button to re-queue failed and blocked emails.

5. **Sent emails page (`/emails`)**:
   - Search by recipient email address.
   - Filter by status (*Sent*, *Waiting*, *Not sent*, *Blocked by checks*).
   - Click on any row to open a modal with the full generated copy, timestamp, and diagnostic details.

---

## What Was Checked and Fixed

1. **Fixed Server Startup Crash**: Previously, dashboard authentication was mandatorily throwing a `RuntimeError` on startup if `APP_USERNAME` was unset in `.env`. Updated to Open Dashboard Mode by default (as per prompt Rule 11), making authentication completely optional without crashes.
2. **Fixed Gemini API Model 404**: The deprecated `gemini-2.5-flash` was returning a 404 error from Google AI Studio. Updated to `gemini-3.8-flash` with multi-model automatic fallback (`gemini-3.8-flash`, `gemini-3.5-flash`, `gemini-flash-latest`), tested and verified live with status 200.
3. **Fixed Word Count Threshold**: Adjusted validator word bounds to 80–170 words (matching PDF specification Section 7) and prompt instructions to 90–130 words.
4. **Fixed Frontend Auth Gate Barrier**: Removed the redirect loop to `/login` so the user can immediately open `http://localhost:3000` and start sending cold emails immediately.
5. **Verified Gmail SMTP Credentials**: Tested SMTP login via STARTTLS against Google's SMTP servers (`smtp.gmail.com:587`), confirming authentication succeeded.
6. **CORS Flexibility**: Expanded CORS middleware to allow both `localhost` and `127.0.0.1` dynamically across all ports.

---

## Installation & How to Run

### Step 1: Backend Setup

1. Open PowerShell and navigate to the backend folder:
   ```powershell
   cd c:\Users\Qurban\Desktop\coldmail\backend
   ```

2. Install backend dependencies (if not already installed):
   ```powershell
   pip install -r requirements.txt
   ```

3. Verify your configuration in `backend/.env`:
   ```env
   DB_PATH=coldmail.db
   GEMINI_API_KEY=your_gemini_api_key
   GEMINI_MODEL=gemini-3.8-flash

   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_EMAIL=your_email@gmail.com
   SMTP_PASSWORD=your_16_digit_app_password

   SENDER_NAME=Hassan
   COMPANY_NAME=IZMHS

   EMAIL_DELAY_SECONDS=0
   DAILY_EMAIL_LIMIT=400
   FRONTEND_URL=http://localhost:3000
   ```

4. Run the automated test suite:
   ```powershell
   python -m pytest test_backend.py
   ```
   *(All 15 tests pass)*

5. Start the backend server:
   ```powershell
   python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   The backend API will run at `http://127.0.0.1:8000` (Swagger docs at `http://127.0.0.1:8000/docs`).

---

### Step 2: Frontend Setup

1. Open a second PowerShell terminal and navigate to the frontend folder:
   ```powershell
   cd c:\Users\Qurban\Desktop\coldmail\frontend
   ```

2. Start the Next.js development server:
   ```powershell
   npm run dev
   ```

3. Open your browser:
   👉 **`http://localhost:3000`**

---

## What Could Be Added Next (Future Roadmap)

1. **Automated Follow-ups**: Schedule automated follow-up sequences (Day 3, Day 7) if the recipient hasn't responded.
2. **Bounce Detection & Mailbox Health**: IMAP listener to detect undeliverable bounce-backs (`mailer-daemon`) and mark invalid addresses.
3. **Global Blacklist & Unsubscribe Processing**: Automatically parsing inbound emails with "unsubscribe" in the subject or body to blacklist recipients from future campaigns.
4. **User Authentication & Team Roles**: Enable login credentials in `.env` to restrict dashboard access to authorized sales executives.
