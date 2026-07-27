import { useEffect, useState } from "react";
import { askPrecedentChat, getSuggestedQuestions } from "../lib/api";
import type { ChatAnswer, DemoRole, SuggestedQuestion } from "../types/investigation";

interface Props {
  caseId: string;
  role: DemoRole;
}

interface Turn {
  question: string;
  answer: ChatAnswer | null;
  error: string | null;
  offline: boolean;
}

// Single-turn under the hood — each question is independent, no conversation
// history sent to the model (keeps the fixture-recording surface bounded:
// see scripts/record_chat_fixtures.py). The running list here is purely a
// client-side rendering choice so it still reads as a conversation.
export function PrecedentChat({ caseId, role }: Props) {
  const [suggested, setSuggested] = useState<SuggestedQuestion[] | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setSuggested(null);
    setTurns([]);
    getSuggestedQuestions(caseId, role)
      .then(setSuggested)
      .catch(() => setSuggested([]));
  }, [caseId, role]);

  async function ask(question: string, questionId?: string) {
    if (loading) return;
    setLoading(true);
    setTurns((t) => [...t, { question, answer: null, error: null, offline: false }]);
    try {
      const answer = await askPrecedentChat(caseId, role, questionId ? { questionId } : { question });
      setTurns((t) => {
        const next = [...t];
        next[next.length - 1] = { question, answer, error: null, offline: false };
        return next;
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to get an answer.";
      const offline = message.toLowerCase().includes("no cached response");
      setTurns((t) => {
        const next = [...t];
        next[next.length - 1] = { question, answer: null, error: message, offline };
        return next;
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="border border-purple-200 rounded-lg bg-white overflow-hidden">
      <div className="px-4 py-3 bg-purple-50 border-b border-purple-100">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold uppercase tracking-wide bg-purple-600 text-white px-1.5 py-0.5 rounded">
            Institutional memory
          </span>
          <span className="text-xs font-semibold uppercase tracking-wide text-purple-900">
            Ask About Prior Investigations
          </span>
        </div>
        <p className="text-xs text-purple-700 mt-1">
          Different from the AI Investigation above: this searches <strong>other</strong> cases' recorded findings
          and decisions — never this case's own evidence. Use it to check "have we seen this before," not to
          re-argue this case.
        </p>
      </div>

      <div className="p-4 space-y-4">
        {suggested && suggested.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {suggested.map((q) => (
              <button
                key={q.question_id}
                onClick={() => ask(q.text, q.question_id)}
                disabled={loading}
                className="text-xs px-3 py-1.5 rounded-full border border-brand-blue/30 text-brand-blue hover:bg-brand-blue/5 transition-colors disabled:opacity-40"
              >
                {q.text}
              </button>
            ))}
          </div>
        )}

        <div className="space-y-4">
          {turns.map((turn, i) => (
            <div key={i} className="space-y-2">
              <div className="text-sm text-slate-800 font-medium">{turn.question}</div>

              {!turn.answer && !turn.error && (
                <div className="text-xs text-slate-400">Searching prior investigations…</div>
              )}

              {turn.error && turn.offline && (
                <div className="text-xs border border-amber-300 bg-amber-50 text-amber-900 rounded-md p-3">
                  Live model access isn't available here — this question hasn't been pre-recorded for offline mode.
                  Try one of the suggested questions above.
                </div>
              )}
              {turn.error && !turn.offline && (
                <div className="text-xs border border-red-300 bg-red-50 text-red-800 rounded-md p-3">{turn.error}</div>
              )}

              {turn.answer && (
                <div className="text-sm text-slate-700 bg-slate-50 rounded-md p-3 space-y-2">
                  <p>{turn.answer.answer}</p>
                  {turn.answer.citations.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {turn.answer.citations.map((c, ci) => (
                        <span
                          key={ci}
                          title={c.note}
                          className={`text-[11px] font-mono px-1.5 py-0.5 rounded ${
                            turn.answer!.unverified_case_ids.includes(c.case_id)
                              ? "bg-amber-100 text-amber-700"
                              : "bg-slate-200 text-slate-600"
                          }`}
                        >
                          {c.case_id}
                        </span>
                      ))}
                    </div>
                  )}
                  {turn.answer.precedent_case_ids_considered.length === 0 && (
                    <p className="text-xs text-slate-400 italic">No prior investigations were available to draw on yet.</p>
                  )}
                  <div className="flex items-center gap-2 pt-1">
                    <span className="text-[11px] text-slate-400">Confidence: {(turn.answer.confidence * 100).toFixed(0)}%</span>
                    <span className="text-[11px] text-slate-400">
                      · {turn.answer.source === "live" ? "Live model call" : "Replayed (cached) response"}
                    </span>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (input.trim()) {
              ask(input.trim());
              setInput("");
            }
          }}
          className="flex gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about this case…"
            disabled={loading}
            className="flex-1 border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-blue/30 focus:border-brand-blue disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-4 py-2 rounded-md bg-brand-blue text-white text-sm font-medium disabled:opacity-40 hover:bg-brand-blue-dark transition-colors"
          >
            Ask
          </button>
        </form>
      </div>
    </div>
  );
}
