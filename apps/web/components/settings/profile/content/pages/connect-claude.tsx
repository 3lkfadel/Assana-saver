/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import useSWR, { mutate } from "swr";
// plane imports
import { Button } from "@makeplane/propel/components/button";
import { API_TOKENS_LIST } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { setToast } from "@plane/blocks/toast";
import { APITokenService } from "@plane/services";
import type { IApiToken } from "@plane/types";
import { cn } from "@plane/utils";
// components
import { ClaudeSetupInstructions, CopyableCode } from "@/components/connect-claude/setup-instructions";
import { ClaudeTokenListItem } from "@/components/connect-claude/token-list-item";
import { ProfileSettingsHeading } from "@/components/settings/profile/heading";
import { APITokenSettingsLoader } from "@/components/ui/loader/settings/api-token";

const apiTokenService = new APITokenService();

const VALIDITY_OPTIONS: { days: number | null; i18nKey: string }[] = [
  { days: 30, i18nKey: "account_settings.connect_claude.validity_30" },
  { days: 90, i18nKey: "account_settings.connect_claude.validity_90" },
  { days: 365, i18nKey: "account_settings.connect_claude.validity_365" },
  { days: null, i18nKey: "account_settings.connect_claude.validity_none" },
];

export const ConnectClaudeProfileSettings = observer(function ConnectClaudeProfileSettings() {
  // states
  const [validityDays, setValidityDays] = useState<number | null>(90);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedToken, setGeneratedToken] = useState<IApiToken | undefined>();
  // store hooks
  const { data: allTokens } = useSWR(API_TOKENS_LIST, () => apiTokenService.list());
  // translation
  const { t } = useTranslation();

  if (!allTokens) return <APITokenSettingsLoader />;

  const claudeTokens = allTokens.filter((token) => token.client === "claude");

  const handleGenerate = async () => {
    if (isGenerating) return;
    setIsGenerating(true);
    try {
      const token = await apiTokenService.createClientToken("claude", validityDays);
      setGeneratedToken(token);
      await mutate<IApiToken[]>(API_TOKENS_LIST, (prevData) => [token, ...(prevData ?? [])], false);
    } catch (error) {
      const message = (error as { error?: string } | undefined)?.error;
      setToast({ type: "error", title: t("error"), message });
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="flex size-full flex-col gap-8">
      <ProfileSettingsHeading
        title={t("account_settings.connect_claude.title")}
        description={t("account_settings.connect_claude.description")}
      />

      <section className="flex flex-col gap-3">
        <span className="text-body-sm-medium text-primary">{t("account_settings.connect_claude.validity")}</span>
        <div className="flex flex-wrap items-center gap-2">
          {VALIDITY_OPTIONS.map(({ days, i18nKey }) => (
            <button
              key={String(days)}
              type="button"
              aria-pressed={validityDays === days}
              onClick={() => setValidityDays(days)}
              className={cn(
                "rounded-md border-[0.5px] px-3 py-1.5 text-13 text-secondary hover:bg-layer-transparent-hover",
                {
                  "border-accent-strong bg-accent-subtle text-primary": validityDays === days,
                  "border-subtle": validityDays !== days,
                }
              )}
            >
              {t(i18nKey)}
            </button>
          ))}
          <Button
            variant="primary"
            size="md"
            stretch="auto"
            label={t("account_settings.connect_claude.generate")}
            loading={isGenerating}
            onClick={handleGenerate}
          />
        </div>
      </section>

      {generatedToken?.token && (
        <section className="flex flex-col gap-2">
          <span className="text-body-sm-medium text-primary">{t("account_settings.connect_claude.token_title")}</span>
          <p className="text-body-xs-regular text-warning-primary">
            {t("account_settings.connect_claude.token_warning")}
          </p>
          <CopyableCode code={generatedToken.token} />
        </section>
      )}

      <ClaudeSetupInstructions token={generatedToken?.token} />

      <section className="flex flex-col">
        <span className="text-body-sm-medium text-primary">{t("account_settings.connect_claude.tokens")}</span>
        {claudeTokens.length > 0 ? (
          <div className="mt-2">
            {claudeTokens.map((token) => (
              <ClaudeTokenListItem key={token.id} token={token} />
            ))}
          </div>
        ) : (
          <p className="mt-2 text-body-xs-regular text-tertiary">{t("account_settings.connect_claude.no_tokens")}</p>
        )}
      </section>
    </div>
  );
});
