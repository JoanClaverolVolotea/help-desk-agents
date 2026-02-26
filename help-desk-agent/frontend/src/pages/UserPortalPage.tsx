import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";

import ChatTranscript from "../components/ChatTranscript";
import Composer from "../components/Composer";
import ErrorBanner from "../components/ErrorBanner";
import StatusRow from "../components/StatusRow";
import { withLanguageHint } from "../i18n/chatLanguage";
import { useI18n } from "../i18n/useI18n";
import { chatStream, readableError, resetConversation } from "../api";
import { INTERNAL_EVENT_KINDS } from "../utils/eventHelpers";
import type { ChatStreamEvent, ConversationId, TranscriptEntry } from "../types";

function nextIdFactory(): () => string {
  let count = 0;
  return () => {
    count += 1;
    return `entry-${count}`;
  };
}

export default function UserPortalPage(): JSX.Element {
  const { language, t } = useI18n();
  const nextId = useMemo(() => nextIdFactory(), []);
  const transcriptRef = useRef<HTMLElement | null>(null);
  const defaultAgent = t("userPortal.defaultAgent");

  const [chatInput, setChatInput] = useState("");
  const [entries, setEntries] = useState<TranscriptEntry[]>([]);
  const [conversationId, setConversationId] = useState<ConversationId>(null);
  const [currentAgent, setCurrentAgent] = useState(defaultAgent);
  const [isSending, setIsSending] = useState(false);
  const [chatError, setChatError] = useState("");

  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [entries, isSending]);

  useEffect(() => {
    if (!conversationId && entries.length === 0) {
      setCurrentAgent(defaultAgent);
    }
  }, [conversationId, defaultAgent, entries.length]);

  const sendMessage = async (messageText: string): Promise<void> => {
    const userEntry: TranscriptEntry = {
      id: nextId(),
      role: "user",
      kind: "user",
      agent: "User",
      text: messageText,
    };

    const streamingEntryId = nextId();
    const streamingEntry: TranscriptEntry = {
      id: streamingEntryId,
      role: "assistant",
      kind: "message",
      agent: currentAgent,
      text: "",
    };

    setEntries((prev) => [...prev, userEntry, streamingEntry]);
    setChatError("");
    setIsSending(true);

    let hasStreamedText = false;
    const modelMessage = withLanguageHint(messageText, language);

    try {
      const finalPayload = await chatStream(
        modelMessage,
        conversationId,
        (streamEvent: ChatStreamEvent) => {
          if (!streamEvent || typeof streamEvent !== "object") {
            return;
          }
          const eventRecord = streamEvent as Record<string, unknown>;

          if (streamEvent.type === "start") {
            if (typeof eventRecord.conversation_id === "string") {
              setConversationId(eventRecord.conversation_id);
            }
            if (typeof eventRecord.current_agent === "string") {
              setCurrentAgent(eventRecord.current_agent);
            }
            return;
          }

          if (streamEvent.type === "agent_updated") {
            if (typeof eventRecord.agent === "string") {
              setCurrentAgent(eventRecord.agent);
            }
            return;
          }

          if (streamEvent.type === "text_delta") {
            const delta = typeof streamEvent.delta === "string" ? streamEvent.delta : "";
            if (!delta) {
              return;
            }
            hasStreamedText = true;
            setEntries((prev) =>
              prev.map((entry) =>
                entry.id === streamingEntryId ? { ...entry, text: `${entry.text ?? ""}${delta}` } : entry,
              ),
            );
            return;
          }

          if (streamEvent.type === "event") {
            const streamPayload = eventRecord.event;
            if (!streamPayload || typeof streamPayload !== "object") {
              return;
            }
            const payload = streamPayload as Record<string, unknown>;
            if (payload.kind !== "message") {
              return;
            }

            const assistantText = typeof payload.text === "string" ? payload.text : "";
            if (!hasStreamedText && assistantText) {
              hasStreamedText = true;
              setEntries((prev) =>
                prev.map((entry) =>
                  entry.id === streamingEntryId
                    ? {
                        ...entry,
                        agent: typeof payload.agent === "string" ? payload.agent : entry.agent,
                        kind: typeof payload.kind === "string" ? payload.kind : entry.kind,
                        text: assistantText,
                      }
                    : entry,
                ),
              );
            }
          }
        },
      );

      if (finalPayload?.conversation_id) {
        setConversationId(finalPayload.conversation_id);
      }
      if (finalPayload?.current_agent) {
        setCurrentAgent(finalPayload.current_agent);
      }
      if (!hasStreamedText) {
        setEntries((prev) => prev.filter((entry) => entry.id !== streamingEntryId));
      }
    } catch (error) {
      setEntries((prev) => prev.filter((entry) => entry.id !== streamingEntryId));
      setChatError(readableError(error));
    } finally {
      setIsSending(false);
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    const messageText = chatInput.trim();
    if (!messageText || isSending) {
      return;
    }
    setChatInput("");
    await sendMessage(messageText);
  };

  const handleResetConversation = async (): Promise<void> => {
    if (conversationId) {
      try {
        await resetConversation(conversationId);
      } catch (error) {
        setChatError(readableError(error));
      }
    }

    setEntries([]);
    setConversationId(null);
    setCurrentAgent(defaultAgent);
    setChatInput("");
  };

  const samplePrompts = [
    t("userPortal.sampleWifi"),
    t("userPortal.samplePasswordReset"),
    t("userPortal.sampleSoftware"),
  ];

  const handleSampleClick = (prompt: string): void => {
    if (isSending) {
      return;
    }
    setChatInput("");
    void sendMessage(prompt);
  };

  return (
    <div className="app-shell user-portal-shell">
      <header className="header user-portal-header">
        <div>
          <h1>{t("userPortal.title")}</h1>
          <p>{t("userPortal.description")}</p>
        </div>
        <Link to="/" className="tab tab-link user-back-link">
          {t("common.backToRoleSelection")}
        </Link>
      </header>

      <section className="tab-panel user-portal-panel">
        <StatusRow
          className="user-portal-status"
          items={[
            { label: t("common.fieldConversation"), value: conversationId ?? t("common.newValue") },
            { label: t("common.fieldCurrentAgent"), value: currentAgent },
          ]}
        />

        <ChatTranscript
          transcriptRef={transcriptRef}
          entries={entries}
          isThinking={isSending}
          thinkingAgent={currentAgent}
          emptyState={t("userPortal.emptyState")}
          hiddenKinds={Array.from(INTERNAL_EVENT_KINDS)}
          allowedKinds={["message"]}
          showMeta={false}
          className="user-portal-transcript"
        />

        {entries.length === 0 && !isSending ? (
          <div className="user-portal-samples">
            {samplePrompts.map((prompt) => (
              <button
                key={prompt}
                type="button"
                className="sample-button"
                onClick={() => handleSampleClick(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>
        ) : null}

        <Composer
          value={chatInput}
          onChange={setChatInput}
          onSubmit={handleSubmit}
          onReset={handleResetConversation}
          placeholder={t("userPortal.placeholder")}
          disabled={isSending}
          submitLabel={t("userPortal.submit")}
          sendingLabel={t("userPortal.sending")}
          resetLabel={t("userPortal.reset")}
          className="user-portal-composer"
        />

        <ErrorBanner message={chatError} />
      </section>
    </div>
  );
}
