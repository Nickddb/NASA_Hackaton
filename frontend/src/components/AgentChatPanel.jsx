import { useEffect, useRef, useState } from "react";

const QUICK_PROMPTS = [
  "Why is the crew member's status critical or warning right now?",
  "Evaluate fluid balance and kidney stone risk",
  "How is the radiation environment affecting vitals?",
  "What should we do for EVA fatigue and orthostatic intolerance?",
  "Explain the ML anomaly score and NASA-STD-3001 rules",
];

function FormattedReply({ text }) {
  if (!text) return null;
  const lines = text.split("\n");
  return (
    <div className="space-y-1.5 text-sm leading-relaxed text-[#113D2E]">
      {lines.map((line, i) => {
        const trimmed = line.trim();
        if (!trimmed) return <div key={i} className="h-1" />;
        const parts = trimmed.split(/(\*\*[^*]+\*\*)/g).map((part, idx) => {
          if (part.startsWith("**") && part.endsWith("**")) {
            return (
              <strong key={idx} className="font-semibold text-[#113D2E]">
                {part.slice(2, -2)}
              </strong>
            );
          }
          return <span key={idx}>{part}</span>;
        });
        if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
          return (
            <div key={i} className="flex gap-2 pl-1">
              <span className="text-[#059669] font-bold">•</span>
              <span>{parts}</span>
            </div>
          );
        }
        return <p key={i}>{parts}</p>;
      })}
    </div>
  );
}

