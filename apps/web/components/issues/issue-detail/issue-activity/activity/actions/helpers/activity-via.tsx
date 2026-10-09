/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";

type Props = {
  via: string | undefined;
};

/** "via Claude" after the actor's name, for changes made through a Claude token. */
export function ActivityVia({ via }: Props) {
  const { t } = useTranslation();

  if (via !== "claude") return null;
  return <span className="text-tertiary"> {t("activity_via_claude")}</span>;
}
