import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";

import { useI18n } from "../i18n/useI18n.js";
import { normalizeEntryKind, normalizeEntryText } from "../utils/eventHelpers.js";

const MARKDOWN_PLUGINS = [remarkGfm, remarkBreaks];

export default function ChatTranscript({
  entries,
  transcriptRef,
  isThinking = false,
  thinkingAgent = "Assistant",
  emptyState,
  hiddenKinds = [],
  allowedKinds = null,
  showMeta = true,
  className = "",
}) {
  const { t } = useI18n();
  const hiddenSet = new Set(hiddenKinds);
  const allowedSet = allowedKinds ? new Set(allowedKinds) : null;
  const lastEntryIndex = entries.length - 1;
  const lastEntry = lastEntryIndex >= 0 ? entries[lastEntryIndex] : null;
  const lastEntryKind = lastEntry ? normalizeEntryKind(lastEntry.kind) : null;
  const hideActiveMessageDuringThinking =
    isThinking && lastEntry?.role === "assistant" && lastEntryKind === "message";

  const visibleEntries = entries.filter((entry, index) => {
    const kind = normalizeEntryKind(entry.kind);

    // Keep active assistant message and thinking indicator mutually exclusive while thinking.
    if (hideActiveMessageDuringThinking && index === lastEntryIndex) {
      return false;
    }
    if (entry.role === "user") {
      return true;
    }
    if (hiddenSet.has(kind)) {
      return false;
    }
    if (allowedSet && !allowedSet.has(kind)) {
      return false;
    }
    return true;
  });

  return (
    <section ref={transcriptRef} className={`transcript ${className}`.trim()}>
      {visibleEntries.length === 0 ? (
        <div className="empty-state">{emptyState}</div>
      ) : (
        visibleEntries.map((entry) => {
          const kind = normalizeEntryKind(entry.kind);
          const text = normalizeEntryText(entry.text);
          const roleClass = typeof entry.role === "string" ? entry.role : "assistant";

          return (
            <article key={entry.id} className={`entry entry-${roleClass} kind-${kind.replace(/_/g, "-")}`}>
              {showMeta ? (
                <div className="meta">
                  {entry.agent} <span>{kind}</span>
                </div>
              ) : null}
              <div className="entry-markdown">
                <ReactMarkdown
                  remarkPlugins={MARKDOWN_PLUGINS}
                  components={{
                    a: ({ node, ...props }) => <a {...props} target="_blank" rel="noreferrer" />,
                  }}
                >
                  {text}
                </ReactMarkdown>
              </div>
            </article>
          );
        })
      )}

      {isThinking ? (
        <article key={`thinking-${thinkingAgent}`} className="entry entry-assistant kind-thinking">
          {showMeta ? (
            <div className="meta">
              {thinkingAgent} <span>{t("chat.thinking")}</span>
            </div>
          ) : null}
          <div className="thinking-dots" aria-label={t("chat.thinkingAria")}>
            <span>.</span>
            <span>.</span>
            <span>.</span>
          </div>
        </article>
      ) : null}
    </section>
  );
}
