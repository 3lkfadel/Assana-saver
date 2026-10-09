/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { AiStarFourOutline } from "@makeplane/propel/icons";
import { Icon } from "@makeplane/propel/components/icon";
import { IconButton } from "@makeplane/propel/components/icon-button";
import { Tooltip } from "@makeplane/propel/components/tooltip";
import { useTranslation } from "@plane/i18n";
// hooks
import { useAssistant } from "@/hooks/store/use-assistant";
// local imports
import { AssistantPanel } from "./panel";

/** Top navigation entry point: shown only to users allowed to use a configured assistant. */
export const AssistantTrigger = observer(function AssistantTrigger() {
  const { workspaceSlug } = useParams();
  const { t } = useTranslation();
  const { isOpen, statusMap, fetchStatus, open, close } = useAssistant();
  const slug = workspaceSlug?.toString();

  useSWR(slug ? `ASSISTANT_STATUS_${slug}` : null, slug ? () => fetchStatus(slug) : null, {
    revalidateOnFocus: false,
  });

  const status = slug ? statusMap[slug] : undefined;
  if (!slug || !status?.is_configured || !status.is_allowed) return null;

  return (
    <>
      <Tooltip label={t("assistant.open")} side="bottom">
        <IconButton
          variant={isOpen ? "secondary" : "ghost"}
          size="md"
          icon={<Icon icon={AiStarFourOutline} />}
          aria-label={t("assistant.open")}
          aria-pressed={isOpen}
          onClick={() => (isOpen ? close() : open(slug))}
        />
      </Tooltip>
      <AssistantPanel />
    </>
  );
});
