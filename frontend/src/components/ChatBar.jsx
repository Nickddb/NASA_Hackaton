import { useEffect, useRef, useState } from "react";
import { Bot, ChevronDown, ChevronUp, SendHorizontal } from "lucide-react";

function renderText(text) {
  return text.split("\n").map((line, i) => {
    const parts = line.split(/(\*\*[^*]+\*\*)/g).map((p, j) =>
      p.startsWith("**") && p.endsWith("**") ? (
        <strong key={j} className="font-semibold text-white">
          {p.slice(2, -2)}
        </strong>
      ) : (
        <span key={j}>{p}</span>
      )
    );
    return (
      <p key={i} className={line.trim() ? "" : "h-1"}>
        {parts}
      </p>
    );
  });
}

export default function ChatBar({ onSendChat }) {
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    { id: "hello", role: "assistant", text: "Hi! How can I help you today?" },
  ]);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, open, sending]);

  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");

  const send = async (e) => {
    e?.preventDefault();
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    setOpen(true);
    setMessages((m) => [...m, { id: `u-${Date.now()}`, role: "user", text }]);
    setSending(true);
    try {
      const res = await onSendChat(text);
      setMessages((m) => [...m, { id: `a-${Date.now()}`, role: "assistant", text: res?.reply || "No response received." }]);
    } catch (err) {
      setMessages((m) => [...m, { id: `e-${Date.now()}`, role: "assistant", text: `Agent error: ${err?.message || "connection lost"}` }]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="relative">
      {open && (
        <div
          ref={scrollRef}
          className="absolute bottom-full left-0 right-0 mb-3 max-h-[50vh] space-y-3 overflow-y-auto rounded-2xl border border-[#3B82F6]/30 bg-[#0B1530]/95 p-4 shadow-[0_0_30px_-6px_rgba(59,130,246,0.5)] backdrop-blur-md"
        >
          {messages.map((m) => (
            <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[85%] space-y-1 rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                  m.role === "user" ? "bg-[#2563EB] text-white" : "border border-[#3B82F6]/30 bg-[#12204A] text-[#DBEAFE]"
                }`}
              >
                {renderText(m.text)}
              </div>
            </div>
          ))}
          {sending && <div className="text-xs text-[#94A3B8]">AstraCare is analyzing telemetry...</div>}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-[#34D399]/35 bg-gradient-to-r from-[#071D30]/85 via-[#072B33]/85 to-[#062C24]/85 p-3 shadow-[0_0_28px_-8px_rgba(16,185,129,0.45)] backdrop-blur-md">
        <Bot className="h-10 w-10 shrink-0 text-[#34D399]" strokeWidth={1.5} />

        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="flex min-h-[48px] min-w-[200px] flex-1 items-center justify-between gap-3 rounded-2xl rounded-bl-sm border border-[#10B981]/25 bg-[#0A2E36]/80 px-5 text-left text-sm text-white transition hover:bg-[#0D3B44]"
          title={open ? "Hide conversation" : "Show conversation"}
        >
          <span className="line-clamp-1">{sending ? "Thinking..." : lastAssistant?.text.replace(/\*\*/g, "")}</span>
          {open ? <ChevronDown className="h-4 w-4 shrink-0 text-[#6EE7B7]" /> : <ChevronUp className="h-4 w-4 shrink-0 text-[#6EE7B7]" />}
        </button>

        <form onSubmit={send} className="flex min-w-[240px] flex-1 items-center gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onFocus={() => messages.length > 1 && setOpen(true)}
            placeholder="Type your question..."
            disabled={sending}
            className="min-h-[48px] flex-1 rounded-full border border-[#34D399]/40 bg-[#051B24]/90 px-5 text-sm text-white placeholder-[#94A3B8] outline-none transition focus:border-[#34D399]"
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            aria-label="Send"
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-[#0EA5E9] to-[#10B981] text-white shadow-[0_0_16px_rgba(16,185,129,0.65)] transition hover:brightness-110 disabled:opacity-50"
          >
            <SendHorizontal className="h-5 w-5" />
          </button>
        </form>
      </div>
    </div>
  );
}