export default function AgentChatPanel({ state, onSendChat }) {
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      role: "assistant",
      mode: "SYSTEM",
      text: "AstraCare Autonomous Flight Surgeon online. Ask me to run diagnostic assessments, check NASA-STD-3001 rules, analyze ML anomaly scores, or recommend countermeasures.",
      tool_trace: [],
      timestamp: "STANDBY",
    },
  ]);

  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, sending]);

  const handleSend = async (promptText) => {
    const trimmed = (promptText ?? input).trim();
    if (!trimmed || sending) return;

    const userMsg = {
      id: `u-${Date.now()}`,
      role: "user",
      text: trimmed,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!promptText) setInput("");
    setSending(true);

    try {
      const res = await onSendChat(trimmed);
      const assistantMsg = {
        id: `a-${Date.now()}`,
        role: "assistant",
        mode: res?.mode || "OFFLINE_DETERMINISTIC",
        text: res?.reply || "No diagnostic response received.",
        tool_trace: res?.tool_trace || [],
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: `e-${Date.now()}`,
          role: "assistant",
          mode: "ERROR",
          text: `Diagnostic agent error: ${err?.message || "Connection lost"}`,
          tool_trace: [],
          timestamp: "ERR",
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  const envLabel = state?.environment?.replaceAll("_", " ") || "ISS LEO";

  return (
    <section className="eco-card flex h-full min-h-[600px] flex-col rounded-3xl bg-white p-5">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#D5E8DD] pb-3.5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-[#113D2E] text-[#C8EE90] shadow-sm">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23-.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5"
              />
            </svg>
          </div>
          <div>
            <h2 className="text-base font-bold tracking-tight text-[#113D2E]">
              Autonomous Flight Surgeon
            </h2>
            <p className="text-xs text-[#476458]">
              Tool-Calling Clinical Agent • {envLabel}
            </p>
          </div>
        </div>

        <span className="inline-flex items-center gap-1.5 rounded-full border border-[#CBE2D5] bg-[#EFF9F2] px-3 py-1 text-[11px] font-semibold text-[#113D2E]">
          <span className="h-2 w-2 rounded-full bg-[#059669] animate-pulse" />
          ONBOARD AI READY
        </span>
      </div>

      {/* Quick Prompts Strip */}
      <div className="mt-3 rounded-2xl border border-[#CBE2D5] bg-[#EFF9F2] p-2.5">
        <div className="mb-1.5 px-1 text-[10px] font-semibold uppercase tracking-wider text-[#476458]">
          Quick Clinical Queries
        </div>
        <div className="flex flex-wrap gap-1.5">
          {QUICK_PROMPTS.map((q) => (
            <button
              key={q}
              type="button"
              disabled={sending}
              onClick={() => handleSend(q)}
              className="rounded-full border border-[#CBE2D5] bg-white px-3 py-1.5 text-left text-xs font-medium text-[#113D2E] transition hover:border-[#113D2E] hover:bg-[#C8EE90]/40 disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Messages Feed */}
      <div
        ref={scrollRef}
        className="mt-3 flex-1 space-y-3 overflow-y-auto rounded-2xl border border-[#E2EFE8] bg-[#F7FBF9] p-3.5"
      >
        {messages.map((m) => {
          const isUser = m.role === "user";
          return (
            <div key={m.id} className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}>
              <div
                className={`max-w-[92%] rounded-2xl px-4 py-3 shadow-sm ${
                  isUser
                    ? "bg-[#113D2E] text-white"
                    : "border border-[#CBE2D5] bg-white text-[#113D2E]"
                }`}
              >
                <div className="mb-1.5 flex items-center justify-between gap-3 text-[10px] font-semibold uppercase tracking-wider">
                  <span className={isUser ? "text-[#C8EE90]" : "text-[#059669]"}>
                    {isUser ? "CREW / FLIGHT SURGEON" : `ASTRACARE AGENT • ${m.mode}`}
                  </span>
                  <span className={isUser ? "text-white/70" : "text-[#476458]"}>{m.timestamp}</span>
                </div>

                {isUser ? (
                  <p className="text-sm leading-relaxed text-white">{m.text}</p>
                ) : (
                  <FormattedReply text={m.text} />
                )}

                {/* Tool Trace Pills */}
                {!isUser && m.tool_trace && m.tool_trace.length > 0 && (
                  <div className="mt-3 space-y-1.5 border-t border-[#E2EFE8] pt-2.5">
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-[#476458]">
                      Executed Clinical Tools
                    </div>
                    <div className="flex flex-col gap-1.5">
                      {m.tool_trace.map((t, idx) => {
                        const statusUpper = String(t.status || "").toUpperCase();
                        const badgeClass =
                          statusUpper === "CRITICAL"
                            ? "border-[#FCA5A5] bg-[#FEF2F2] text-[#991B1B]"
                            : statusUpper === "WARNING"
                            ? "border-[#FCD34D] bg-[#FFFBEB] text-[#92400E]"
                            : "border-[#A7F3D0] bg-[#ECFDF5] text-[#065F46]";
                        return (
                          <div
                            key={idx}
                            className="rounded-xl border border-[#CBE2D5] bg-[#EFF9F2] px-2.5 py-2 text-xs"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-1.5">
                              <span className="font-mono font-semibold text-[#113D2E]">
                                {t.tool_name}
                              </span>
                              <span
                                className={`rounded-full border px-2 py-0.5 text-[10px] font-bold ${badgeClass}`}
                              >
                                {t.status || "OK"}
                              </span>
                            </div>
                            {t.summary && (
                              <p className="mt-1 text-[11px] text-[#476458]">{t.summary}</p>
                            )}
                            {t.rule_or_score && (
                              <p className="mt-0.5 font-mono text-[10px] font-medium text-[#113D2E]">
                                {t.rule_or_score}
                              </p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {sending && (
          <div className="flex items-start">
            <div className="rounded-2xl border border-[#CBE2D5] bg-white px-4 py-3 text-xs font-medium text-[#476458] shadow-sm">
              Running NASA-STD-3001 clinical rules & ML anomaly assessment...
            </div>
          </div>
        )}
      </div>

      {/* Input Form */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="mt-3 flex items-center gap-2"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask the Autonomous Flight Surgeon..."
          disabled={sending}
          className="min-h-[44px] flex-1 rounded-full border border-[#CBE2D5] bg-[#F7FBF9] px-4 text-sm text-[#113D2E] placeholder-[#476458]/70 outline-none transition focus:border-[#113D2E] focus:bg-white"
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="min-h-[44px] rounded-full bg-[#113D2E] px-5 text-sm font-semibold text-white transition hover:bg-[#195440] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {sending ? "Thinking..." : "Send"}
        </button>
      </form>
    </section>
  );
}
