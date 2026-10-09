/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { action, makeObservable, observable, runInAction } from "mobx";
import { v4 as uuidv4 } from "uuid";
// services
import type { TAssistantContext, TAssistantStatus } from "@/services/assistant.service";
import { AssistantService } from "@/services/assistant.service";

export type TAssistantMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  /** Tool currently running while the answer is being prepared. */
  activeTool?: string;
  /** Error code returned by the stream, or the request error message. */
  error?: string;
};

export type TAssistantOpenOptions = {
  context?: TAssistantContext;
  /** Sent right away when provided (contextual shortcuts). */
  question?: string;
};

export interface IAssistantStore {
  // observables
  isOpen: boolean;
  isStreaming: boolean;
  context: TAssistantContext | undefined;
  messages: TAssistantMessage[];
  statusMap: Record<string, TAssistantStatus>;
  // actions
  fetchStatus: (workspaceSlug: string) => Promise<TAssistantStatus | undefined>;
  open: (workspaceSlug: string, options?: TAssistantOpenOptions) => void;
  close: () => void;
  ask: (workspaceSlug: string, question: string) => Promise<void>;
  stop: () => void;
  clearConversation: () => void;
}

export class AssistantStore implements IAssistantStore {
  // observables
  isOpen = false;
  isStreaming = false;
  context: TAssistantContext | undefined = undefined;
  messages: TAssistantMessage[] = [];
  statusMap: Record<string, TAssistantStatus> = {};
  // non-observables
  private abortController: AbortController | undefined = undefined;
  private workspaceSlug: string | undefined = undefined;
  // services
  private assistantService = new AssistantService();

  constructor() {
    makeObservable(this, {
      isOpen: observable.ref,
      isStreaming: observable.ref,
      context: observable.ref,
      messages: observable,
      statusMap: observable,
      fetchStatus: action,
      open: action,
      close: action,
      ask: action,
      stop: action,
      clearConversation: action,
    });
  }

  fetchStatus = async (workspaceSlug: string) => {
    try {
      const status = await this.assistantService.getStatus(workspaceSlug);
      runInAction(() => {
        this.statusMap[workspaceSlug] = status;
      });
      return status;
    } catch {
      return undefined;
    }
  };

  open = (workspaceSlug: string, options?: TAssistantOpenOptions) => {
    // a conversation belongs to one workspace
    if (this.workspaceSlug && this.workspaceSlug !== workspaceSlug) this.clearConversation();
    this.workspaceSlug = workspaceSlug;
    this.isOpen = true;
    if (options?.context) this.context = options.context;
    if (options?.question && !this.isStreaming) void this.ask(workspaceSlug, options.question);
  };

  close = () => {
    this.isOpen = false;
  };

  clearConversation = () => {
    this.stop();
    this.messages = [];
    this.context = undefined;
  };

  stop = () => {
    this.abortController?.abort();
    this.abortController = undefined;
    this.isStreaming = false;
  };

  ask = async (workspaceSlug: string, question: string) => {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || this.isStreaming) return;

    const history = this.messages
      .filter((message) => !message.error && message.content)
      .map((message) => ({ role: message.role, content: message.content }));
    const answerId = uuidv4();
    this.messages.push({ id: uuidv4(), role: "user", content: trimmedQuestion });
    this.messages.push({ id: answerId, role: "assistant", content: "" });
    this.isStreaming = true;
    const abortController = new AbortController();
    this.abortController = abortController;

    const updateAnswer = (update: (answer: TAssistantMessage) => void) =>
      runInAction(() => {
        const answer = this.messages.find((message) => message.id === answerId);
        if (answer) update(answer);
      });

    try {
      await this.assistantService.streamChat(
        workspaceSlug,
        { messages: [...history, { role: "user", content: trimmedQuestion }], context: this.context },
        (event) => {
          if (event.type === "status") updateAnswer((answer) => (answer.activeTool = event.tool));
          else if (event.type === "text")
            updateAnswer((answer) => {
              answer.activeTool = undefined;
              answer.content += event.text;
            });
          else if (event.type === "error") updateAnswer((answer) => (answer.error = event.code));
        },
        abortController.signal
      );
    } catch (error) {
      if (!abortController.signal.aborted)
        updateAnswer((answer) => (answer.error = error instanceof Error ? error.message : "unexpected_error"));
    } finally {
      updateAnswer((answer) => (answer.activeTool = undefined));
      runInAction(() => {
        if (this.abortController === abortController) {
          this.abortController = undefined;
          this.isStreaming = false;
        }
      });
    }
  };
}
