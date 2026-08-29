# Teen Wellbeing Intelligence — Voice-First AI Agent

An AI-powered voice wellbeing companion for teenagers that listens with empathy, understands 5 core life dimensions, detects patterns early, and provides **automated escalation to counselors/guardians** before situations become critical.

---

## 🧠 Agent Architecture (v2 — Agentic Upgrade)

```
Teenager 🗣️
  ↓
Voice / Text Message
  ↓
┌─────────────────────────────────────────────────────────┐
│  SAFETY FLOOR (runs FIRST, always)                       │
│  RiskClassifier — regex/threshold rules                  │
│  IMMEDIATE_SAFETY, HIGH_CONCERN, CONCERNING, NORMAL      │
└───────────────────┬─────────────────────────────────────┘
                    │ rule_level (floor — cannot be lowered)
                    ▼
┌─────────────────────────────────────────────────────────┐
│  LLM AGENT — Gemini 1.5 Flash (PRIMARY signal)           │
│  • Reasons over FULL conversation history                │
│  • Returns risk_assessment.proposed_level + reasoning    │
│  • Returns pattern_observations (LLM-observed patterns)  │
│  • Tool-use: check_pattern_history, flag_risk_level,     │
│    trigger_escalation (function calling)                 │
└───────────────────┬─────────────────────────────────────┘
                    │ llm_proposed_level
                    ▼
        final = max(rule_level, llm_level)
        [Rule engine can escalate, NEVER downgrade LLM]
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  ESCALATION SERVICE (Task 1)                             │
│  Triggers on HIGH_CONCERN / IMMEDIATE_SAFETY             │
│  → Writes Escalation record to DB (audit trail)          │
│  → Optional SMTP email alert (ESCALATION_EMAIL_ENABLED)  │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  PATTERN DETECTOR (Task 3 — Adaptive)                    │
│  Rule-based patterns (source: "rule_based")              │
│  + LLM-observed patterns (source: "llm")                 │
│  → Merged, deduplicated by title                         │
└─────────────────────────────────────────────────────────┘
                    │
           ┌────────┴────────┐
           ▼                 ▼
   Teen Dashboard     Counselor /alerts
   (chat, graph)      (escalation audit)
```

---

## 🌟 Core System Features

### 1. 5 Core Life Dimensions
- **Social**: Friendships, peer pressure, isolation, drama, social confidence.
- **Family**: Parental expectations, home atmosphere, family communication.
- **Academic**: Exam anxiety, study workload, fear of failure, grades.
- **Digital**: Late-night phone browsing, doomscrolling, comparison.
- **Lifestyle**: Sleep duration, routine, energy, fatigue, meals.

### 2. Adaptive Pattern Detection
Identifies compound linkages using **two complementary engines**:
- **Rule-based engine** (always runs): 6 deterministic cross-dimensional patterns, baseline deviation detection, multi-session trend tracking.
- **LLM-observed patterns** (Task 3): Gemini observes subtler patterns (perfectionism, identity stress, seasonal low mood) that rules can't catch. Each pattern is tagged `source: "llm"` or `source: "rule_based"`.

Example rule-based chain:
> **Academic Pressure ↑ → Late Screen Use ↑ → Sleep Disruption ↓ → Daytime Fatigue ↑ → Social Withdrawal ↑**

### 3. Multilevel Safety & Escalation (Task 1)
| Level | Action |
|-------|--------|
| NORMAL | Supportive, reflective check-in |
| CONCERNING | Gentle inquiry, micro-coping actions |
| HIGH_CONCERN | Counselor suggestion + **automated Escalation record** |
| IMMEDIATE_SAFETY | Crisis guidance + click-to-dial + **automated Escalation record** |

### 4. LLM-Driven Risk Judgment (Task 2)
The LLM (Gemini 1.5 Flash) is the **primary signal** for risk assessment:
- Reasons over the full conversation history (last 12 turns).
- Returns `risk_assessment.proposed_level` with explicit `reasoning`.
- The deterministic `RiskClassifier` acts as a **mandatory safety floor** — it can only escalate the LLM's level upward, never downgrade it.

### 5. Gemini Tool-Use / Agentic Behaviour (Task 4)
The agent uses Gemini function calling with 3 tools:
- `check_pattern_history(user_id)` — queries DB for historical patterns.
- `trigger_escalation(reason)` — requests human escalation with reasoning.
- `flag_risk_level(level, reasoning)` — formally proposes a risk level.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Main agent endpoint. Returns `risk_assessment`, `active_patterns` (with `source`), `escalation_triggered`. |
| `GET` | `/api/dashboard/{user_id}` | Teen's wellbeing dashboard data. |
| `GET` | `/api/alerts` | **Counselor/guardian view** — lists all escalation records. |
| `PATCH` | `/api/alerts/{id}/status` | Update alert status: `acknowledged` \| `resolved`. |
| `POST` | `/api/speech/transcribe` | Audio → text (Deepgram). |
| `POST` | `/api/speech/synthesize` | Text → audio (ElevenLabs). |
| `GET` | `/docs` | Interactive OpenAPI documentation. |

### `/api/alerts` Query Params
| Param | Description |
|-------|-------------|
| `risk_level` | Filter: `HIGH_CONCERN` or `IMMEDIATE_SAFETY` |
| `status` | Filter: `pending`, `notified`, `acknowledged`, `resolved` |
| `limit` | Max results (default 50, max 200) |
| `offset` | Pagination offset |

---

## 🚀 Getting Started

### 1. Prerequisites
- **Node.js**: v18+
- **Python**: v3.10+
- **(Optional) PostgreSQL**: Falls back to SQLite automatically for local dev.

### 2. Backend Setup
```bash
cd backend
cp .env.example .env
# Edit .env and fill in your API keys (see Environment Variables below)

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Backend runs at `http://localhost:8000`.  
Docs at `http://localhost:8000/docs`.

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at `http://localhost:3000`.

### 4. Docker Deployment
```bash
docker-compose up --build
```
Create a `.env` in the project root with your keys (see docker-compose.yml).

---

## ⚙️ Environment Variables

Copy `backend/.env.example` to `backend/.env` and set:

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `DEEPGRAM_API_KEY` | For voice | Deepgram STT key |
| `ELEVENLABS_API_KEY` | For voice | ElevenLabs TTS key |
| `DATABASE_URL` | No | Postgres URL (defaults to SQLite) |
| `ESCALATION_EMAIL_ENABLED` | No | `true` to send SMTP alerts (default: `false`) |
| `SMTP_HOST` | If email enabled | e.g. `smtp.gmail.com` |
| `SMTP_PORT` | If email enabled | e.g. `587` |
| `SMTP_USER` | If email enabled | Sender email address |
| `SMTP_PASS` | If email enabled | SMTP app password |
| `ALERT_RECIPIENT_EMAIL` | If email enabled | Counselor's email |

---

## 🛡️ Responsible AI Principles
- **Preventive Companion**: Early pattern recognition and supportive listening, not clinical diagnosis.
- **Non-Diagnostic**: Detects patterns and life balances; does not label psychological disorders.
- **Human Connection First**: Prioritizes connecting teenagers with parents, counselors, and trusted mentors.
- **Safety Floor Guarantee**: Crisis language regex patterns (CRISIS_PATTERNS, HIGH_CONCERN_PATTERNS) run independently of the LLM and can only escalate, never be bypassed or overridden.
- **Audit Trail**: Every HIGH_CONCERN/IMMEDIATE_SAFETY message creates an immutable Escalation DB record for counselor review.
