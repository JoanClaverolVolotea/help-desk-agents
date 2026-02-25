import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";

import ChatTranscript from "../components/ChatTranscript.jsx";
import Composer from "../components/Composer.jsx";
import ErrorBanner from "../components/ErrorBanner.jsx";
import StatusRow from "../components/StatusRow.jsx";
import { chatStream, readableError, resetConversation } from "../api.js";
import { INTERNAL_EVENT_KINDS } from "../utils/eventHelpers.js";

function nextIdFactory() {
  let count = 0;
  return () => {
    count += 1;
    return `entry-${count}`;
  };
}

export default function UserPortalPage() {
  const nextId = useMemo(() => nextIdFactory(), []);
  const transcriptRef = useRef(null);

  const [chatInput, setChatInput] = useState("");
  const [entries, setEntries] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [currentAgent, setCurrentAgent] = useState("Help Desk Triage Agent");
  const [isSending, setIsSending] = useState(false);
  const [chatError, setChatError] = useState("");

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
      agent: "User",
      text: messageText,
    };

    const streamingEntryId = nextId();
    const streamingEntry = {
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

    try {
      const finalPayload = await chatStream(messageText, conversationId, (streamEvent) => {
        if (!streamEvent || typeof streamEvent !== "object") {
          return;
        }

        if (streamEvent.type === "start") {
          if (streamEvent.conversation_id) {
            setConversationId(streamEvent.conversation_id);
          }
          if (streamEvent.current_agent) {
            setCurrentAgent(streamEvent.current_agent);
          }
          return;
        }

        if (streamEvent.type === "agent_updated") {
          if (streamEvent.agent) {
            setCurrentAgent(streamEvent.agent);
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
              entry.id === streamingEntryId ? { ...entry, text: `${entry.text}${delta}` } : entry,
            ),
          );
          return;
        }

        if (streamEvent.type === "event" && streamEvent.event?.kind === "message") {
          const assistantText = typeof streamEvent.event.text === "string" ? streamEvent.event.text : "";
          if (!hasStreamedText && assistantText) {
            hasStreamedText = true;
            setEntries((prev) =>
              prev.map((entry) =>
                entry.id === streamingEntryId
                  ? {
                      ...entry,
                      agent: streamEvent.event.agent ?? entry.agent,
                      kind: streamEvent.event.kind ?? entry.kind,
                      text: assistantText,
                    }
                  : entry,
              ),
            );
          }
        }
      });

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

  const handleSubmit = async (event) => {
    event.preventDefault();
    const messageText = chatInput.trim();
    if (!messageText || isSending) {
      return;
    }
    setChatInput("");
    await sendMessage(messageText);
  };

  const handleResetConversation = async () => {
    if (conversationId) {
      try {
        await resetConversation(conversationId);
      } catch (error) {
        setChatError(readableError(error));
      }
    }

    setEntries([]);
    setConversationId(null);
    setCurrentAgent("Help Desk Triage Agent");
    setChatInput("");
  };

  const samplePrompts = [
    "My laptop won't connect to WiFi",
    "I need a password reset",
    "Software installation request",
  ];

  const handleSampleClick = (prompt) => {
    if (isSending) return;
    setChatInput("");
    sendMessage(prompt);
  };

  return (
    <div className="app-shell user-portal-shell">
      <header className="header user-portal-header">
        <div>
          <h1>User Portal / Portal Usuario</h1>
          <p>Describe your issue in chat and send it directly to the help desk.</p>
        </div>
        <Link to="/" className="tab tab-link user-back-link">
          Back to role selection
        </Link>
      </header>

      <section className="tab-panel user-portal-panel">
        <StatusRow
          className="user-portal-status"
          items={[
            { label: "Conversation", value: conversationId ?? "new" },
            { label: "Current agent", value: currentAgent },
          ]}
        />

        <ChatTranscript
          transcriptRef={transcriptRef}
          entries={entries}
          isThinking={isSending}
          thinkingAgent={currentAgent}
          emptyState="Hi! Describe your issue below, or try one of the quick prompts. / ¡Hola! Describe tu problema abajo, o prueba una de las opciones rápidas."
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
          placeholder="Describe your issue... / Describe tu problema..."
          disabled={isSending}
          submitLabel="Send"
          sendingLabel="Sending..."
          resetLabel="New conversation"
          className="user-portal-composer"
        />

        <ErrorBanner message={chatError} />
      </section>
    </div>
  );
}
