import { useEffect, useMemo, useRef, useState } from "react";

import ChatTranscript from "../components/ChatTranscript.jsx";
import Composer from "../components/Composer.jsx";
import ErrorBanner from "../components/ErrorBanner.jsx";
import StatusRow from "../components/StatusRow.jsx";
import {
  adminAssistantChat,
  readableError,
  resetAdminAssistantConversation,
} from "../api.js";

function nextIdFactory() {
  let count = 0;
  return () => {
    count += 1;
    return `tech-entry-${count}`;
  };
}

export default function ITAssistantPage() {
  const nextId = useMemo(() => nextIdFactory(), []);
  const transcriptRef = useRef(null);

  const [input, setInput] = useState("");
  const [entries, setEntries] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [currentAgent, setCurrentAgent] = useState("Tech Team Assistant Triage");
  const [isSending, setIsSending] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [entries, isSending]);

  const sendMessage = async (messageText) => {
    const userEntry = {
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
      const data = await adminAssistantChat(messageText, conversationId);
      setConversationId(data.conversation_id);
      setCurrentAgent(data.current_agent);

      const agentEntries = data.events.map((event) => ({
        id: nextId(),
        role: "assistant",
        kind: event.kind,
        agent: event.agent,
        text: event.text,
      }));

      setEntries((prev) => [...prev, ...agentEntries]);
    } catch (error) {
      setErrorMessage(readableError(error));
    } finally {
      setIsSending(false);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const messageText = input.trim();
    if (!messageText || isSending) {
      return;
    }
    setInput("");
    await sendMessage(messageText);
  };

  const handleReset = async () => {
    if (conversationId) {
      try {
        await resetAdminAssistantConversation(conversationId);
      } catch (error) {
        setErrorMessage(readableError(error));
      }
    }

    setEntries([]);
    setConversationId(null);
    setCurrentAgent("Tech Team Assistant Triage");
    setInput("");
  };

  return (
    <section className="tab-panel tech-panel it-console-panel it-console-assistant">
      <StatusRow
        items={[
          { label: "Tech Session", value: conversationId ?? "new" },
          { label: "Current agent", value: currentAgent },
        ]}
      />

      <ChatTranscript
        transcriptRef={transcriptRef}
        entries={entries}
        isThinking={isSending}
        thinkingAgent={currentAgent}
        emptyState="Ask for help to manage categories and use-cases."
      />

      <Composer
        value={input}
        onChange={setInput}
        onSubmit={handleSubmit}
        onReset={handleReset}
        placeholder="Pide ayuda para crear categorias... / Ask how to create categories..."
        disabled={isSending}
        submitLabel="Enviar"
        sendingLabel="Enviando..."
        resetLabel="Nueva sesion"
      />

      <ErrorBanner message={errorMessage} />
    </section>
  );
}
