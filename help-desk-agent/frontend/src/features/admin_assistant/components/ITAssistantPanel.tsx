import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";

import ChatTranscript from "../../../shared/components/ChatTranscript";
import Composer from "../../../shared/components/Composer";
import ErrorBanner from "../../../shared/components/ErrorBanner";
import StatusRow from "../../../shared/components/StatusRow";
import { withLanguageHint } from "../../../shared/i18n/chatLanguage";
import { useI18n } from "../../../shared/i18n/useI18n";
import { readableError } from "../../../shared/api/errors";
import {
  adminAssistantChat,
  resetAdminAssistantConversation,
} from "../api/adminAssistantClient";
import type { ConversationId, TranscriptEntry } from "../../../shared/types";

function nextIdFactory(): () => string {
  let count = 0;
  return () => {
    count += 1;
    return `tech-entry-${count}`;
  };
}

interface ITAssistantPanelProps {
  isOpen?: boolean;
  onToggle?: () => void;
}

export default function ITAssistantPanel({
  isOpen = true,
  onToggle = () => {},
}: ITAssistantPanelProps): JSX.Element {
  const { language, t } = useI18n();
  const nextId = useMemo(() => nextIdFactory(), []);
  const transcriptRef = useRef<HTMLElement | null>(null);
  const defaultAgent = t("itConsole.assistant.defaultAgent");

  const [input, setInput] = useState("");
  const [entries, setEntries] = useState<TranscriptEntry[]>([]);
  const [conversationId, setConversationId] = useState<ConversationId>(null);
  const [currentAgent, setCurrentAgent] = useState(defaultAgent);
  const [isSending, setIsSending] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

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
      agent: "Tech Team",
      text: messageText,
    };

    setEntries((prev) => [...prev, userEntry]);
    setErrorMessage("");
    setIsSending(true);

    try {
      const data = await adminAssistantChat(withLanguageHint(messageText, language), conversationId);
      setConversationId(data.conversation_id);
      setCurrentAgent(data.current_agent);

      const agentEntries: TranscriptEntry[] = data.events.map((event) => ({
        id: nextId(),
        role: "assistant",
        kind: typeof event.kind === "string" ? event.kind : "message",
        agent: typeof event.agent === "string" ? event.agent : data.current_agent,
        text: event.text,
      }));

      setEntries((prev) => [...prev, ...agentEntries]);
    } catch (error) {
      setErrorMessage(readableError(error));
    } finally {
      setIsSending(false);
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    const messageText = input.trim();
    if (!messageText || isSending) {
      return;
    }
    setInput("");
    await sendMessage(messageText);
  };

  const handleReset = async (): Promise<void> => {
    if (conversationId) {
      try {
        await resetAdminAssistantConversation(conversationId);
      } catch (error) {
        setErrorMessage(readableError(error));
      }
    }

    setEntries([]);
    setConversationId(null);
    setCurrentAgent(defaultAgent);
    setInput("");
  };

  return (
    <section
      className={`tab-panel tech-panel it-console-panel it-console-assistant-panel ${isOpen ? "" : "collapsed"}`.trim()}
    >
      <div className="it-console-assistant-toolbar">
        <button
          type="button"
          className={`assistant-visibility-toggle ${isOpen ? "open" : "closed"}`}
          onClick={onToggle}
          aria-expanded={isOpen}
          aria-controls="it-console-assistant-pane"
        >
          {isOpen ? t("itConsole.assistant.hideChat") : t("itConsole.assistant.openChat")}
        </button>
      </div>

      {isOpen ? (
        <>
          <StatusRow
            items={[
              { label: t("itConsole.assistant.techSession"), value: conversationId ?? t("common.newValue") },
              { label: t("itConsole.assistant.currentAgent"), value: currentAgent },
            ]}
          />

          <ChatTranscript
            transcriptRef={transcriptRef}
            entries={entries}
            isThinking={isSending}
            thinkingAgent={currentAgent}
            emptyState={t("itConsole.assistant.emptyState")}
          />

          <Composer
            value={input}
            onChange={setInput}
            onSubmit={handleSubmit}
            onReset={handleReset}
            placeholder={t("itConsole.assistant.placeholder")}
            disabled={isSending}
            submitLabel={t("itConsole.assistant.submit")}
            sendingLabel={t("itConsole.assistant.sending")}
            resetLabel={t("itConsole.assistant.reset")}
          />

          <ErrorBanner message={errorMessage} />
        </>
      ) : null}
    </section>
  );
}
