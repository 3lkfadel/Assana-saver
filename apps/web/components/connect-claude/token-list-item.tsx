/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
// plane imports
import { Button } from "@makeplane/propel/components/button";
import { useTranslation } from "@plane/i18n";
import type { IApiToken } from "@plane/types";
import { cn, renderFormattedDate } from "@plane/utils";
// components
import { DeleteApiTokenModal } from "@/components/api-token/delete-token-modal";

/** A token expiring within this many days shows a warning. */
const EXPIRY_WARNING_DAYS = 14;

const isExpiringSoon = (expiredAt: string): boolean =>
  new Date(expiredAt).getTime() - Date.now() < EXPIRY_WARNING_DAYS * 24 * 60 * 60 * 1000;

type Props = {
  token: IApiToken;
};

export function ClaudeTokenListItem({ token }: Props) {
  const [isRevokeModalOpen, setIsRevokeModalOpen] = useState(false);
  const { t } = useTranslation();

  const expiringSoon = token.is_active && !!token.expired_at && isExpiringSoon(token.expired_at);
  const date = token.expired_at ? renderFormattedDate(token.expired_at) : undefined;
  const status = !token.is_active
    ? t("account_settings.connect_claude.expired")
    : !token.expired_at
      ? t("account_settings.connect_claude.never_expires")
      : expiringSoon
        ? t("account_settings.connect_claude.expires_soon", { date })
        : t("account_settings.connect_claude.expires_on", { date });

  return (
    <>
      <DeleteApiTokenModal isOpen={isRevokeModalOpen} onClose={() => setIsRevokeModalOpen(false)} tokenId={token.id} />
      <div className="flex items-center justify-between gap-4 border-b border-subtle py-3">
        <div className="flex min-w-0 flex-col gap-1">
          <span className="truncate text-13 font-medium text-primary">{token.label}</span>
          <span
            className={cn("text-11", {
              "text-placeholder": !expiringSoon,
              "text-warning-primary": expiringSoon,
              "text-danger-primary": !token.is_active,
            })}
          >
            {status}
          </span>
        </div>
        <Button
          variant="secondary"
          size="sm"
          stretch="auto"
          label={t("account_settings.connect_claude.revoke")}
          onClick={() => setIsRevokeModalOpen(true)}
        />
      </div>
    </>
  );
}
