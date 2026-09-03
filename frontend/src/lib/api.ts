const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export interface ChatResponse {
  user_id: string;
  conversation_id: string;
  response_text: string;
  emotions_detected: string[];
  dimension_scores: {
    social: number;
    family: number;
    academic: number;
    digital: number;
    lifestyle: number;
  };
  score_deltas: Record<string, number>;
  risk_level: "NORMAL" | "CONCERNING" | "HIGH_CONCERN" | "IMMEDIATE_SAFETY";
  risk_reasons: string[];
  safety_guidance: {
    headline: string;
    message: string;
    action: string;
    show_helplines: boolean;
    urgency: string;
  };
  helplines?: {
    country: string;
    emergency: string;
    resources: Array<{
      name: string;
      number: string;
      availability: string;
      type: string;
    }>;
  };
  active_patterns: Array<{
    title: string;
    description: string;
    category: string;
    severity: string;
    dimensions_involved: string[];
    evidence_snippets: string[];
  }>;
  intervention?: {
    id: string;
    type: string;
    title: string;
    content: string;
  };
  graph?: {
    nodes: any[];
    edges: any[];
  };
}

export interface DashboardData {
  user: {
    id: string;
    display_name: string;
    country_code: string;
    age_group: string;
    session_count: number;
  };
  dimensions: {
    [key: string]: {
      current: number;
      baseline: number;
      delta: number;
    };
  };
  trends: Array<{
    timestamp: string;
    social: number;
    family: number;
    academic: number;
    digital: number;
    lifestyle: number;
    emotions: string[];
  }>;
  patterns: Array<{
    id: string;
    title: string;
    description: string;
    category: string;
    severity: string;
    dimensions_involved: string[];
    evidence_snippets: string[];
    occurrence_count: number;
  }>;
  graph: {
    nodes: any[];
    edges: any[];
  };
  interventions: Array<{
    id: string;
    type: string;
    title: string;
    content: string;
    risk_level: string;
    date: string;
  }>;
  safety: {
    risk_level: "NORMAL" | "CONCERNING" | "HIGH_CONCERN" | "IMMEDIATE_SAFETY";
    guidance: any;
    helplines: any;
  };
}

export async function sendMessage(
  message: string,
  userId?: string,
  conversationId?: string,
  countryCode: string = "IN"
): Promise<ChatResponse> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: userId,
        conversation_id: conversationId,
        message,
        country_code: countryCode
      })
    });
  } catch (networkErr) {
    // The fetch itself failed — the backend is almost certainly not
    // reachable (not running, wrong port, CORS block, no network).
    console.error("[sendMessage] Network error reaching backend:", networkErr);
    throw new Error(
      `Could not reach the backend at ${API_BASE}. Is it running on port 8000?`
    );
  }

  if (!res.ok) {
    // Surface the REAL error from the backend instead of a generic message.
    // main.py's global exception handler returns { error, message, path }
    // on a 500, so we try to read that first.
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.message || body.detail || JSON.stringify(body);
    } catch {
      // response wasn't JSON, fall back to statusText
    }
    console.error(`[sendMessage] Backend returned ${res.status}:`, detail);
    throw new Error(`Backend error (${res.status}): ${detail}`);
  }
  return res.json();
}

export async function submitFeedback(
  userId: string,
  interventionId: string | null,
  rating: "helpful" | "somewhat_helpful" | "not_helpful",
  comment?: string
) {
  const res = await fetch(`${API_BASE}/chat/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: userId,
      intervention_id: interventionId,
      rating,
      comment
    })
  });
  return res.json();
}

export async function transcribeAudio(audioBlob: Blob): Promise<string> {
  const formData = new FormData();
  formData.append("file", audioBlob, "recording.webm");

  const res = await fetch(`${API_BASE}/speech/transcribe`, {
    method: "POST",
    body: formData
  });

  if (!res.ok) {
    return "";
  }
  const data = await res.json();
  return data.transcript || "";
}

export async function synthesizeSpeech(text: string): Promise<Blob | null> {
  const res = await fetch(`${API_BASE}/speech/synthesize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text })
  });

  if (res.status === 200) {
    return await res.blob();
  }
  return null;
}

export async function getDashboardData(userId: string): Promise<DashboardData> {
  const res = await fetch(`${API_BASE}/dashboard/${userId}`);
  if (!res.ok) {
    throw new Error("Failed to fetch dashboard data");
  }
  return res.json();
}
