# Teen Wellbeing Intelligence — Voice-First AI

An AI-powered voice wellbeing companion for teenagers that listens with empathy, understands 5 core life dimensions, detects patterns early, and provides preventive human-support escalation before situations become critical.

---

## 🌟 Core System Architecture

```
Teenager 🗣️ ↔ Voice AI Wellbeing Agent 🧠 ↔ Multi-Dimension Analysis 📊 ↔ Pattern Detection 🔄 ↔ Personal Wellbeing Profile & Graph 🕸️ ↔ Preventive Human Escalation 🛡️
```

### 1. 5 Core Life Dimensions
- **Social**: Friendships, peer pressure, isolation, drama, social confidence.
- **Family**: Parental expectations, home atmosphere, family communication.
- **Academic**: Exam anxiety, study workload, fear of failure, grades.
- **Digital**: Late-night phone browsing, doomscrolling, comparison.
- **Lifestyle**: Sleep duration, routine, energy, fatigue, meals.

### 2. Cross-Dimensional Pattern Recognition
Identifies compound linkages such as:
> **Academic Pressure ↑ → Late Screen Use ↑ → Sleep Disruption ↓ → Daytime Fatigue ↑ → Social Withdrawal ↑**

### 3. Multilevel Safety & Escalation
- **NORMAL**: Supportive, reflective check-in.
- **CONCERNING**: Gentle inquiry, micro-coping actions, trusted adult encouragement.
- **HIGH CONCERN**: Clear preventive guidance, counselor/mentor suggestion, 24/7 helplines.
- **IMMEDIATE SAFETY**: Immediate crisis guidance, direct click-to-dial emergency numbers (112, 1098, 14416).

---

## 📞 Powered by CALL-E — Autonomous AI Phone Escalation

Aura integrates **[CALL-E](https://docs.heycall-e.com/)** (`calle-ai`) as its primary, intelligent escalation channel. 

When a teenager's message is assessed at **HIGH_CONCERN** or **IMMEDIATE_SAFETY**, the system does not simply log an alert in a dashboard or send a static robocall. Instead, Aura's backend dispatches an autonomous AI voice call via the CALL-E SDK to the on-call counselor or student support staff:

1. **Natural AI-to-Human Conversation**: CALL-E calls the designated counselor number, speaks naturally in their local language/region, and provides a clear situation briefing detailing the detected risk level and specific reasons.
2. **Context-Aware Follow-up & Confirmation**: CALL-E confirms whether the counselor is reached, checks if they can follow up with the student, and asks for immediate guidance.
3. **Structured & Schema-Validated Outcomes**: Upon call completion, CALL-E returns a structured JSON result validated against a strict JSON Schema:
   - `counselor_reached`: `yes` | `no` | `unknown`
   - `acknowledged`: `yes` | `no` | `unknown`
   - `recommended_next_step`: `dispatch_now` | `schedule_followup` | `no_action_needed` | `retry_later` | `unknown`
   - `notes`: Key notes and guidance transcribed from the conversation
4. **Actionable Counselor Dashboard**: These structured insights are automatically stored in the `Escalation` audit record and surfaced via `GET /api/alerts`, giving school staff and counselors immediate visibility into what the call accomplished and what next steps were agreed upon.
5. **Robust Fallback**: If CALL-E is not configured, the system gracefully falls back to Twilio SMS/Voice or secure audit logging.

> *Built for the CALL-E Hackathon demonstrating real-world agentic voice SDK integration for preventative adolescent mental health support.*


---

## 🚀 Getting Started

### 1. Prerequisites
- **Node.js**: v18+
- **Python**: v3.10+
- **(Optional) PostgreSQL**: PostgreSQL 15+ (falls back to built-in SQLite for immediate local testing)

### 2. Backend Setup
```bash
cd backend
cp .env.example .env
# Optional: Add your GEMINI_API_KEY, DEEPGRAM_API_KEY, ELEVENLABS_API_KEY in .env

# Install dependencies
pip install -r requirements.txt

# Run the FastAPI server
uvicorn main:app --reload --port 8000
```
Backend runs at `http://localhost:8000`. Interactive OpenAPI documentation at `http://localhost:8000/docs`.

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

---

## 🛡️ Responsible AI Principles
- **Preventive Companion**: Designed for early pattern recognition and supportive listening, not clinical diagnosis.
- **Non-Diagnostic**: Detects patterns and life balances; does not label psychological disorders.
- **Human Connection First**: Prioritizes connecting teenagers with parents, counselors, and trusted mentors.
