import axios from "axios";

export interface FraudReport {
  risk_score: number;
  risk_level: string;
  explanation: string;
  processing_time_ms: number;
  analysis: {
    ela_score: number;
    noise_anomaly: boolean;
    edge_artifacts: boolean;
    blur_inconsistency: boolean;
    metadata_flag: boolean;
  };
  gemini: {
    verdict: string;
    suspicion_score: number;
    confidence: number;
    reasoning: string;
    available: boolean;
  } | null;
  warnings: string[];
  validation: {
    is_valid: boolean;
    reasons: string[];
    width: number | null;
    height: number | null;
    file_size_bytes: number | null;
    mime_type: string | null;
  };
  ela_visual: string | null;
  edge_visual: string | null;
  tamper_overlay_visual: string | null;
}

const base = (
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) ||
  "http://localhost:8000"
).replace(/\/+$/, "");

const client = axios.create({ baseURL: `${base}/api/v1`, timeout: 60_000 });

export async function analyzeDocument(file: File): Promise<FraudReport> {
  const form = new FormData();
  form.append("image", file);
  const res = await client.post<FraudReport>("/analyze-id", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}
