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
          className="absolute bottom-full left-0 right-0 mb-3 max-h-[50vh] space-y-3 overflow-y-auto rounded-2xl border border-white/15 bg-[#0E1218]/98 p-4 shadow-[0_16px_42px_rgba(0,0,0,0.85)] backdrop-blur-md"
        >
          {messages.map((m) => (
            <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[85%] space-y-1 rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                  m.role === "user" ? "bg-sky-600 text-white" : "border border-white/12 bg-[#161B24] text-slate-100"
                }`}
              >
                {renderText(m.text)}
              </div>
            </div>
          ))}
          {sending && <div className="text-xs text-slate-400">AstraCare is analyzing telemetry...</div>}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-white/15 bg-[#0E1218] p-3 shadow-[0_12px_32px_rgba(0,0,0,0.75)]">
        <Bot className="h-10 w-10 shrink-0 text-sky-400" strokeWidth={1.5} />

        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="flex min-h-[48px] min-w-[200px] flex-1 items-center justify-between gap-3 rounded-2xl rounded-bl-sm border border-white/15 bg-[#151A22] px-5 text-left text-sm text-white transition hover:bg-[#1D232E] cursor-pointer"
          title={open ? "Hide conversation" : "Show conversation"}
        >
          <span className="line-clamp-1">{sending ? "Thinking..." : lastAssistant?.text.replace(/\*\*/g, "")}</span>
          {open ? <ChevronDown className="h-4 w-4 shrink-0 text-slate-300" /> : <ChevronUp className="h-4 w-4 shrink-0 text-slate-300" />}
        </button>

        <form onSubmit={send} className="flex min-w-[240px] flex-1 items-center gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onFocus={() => messages.length > 1 && setOpen(true)}
            placeholder="Type your question..."
            disabled={sending}
            className="min-h-[48px] flex-1 rounded-full border border-white/15 bg-[#07090D] px-5 text-sm text-white placeholder-slate-400 outline-none transition focus:border-sky-400"
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            aria-label="Send"
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-sky-600 text-white shadow-sm transition hover:bg-sky-500 disabled:opacity-50 cursor-pointer"
          >
            <SendHorizontal className="h-5 w-5" />
          </button>
        </form>
      </div>
    </div>
  );
}
