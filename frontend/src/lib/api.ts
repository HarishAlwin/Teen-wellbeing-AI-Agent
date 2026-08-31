const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export interface ChatResponse {
  user_id: string;
  conversation_id: string;
  response_text: string;
  emotions_detected: string[];
  detailed_emotions?: Array<{ emotion: string; score: number }>;
  sentiment?: {
    label: "positive" | "neutral" | "negative";
    score: number;
    distribution?: Record<string, number>;
  };
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

export interface OCRResponse {
  filename: string;
  ocr_result: {
    extracted_text: string;
    document_type: string;
    summary: string;
    wellbeing_indicators: {
      dimensions_affected: string[];
      apparent_stress_level: string;
      key_observations: string[];
    };
  };
  ai_companion_reply: string;
  dimension_impacts: Record<string, number>;
  risk_assessment: Record<string, any>;
  intervention?: {
    type: string;
    title: string;
    content: string;
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

let cachedToken: string | null = null;

export function getStoredToken(): string | null {
  if (typeof window !== "undefined") {
    return localStorage.getItem("teen_auth_token") || cachedToken;
  }
  return cachedToken;
}

export function setAuthToken(token: string, userId?: string, role?: string): void {
  cachedToken = token;
  if (typeof window !== "undefined") {
    localStorage.setItem("teen_auth_token", token);
    if (userId) localStorage.setItem("teen_user_id", userId);
    if (role) localStorage.setItem("teen_user_role", role);
  }
}

export function clearAuthToken(): void {
  cachedToken = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem("teen_auth_token");
    localStorage.removeItem("teen_user_id");
    localStorage.removeItem("teen_user_role");
  }
}

export async function getAuthToken(): Promise<string> {
  const existing = getStoredToken();
  if (existing) return existing;

  try {
    const res = await fetch(`${API_BASE}/auth/guest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ display_name: "Alex", country_code: "IN" })
    });
    if (res.ok) {
      const data = await res.json();
      if (data.access_token) {
        setAuthToken(data.access_token, data.user_id, data.role);
        return data.access_token;
      }
    }
  } catch (err) {
    console.error("Failed to acquire guest auth token:", err);
  }
  return "";
}

export async function getAuthHeaders(extraHeaders: Record<string, string> = {}): Promise<Record<string, string>> {
  const token = await getAuthToken();
  const headers: Record<string, string> = { ...extraHeaders };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export async function sendMessage(
  message: string,
  userId?: string,
  conversationId?: string,
  countryCode: string = "IN"
): Promise<ChatResponse> {
  let headers = await getAuthHeaders({ "Content-Type": "application/json" });
  let res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      conversation_id: conversationId,
      message,
      country_code: countryCode
    })
  });

  // If unauthorized (e.g. token expired), re-authenticate as guest and retry once
  if (res.status === 401) {
    clearAuthToken();
    headers = await getAuthHeaders({ "Content-Type": "application/json" });
    res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        conversation_id: conversationId,
        message,
        country_code: countryCode
      })
    });
  }

  if (!res.ok) {
    const errText = await res.text().catch(() => "");
    throw new Error(`Failed to send message (${res.status}): ${errText || res.statusText}`);
  }
  return res.json();
}

export async function analyzeImageDocument(
  file: File,
  userId?: string,
  conversationId?: string
): Promise<OCRResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (userId) formData.append("user_id", userId);
  if (conversationId) formData.append("conversation_id", conversationId);

  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/ocr/analyze`, {
    method: "POST",
    headers,
    body: formData
  });

  if (!res.ok) {
    throw new Error(`OCR analysis failed: ${res.statusText}`);
  }
  return res.json();
}

export async function submitFeedback(
  userId: string,
  interventionId: string | null,
  rating: "helpful" | "somewhat_helpful" | "not_helpful",
  comment?: string
) {
  const headers = await getAuthHeaders({ "Content-Type": "application/json" });
  const res = await fetch(`${API_BASE}/chat/feedback`, {
    method: "POST",
    headers,
    body: JSON.stringify({
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
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/dashboard/${userId}`, {
    headers
  });
  if (!res.ok) {
    throw new Error("Failed to fetch dashboard data");
  }
  return res.json();
}

