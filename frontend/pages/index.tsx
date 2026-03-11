import Head from "next/head";
import React, { useCallback, useRef, useState } from "react";
import { analyzeDocument, FraudReport } from "@/services/api";

// ─── tiny inline helpers ───────────────────────────────────────────────────

function riskColor(score: number) {
  if (score < 30) return { bg: "#e8faf3", border: "#34d399", text: "#065f46", bar: "#10b981" };
  if (score < 60) return { bg: "#fffbeb", border: "#fbbf24", text: "#92400e", bar: "#f59e0b" };
  return              { bg: "#fef2f2", border: "#f87171", text: "#991b1b", bar: "#ef4444" };
}

function riskEmoji(level: string) {
  if (level === "Likely Genuine") return "✅";
  if (level === "Medium Risk")    return "⚠️";
  return "🚨";
}

function SignalDot({ active }: { active: boolean }) {
  return (
    <span style={{
      display: "inline-block", width: 8, height: 8, borderRadius: "50%",
      background: active ? "#f59e0b" : "#10b981",
      flexShrink: 0,
    }} />
  );
}

// ─── main page ─────────────────────────────────────────────────────────────

export default function Home() {
  const [file, setFile]         = useState<File | null>(null);
  const [preview, setPreview]   = useState<string | null>(null);
  const [report, setReport]     = useState<FraudReport | null>(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);
  const [drag, setDrag]         = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const pick = useCallback((f: File | null | undefined) => {
    if (!f) return;
    if (!["image/jpeg","image/jpg","image/png"].includes(f.type)) {
      setError("Please upload a JPEG or PNG image."); return;
    }
    if (f.size > 10 * 1024 * 1024) {
      setError("File must be under 10 MB."); return;
    }
    setError(null);
    setReport(null);
    setFile(f);
    setPreview(URL.createObjectURL(f));
  }, []);

  const analyze = async () => {
    if (!file) return;
    setLoading(true); setError(null); setReport(null);
    try {
      setReport(await analyzeDocument(file));
    } catch (e: any) {
      setError(
        e?.response?.data?.detail?.details ||
        e?.response?.data?.detail?.message ||
        e?.message || "Analysis failed."
      );
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    if (preview) URL.revokeObjectURL(preview);
    setFile(null); setPreview(null); setReport(null);
    setError(null); setLoading(false);
  };

  const colors = report ? riskColor(report.risk_score) : null;

  return (
    <>
      <Head>
        <title>ID Forgery Detector</title>
      </Head>

      <div style={{ minHeight: "100vh", background: "#f5f4f0" }}>

        {/* ── Header ── */}
        <header style={{
          background: "#1a1a1a", color: "#fff",
          padding: "0 24px", height: 56,
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 20 }}>🔍</span>
            <span style={{ fontFamily: "Syne, sans-serif", fontWeight: 700, fontSize: 16, letterSpacing: "0.03em" }}>
              ID Forgery Detector
            </span>
          </div>
          <span style={{ fontSize: 11, color: "#666", letterSpacing: "0.08em" }}>
            POWERED BY GEMINI + CV
          </span>
        </header>

        {/* ── Body ── */}
        <div style={{
          maxWidth: 520,
          margin: "0 auto",
          padding: "40px 20px 80px",
        }}>

          {/* Title */}
          <div style={{ textAlign: "center", marginBottom: 32 }}>
            <h1 style={{
              fontFamily: "Syne, sans-serif",
              fontSize: "clamp(26px, 6vw, 36px)",
              fontWeight: 800,
              lineHeight: 1.15,
              color: "#1a1a1a",
              marginBottom: 10,
            }}>
              Is this ID real or fake?
            </h1>
            <p style={{ fontSize: 14, color: "#666", lineHeight: 1.6 }}>
              Upload an ID document image. We'll analyze it using AI vision and forensic checks.
            </p>
          </div>

          {/* ── Upload card ── */}
          {!report && (
            <div style={{
              background: "#fff",
              borderRadius: 16,
              padding: 28,
              boxShadow: "0 2px 20px rgba(0,0,0,0.06)",
              marginBottom: 16,
            }}>
              {!file ? (
                <div
                  onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
                  onDragLeave={() => setDrag(false)}
                  onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files[0]); }}
                  onClick={() => inputRef.current?.click()}
                  style={{
                    border: `2px dashed ${drag ? "#1a1a1a" : "#ddd"}`,
                    borderRadius: 12,
                    padding: "44px 20px",
                    textAlign: "center",
                    cursor: "pointer",
                    background: drag ? "#f9f9f9" : "transparent",
                    transition: "all 0.2s",
                  }}
                >
                  <div style={{ fontSize: 40, marginBottom: 12 }}>🪪</div>
                  <p style={{ fontWeight: 600, fontSize: 15, marginBottom: 6 }}>
                    Drop your ID document here
                  </p>
                  <p style={{ fontSize: 13, color: "#999", marginBottom: 16 }}>
                    or click to browse — JPEG / PNG · max 10 MB
                  </p>
                  <span style={{
                    display: "inline-block",
                    background: "#1a1a1a", color: "#fff",
                    borderRadius: 8, padding: "9px 22px",
                    fontSize: 13, fontWeight: 600,
                  }}>
                    Choose File
                  </span>
                  <input ref={inputRef} type="file" accept=".jpg,.jpeg,.png" style={{ display: "none" }}
                    onChange={(e) => pick(e.target.files?.[0])} />
                </div>
              ) : (
                <div style={{ animation: "fadeUp 0.3s ease" }}>
                  {/* Preview */}
                  <div style={{
                    borderRadius: 10, overflow: "hidden",
                    border: "1px solid #eee", marginBottom: 20,
                    background: "#fafafa",
                  }}>
                    <img src={preview!} alt="ID preview"
                      style={{ width: "100%", maxHeight: 220, objectFit: "contain", display: "block" }} />
                  </div>
                  <p style={{ fontSize: 12, color: "#999", marginBottom: 16, textAlign: "center" }}>
                    {file.name} · {(file.size / 1024).toFixed(0)} KB
                  </p>

                  {/* Buttons */}
                  <div style={{ display: "flex", gap: 10 }}>
                    <button
                      onClick={analyze}
                      disabled={loading}
                      style={{
                        flex: 1,
                        background: loading ? "#ccc" : "#1a1a1a",
                        color: "#fff",
                        border: "none",
                        borderRadius: 10,
                        padding: "13px 0",
                        fontSize: 14, fontWeight: 600,
                        cursor: loading ? "not-allowed" : "pointer",
                        display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
                        transition: "background 0.2s",
                      }}
                    >
                      {loading ? (
                        <>
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                            stroke="#fff" strokeWidth="2.5"
                            style={{ animation: "spin 0.8s linear infinite" }}>
                            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" />
                          </svg>
                          Analyzing…
                        </>
                      ) : "🔍 Analyze Document"}
                    </button>
                    <button onClick={reset} style={{
                      background: "transparent",
                      border: "1.5px solid #ddd",
                      borderRadius: 10, padding: "13px 18px",
                      fontSize: 13, color: "#666", cursor: "pointer",
                    }}>
                      Reset
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Loading state */}
          {loading && (
            <div style={{
              background: "#fff", borderRadius: 16, padding: 24,
              boxShadow: "0 2px 20px rgba(0,0,0,0.06)",
              textAlign: "center", marginBottom: 16,
            }}>
              <div style={{ fontSize: 32, marginBottom: 12, animation: "pulse 1.5s infinite" }}>🔬</div>
              <p style={{ fontWeight: 600, marginBottom: 6 }}>Running forensic analysis…</p>
              <p style={{ fontSize: 12, color: "#999" }}>
                ELA · Noise · Edge · Blur · Metadata · Gemini AI
              </p>
            </div>
          )}

          {/* Error */}
          {error && (
            <div style={{
              background: "#fef2f2", border: "1px solid #fca5a5",
              borderRadius: 12, padding: "14px 18px",
              fontSize: 13, color: "#991b1b", marginBottom: 16,
              animation: "fadeUp 0.3s ease",
            }}>
              ⚠️ {error}
            </div>
          )}

          {/* ── Result card ── */}
          {report && colors && (
            <div style={{ animation: "fadeUp 0.4s ease" }}>

              {/* Big verdict */}
              <div style={{
                background: colors.bg,
                border: `2px solid ${colors.border}`,
                borderRadius: 16,
                padding: 28,
                textAlign: "center",
                marginBottom: 16,
                boxShadow: "0 2px 20px rgba(0,0,0,0.06)",
              }}>
                <div style={{ fontSize: 52, marginBottom: 10 }}>
                  {riskEmoji(report.risk_level)}
                </div>
                <div style={{
                  fontFamily: "Syne, sans-serif",
                  fontSize: 28, fontWeight: 800,
                  color: colors.text, marginBottom: 6,
                }}>
                  {report.risk_level}
                </div>
                <div style={{ fontSize: 13, color: colors.text, opacity: 0.7, marginBottom: 20 }}>
                  Risk Score: {report.risk_score} / 100
                </div>

                {/* Score bar */}
                <div style={{
                  height: 8, borderRadius: 4,
                  background: "rgba(0,0,0,0.08)",
                  overflow: "hidden",
                }}>
                  <div style={{
                    height: "100%",
                    width: `${report.risk_score}%`,
                    background: colors.bar,
                    borderRadius: 4,
                    animation: "fillBar 1s ease-out forwards",
                  }} />
                </div>
              </div>

              {/* Gemini AI verdict */}
              {report.gemini?.available && (
                <div style={{
                  background: "#fff",
                  borderRadius: 16, padding: 22,
                  boxShadow: "0 2px 20px rgba(0,0,0,0.06)",
                  marginBottom: 16,
                }}>
                  <div style={{
                    display: "flex", alignItems: "center", gap: 8,
                    marginBottom: 12,
                  }}>
                    <span style={{ fontSize: 18 }}>🤖</span>
                    <span style={{
                      fontFamily: "Syne, sans-serif",
                      fontWeight: 700, fontSize: 14,
                    }}>Gemini AI Says</span>
                    <span style={{
                      marginLeft: "auto",
                      fontSize: 11, color: "#666",
                      background: "#f5f4f0",
                      borderRadius: 6, padding: "2px 8px",
                    }}>
                      {report.gemini.confidence}% confident
                    </span>
                  </div>
                  <p style={{ fontSize: 13, color: "#444", lineHeight: 1.7 }}>
                    {report.gemini.reasoning}
                  </p>
                </div>
              )}

              {/* Forensic signals */}
              <div style={{
                background: "#fff",
                borderRadius: 16, padding: 22,
                boxShadow: "0 2px 20px rgba(0,0,0,0.06)",
                marginBottom: 16,
              }}>
                <div style={{
                  fontFamily: "Syne, sans-serif",
                  fontWeight: 700, fontSize: 14, marginBottom: 16,
                }}>
                  🔬 Forensic Signals
                </div>

                {/* ELA bar */}
                <div style={{ marginBottom: 14 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                    <span style={{ fontSize: 12, color: "#555" }}>ELA Score</span>
                    <span style={{ fontSize: 12, fontWeight: 600 }}>
                      {Math.round(report.analysis.ela_score * 100)}%
                    </span>
                  </div>
                  <div style={{ height: 6, borderRadius: 3, background: "#f0f0f0", overflow: "hidden" }}>
                    <div style={{
                      height: "100%",
                      width: `${report.analysis.ela_score * 100}%`,
                      background: report.analysis.ela_score > 0.6 ? "#ef4444"
                               : report.analysis.ela_score > 0.3 ? "#f59e0b" : "#10b981",
                      borderRadius: 3,
                    }} />
                  </div>
                </div>

                {/* Boolean flags */}
                {[
                  { label: "Noise Inconsistency",  val: report.analysis.noise_anomaly },
                  { label: "Edge Artifacts",        val: report.analysis.edge_artifacts },
                  { label: "Blur Inconsistency",    val: report.analysis.blur_inconsistency },
                  { label: "Metadata Suspicious",   val: report.analysis.metadata_flag },
                ].map((s) => (
                  <div key={s.label} style={{
                    display: "flex", alignItems: "center", justifyContent: "space-between",
                    padding: "8px 0",
                    borderTop: "1px solid #f5f4f0",
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <SignalDot active={s.val} />
                      <span style={{ fontSize: 13, color: "#444" }}>{s.label}</span>
                    </div>
                    <span style={{
                      fontSize: 11, fontWeight: 600,
                      color: s.val ? "#92400e" : "#065f46",
                      background: s.val ? "#fffbeb" : "#e8faf3",
                      padding: "2px 8px", borderRadius: 5,
                    }}>
                      {s.val ? "FLAGGED" : "CLEAR"}
                    </span>
                  </div>
                ))}
              </div>

              {/* Visuals */}
              {(report.ela_visual || report.edge_visual) && (
                <div style={{
                  background: "#fff",
                  borderRadius: 16, padding: 22,
                  boxShadow: "0 2px 20px rgba(0,0,0,0.06)",
                  marginBottom: 16,
                }}>
                  <div style={{
                    fontFamily: "Syne, sans-serif",
                    fontWeight: 700, fontSize: 14, marginBottom: 14,
                  }}>
                    🗺 Forensic Maps
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                    {report.ela_visual && (
                      <div>
                        <p style={{ fontSize: 10, color: "#999", marginBottom: 6, textAlign: "center" }}>
                          ELA Heatmap
                        </p>
                        <img src={report.ela_visual} alt="ELA"
                          style={{ width: "100%", borderRadius: 8, border: "1px solid #eee" }} />
                      </div>
                    )}
                    {report.edge_visual && (
                      <div>
                        <p style={{ fontSize: 10, color: "#999", marginBottom: 6, textAlign: "center" }}>
                          Edge Detection
                        </p>
                        <img src={report.edge_visual} alt="Edges"
                          style={{ width: "100%", borderRadius: 8, border: "1px solid #eee" }} />
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Processing info */}
              <div style={{
                fontSize: 11, color: "#aaa", textAlign: "center",
                marginBottom: 16,
              }}>
                Analyzed in {report.processing_time_ms} ms ·{" "}
                {report.validation.width}×{report.validation.height}px
              </div>

              {/* Actions */}
              <div style={{ display: "flex", gap: 10 }}>
                <button onClick={reset} style={{
                  flex: 1,
                  background: "#1a1a1a", color: "#fff",
                  border: "none", borderRadius: 10,
                  padding: "13px 0", fontSize: 14, fontWeight: 600,
                  cursor: "pointer",
                }}>
                  Analyze Another
                </button>
                <button onClick={() => {
                  const a = document.createElement("a");
                  a.href = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }));
                  a.download = "report.json"; a.click();
                }} style={{
                  background: "transparent",
                  border: "1.5px solid #ddd", borderRadius: 10,
                  padding: "13px 18px", fontSize: 13, color: "#666", cursor: "pointer",
                }}>
                  ↓ Export
                </button>
              </div>
            </div>
          )}

        </div>
      </div>
    </>
  );
}
