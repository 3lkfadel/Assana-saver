/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
import { observer } from "mobx-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
// store
import type { TAssistantMessage } from "@/store/assistant.store";

const KNOWN_TOOLS = new Set([
  "list_projects",
  "search_work_items",
  "get_work_item",
  "project_progress",
  "deadline_report",
  "member_workload",
]);

const KNOWN_ERRORS = new Set([
  "refusal",
  "truncated",
  "too_many_steps",
  "invalid_api_key",
  "permission_denied",
  "model_not_found",
  "rate_limited",
  "connection_error",
]);

const markdownComponents = {
  p: ({ children }: { children?: ReactNode }) => <p className="mb-2 last:mb-0">{children}</p>,
  ul: ({ children }: { children?: ReactNode }) => <ul className="mb-2 ml-5 list-disc space-y-1">{children}</ul>,
  ol: ({ children }: { children?: ReactNode }) => <ol className="mb-2 ml-5 list-decimal space-y-1">{children}</ol>,
  strong: ({ children }: { children?: ReactNode }) => (
    <strong className="font-semibold text-primary">{children}</strong>
  ),
  h1: ({ children }: { children?: ReactNode }) => <h3 className="mb-2 font-semibold text-primary">{children}</h3>,
  h2: ({ children }: { children?: ReactNode }) => <h3 className="mb-2 font-semibold text-primary">{children}</h3>,
  h3: ({ children }: { children?: ReactNode }) => <h4 className="mb-2 font-semibold text-primary">{children}</h4>,
  table: ({ children }: { children?: ReactNode }) => (
    <div className="mb-2 overflow-x-auto">
      <table className="w-full border-collapse text-12">{children}</table>
    </div>
  ),
  th: ({ children }: { children?: ReactNode }) => (
    <th className="border border-subtle bg-layer-1 px-2 py-1 text-left font-medium text-primary">{children}</th>
  ),
  td: ({ children }: { children?: ReactNode }) => <td className="border border-subtle px-2 py-1">{children}</td>,
  code: ({ children }: { children?: ReactNode }) => (
    <code className="rounded-sm bg-layer-1 px-1 py-0.5 text-12">{children}</code>
  ),
};

type TAssistantMessageProps = {
  message: TAssistantMessage;
  isStreaming: boolean;
};

export const AssistantMessage = observer(function AssistantMessage(props: TAssistantMessageProps) {
  const { message, isStreaming } = props;
  const { t } = useTranslation();

  if (message.role === "user")
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-lg bg-accent-subtle px-3 py-2 text-13 whitespace-pre-wrap text-primary">
          {message.content}
        </div>
      </div>
    );

  const toolLabel = message.activeTool
    ? t(KNOWN_TOOLS.has(message.activeTool) ? `assistant.tools.${message.activeTool}` : "assistant.tools.default")
    : undefined;
  const isWaiting = isStreaming && !message.content && !message.error;

  return (
    <div className="flex flex-col gap-1.5 text-13 text-secondary">
      {message.content && (
        <div className="break-words">
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
            {message.content}
          </ReactMarkdown>
        </div>
      )}
      {(toolLabel || isWaiting) && (
        <div className="flex items-center gap-2 text-12 text-tertiary">
          <span className="size-1.5 animate-pulse rounded-full bg-accent-primary" />
          {toolLabel ?? t("assistant.tools.default")}
        </div>
      )}
      {message.error && (
        <div
          className={cn(
            "rounded-md border border-danger-subtle bg-danger-subtle px-3 py-2 text-12 text-danger-primary"
          )}
        >
          {t(KNOWN_ERRORS.has(message.error) ? `assistant.errors.${message.error}` : "assistant.errors.generic")}
        </div>
      )}
    </div>
  );
});
