/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { CopyOutline } from "@makeplane/propel/icons";
// plane imports
import { MCP_URL } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { setToast } from "@plane/blocks/toast";
import { copyTextToClipboard } from "@plane/utils";
// hooks
import { usePlatformOS } from "@/hooks/use-platform-os";

export const TOKEN_PLACEHOLDER = "YOUR_TOKEN";
const SERVER_NAME = "infinity-planning";

/** The MCP server URL: VITE_MCP_URL, or /mcp on the app's own origin. */
export const getMcpUrl = (): string =>
  MCP_URL || (typeof window !== "undefined" ? `${window.location.origin}/mcp` : "/mcp");

export const getClaudeCodeCommand = (mcpUrl: string, token: string): string =>
  `claude mcp add --transport http ${SERVER_NAME} ${mcpUrl} --header "Authorization: Bearer ${token}"`;

/**
 * Where Node.js usually lives on macOS (installer, Homebrew on Intel and Apple silicon) and Linux: Claude Desktop
 * starts servers with a minimal PATH, without those folders, so npx would not be found.
 */
const DESKTOP_PATH = "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin";

/** Claude Desktop reaches a remote server through the mcp-remote bridge, which adds the token header. */
export const getClaudeDesktopConfig = (mcpUrl: string, token: string, platform: string): string =>
  JSON.stringify(
    {
      mcpServers: {
        [SERVER_NAME]: {
          command: "npx",
          args: [
            "-y",
            "mcp-remote",
            mcpUrl,
            ...(mcpUrl.startsWith("http://") ? ["--allow-http"] : []),
            "--header",
            "Authorization:${AUTH_HEADER}",
          ],
          // Windows keeps its own PATH, where the Node.js installer adds npx
          env: { AUTH_HEADER: `Bearer ${token}`, ...(platform === "Windows" ? {} : { PATH: DESKTOP_PATH }) },
        },
      },
    },
    null,
    2
  );

type TCodeBlockProps = {
  code: string;
};

export function CopyableCode({ code }: TCodeBlockProps) {
  const { t } = useTranslation();

  const handleCopy = () =>
    copyTextToClipboard(code).then(() =>
      setToast({ type: "success", title: t("account_settings.connect_claude.copied") })
    );

  return (
    <div className="relative rounded-md border-[0.5px] border-subtle bg-layer-1">
      <pre className="overflow-x-auto px-3 py-2 pr-10 text-12 leading-5 whitespace-pre text-secondary">{code}</pre>
      <button
        type="button"
        onClick={handleCopy}
        aria-label={t("account_settings.connect_claude.copy")}
        className="absolute top-2 right-2 grid place-items-center rounded-sm p-1 text-placeholder hover:text-primary"
      >
        <CopyOutline className="size-4" />
      </button>
    </div>
  );
}

type TSetupInstructionsProps = {
  token: string | undefined;
};

export function ClaudeSetupInstructions({ token }: TSetupInstructionsProps) {
  const { t } = useTranslation();
  const { platform } = usePlatformOS();
  const mcpUrl = getMcpUrl();
  const value = token ?? TOKEN_PLACEHOLDER;

  return (
    <div className="flex flex-col gap-5">
      {!token && (
        <p className="text-body-xs-regular text-tertiary">{t("account_settings.connect_claude.placeholder_hint")}</p>
      )}
      <section className="flex flex-col gap-2">
        <h6 className="text-body-sm-medium text-primary">Claude Code</h6>
        <p className="text-body-xs-regular text-tertiary">
          {t("account_settings.connect_claude.claude_code_description")}
        </p>
        <CopyableCode code={getClaudeCodeCommand(mcpUrl, value)} />
      </section>
      <section className="flex flex-col gap-2">
        <h6 className="text-body-sm-medium text-primary">Claude Desktop</h6>
        <p className="text-body-xs-regular text-tertiary">
          {t("account_settings.connect_claude.claude_desktop_description")}
        </p>
        <CopyableCode code={getClaudeDesktopConfig(mcpUrl, value, platform)} />
      </section>
    </div>
  );
}
