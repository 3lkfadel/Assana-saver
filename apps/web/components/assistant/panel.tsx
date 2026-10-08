/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { AiStarFourOutline, CloseOutline, RefreshOutline, SendOutline, StopOutline } from "@makeplane/propel/icons";
import { Icon } from "@makeplane/propel/components/icon";
import { IconButton } from "@makeplane/propel/components/icon-button";
import { Tooltip } from "@makeplane/propel/components/tooltip";
import { useTranslation } from "@plane/i18n";
// hooks
import { useAssistant } from "@/hooks/store/use-assistant";
// local imports
import { AssistantMessage } from "./message";

const SUGGESTIONS = [
  "assistant.suggestions.overdue",
  "assistant.suggestions.workload",
  "assistant.suggestions.projects",
];

/** Right-hand drawer hosting the conversation with the read-only project assistant. */
export const AssistantPanel = observer(function AssistantPanel() {
  const { workspaceSlug } = useParams();
  const { t } = useTranslation();
  const { isOpen, isStreaming, messages, context, close, ask, stop, clearConversation } = useAssistant();
  // states
  const [question, setQuestion] = useState("");
  // refs
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const lastMessage = messages.at(-1);

  // keep the latest answer in view while it streams
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages.length, lastMessage?.content, lastMessage?.activeTool]);

  if (!isOpen || !workspaceSlug) return null;

  const submit = (text: string) => {
    if (!text.trim() || isStreaming) return;
    void ask(workspaceSlug.toString(), text);
    setQuestion("");
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    submit(question);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit(question);
    }
  };

  const contextLabel = context?.work_item_id
    ? t("assistant.context_work_item")
    : context?.project_id
      ? t("assistant.context_project")
      : undefined;

  return (
    <aside
      aria-label={t("assistant.title")}
      className="shadow-lg fixed top-12 right-3 bottom-3 z-30 flex w-[420px] max-w-[calc(100vw-24px)] flex-col overflow-hidden rounded-lg border border-subtle bg-surface-1"
    >
      <div className="flex items-center gap-2 border-b border-subtle px-4 py-3">
        <AiStarFourOutline className="size-4 text-accent-primary" />
        <div className="flex min-w-0 flex-1 flex-col">
          <span className="text-14 font-semibold text-primary">{t("assistant.title")}</span>
          {contextLabel && <span className="truncate text-11 text-tertiary">{contextLabel}</span>}
        </div>
        <Tooltip label={t("assistant.new_conversation")}>
          <IconButton
            variant="ghost"
            size="sm"
            icon={<Icon icon={RefreshOutline} />}
            aria-label={t("assistant.new_conversation")}
            onClick={clearConversation}
            disabled={messages.length === 0}
          />
        </Tooltip>
        <Tooltip label={t("assistant.close")}>
          <IconButton
            variant="ghost"
            size="sm"
            icon={<Icon icon={CloseOutline} />}
            aria-label={t("assistant.close")}
            onClick={close}
          />
        </Tooltip>
      </div>

      <div ref={scrollRef} className="flex flex-1 flex-col gap-4 overflow-y-auto px-4 py-4">
        {messages.length === 0 ? (
          <div className="flex flex-col gap-3">
            <p className="text-13 text-secondary">{t("assistant.subtitle")}</p>
            <div className="flex flex-col gap-2">
              {SUGGESTIONS.map((key) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => submit(t(key))}
                  className="rounded-md border border-subtle px-3 py-2 text-left text-13 text-secondary transition-colors hover:bg-layer-1-hover hover:text-primary"
                >
                  {t(key)}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <AssistantMessage
              key={message.id}
              message={message}
              isStreaming={isStreaming && message.id === lastMessage?.id}
            />
          ))
        )}
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-2 border-t border-subtle px-4 py-3">
        <div className="flex items-end gap-2">
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            placeholder={t("assistant.placeholder")}
            aria-label={t("assistant.placeholder")}
            className="max-h-40 min-h-[44px] flex-1 resize-none rounded-md border border-subtle bg-surface-1 px-3 py-2 text-13 text-primary outline-none placeholder:text-placeholder focus:border-accent-strong"
          />
          {isStreaming ? (
            <Tooltip label={t("assistant.stop")}>
              <IconButton
                variant="secondary"
                size="md"
                icon={<Icon icon={StopOutline} />}
                aria-label={t("assistant.stop")}
                onClick={stop}
              />
            </Tooltip>
          ) : (
            <Tooltip label={t("assistant.send")}>
              <IconButton
                type="submit"
                variant="primary"
                size="md"
                icon={<Icon icon={SendOutline} />}
                aria-label={t("assistant.send")}
                disabled={!question.trim()}
              />
            </Tooltip>
          )}
        </div>
        <p className="text-11 text-tertiary">{t("assistant.read_only_note")}</p>
      </form>
    </aside>
  );
});
