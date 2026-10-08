/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

export type TAssistantStatus = {
  is_configured: boolean;
  is_allowed: boolean;
};

export type TAssistantContext = {
  project_id?: string;
  work_item_id?: string;
};

export type TAssistantChatMessage = {
  role: "user" | "assistant";
  content: string;
};

/** Server-sent events emitted by the assistant chat endpoint. */
export type TAssistantEvent =
  | { type: "status"; tool: string }
  | { type: "text"; text: string }
  | { type: "error"; code: string }
  | { type: "done" };

export class AssistantService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async getStatus(workspaceSlug: string): Promise<TAssistantStatus> {
    return this.get(`/api/workspaces/${workspaceSlug}/assistant/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /**
   * Streams the answer to the last user message. Resolves once the stream ends.
   * Throws an Error whose message is the API error (or `http_<status>`) when the request is rejected.
   */
  async streamChat(
    workspaceSlug: string,
    payload: { messages: TAssistantChatMessage[]; context?: TAssistantContext },
    onEvent: (event: TAssistantEvent) => void,
    signal?: AbortSignal
  ): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/workspaces/${workspaceSlug}/assistant/chat/`, {
      method: "POST",
      credentials: "include",
      // no `Accept: text/event-stream`: DRF content negotiation would reject it (406) before the view runs
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal,
    });
    if (!response.ok || !response.body) {
      const data = (await response.json().catch(() => undefined)) as { error?: string } | undefined;
      throw new Error(data?.error ?? `http_${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      // stream chunks must be read one after another
      // oxlint-disable-next-line no-await-in-loop
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      // events are separated by a blank line; keep the trailing partial event in the buffer
      const chunks = buffer.split("\n\n");
      buffer = chunks.pop() ?? "";
      for (const chunk of chunks) {
        const data = chunk
          .split("\n")
          .filter((line) => line.startsWith("data: "))
          .map((line) => line.slice("data: ".length))
          .join("\n");
        if (data) onEvent(JSON.parse(data) as TAssistantEvent);
      }
    }
  }
}
