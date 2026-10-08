/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { AiStarFourOutline } from "@makeplane/propel/icons";
import { Icon } from "@makeplane/propel/components/icon";
import { IconButton } from "@makeplane/propel/components/icon-button";
import { Tooltip } from "@makeplane/propel/components/tooltip";
import { useTranslation } from "@plane/i18n";
// hooks
import { useAssistant } from "@/hooks/store/use-assistant";
import type { TAssistantContext } from "@/services/assistant.service";

type TAssistantQuickAction = {
  workspaceSlug: string;
  /** What the question is about: a work item (progress, deadline) or a project (delay report). */
  context: TAssistantContext;
};

/** Contextual shortcut that opens the assistant and asks about the current work item or project. */
export const AssistantQuickAction = observer(function AssistantQuickAction(props: TAssistantQuickAction) {
  const { workspaceSlug, context } = props;
  const { t } = useTranslation();
  const { statusMap, open } = useAssistant();

  const status = statusMap[workspaceSlug];
  if (!status?.is_configured || !status.is_allowed) return null;

  const isWorkItem = !!context.work_item_id;
  const label = t(isWorkItem ? "assistant.actions.work_item" : "assistant.actions.project");

  return (
    <Tooltip label={label}>
      <IconButton
        variant="secondary"
        size="md"
        icon={<Icon icon={AiStarFourOutline} />}
        aria-label={label}
        onClick={() =>
          open(workspaceSlug, {
            context,
            question: t(isWorkItem ? "assistant.prompts.work_item" : "assistant.prompts.project"),
          })
        }
      />
    </Tooltip>
  );
});
