/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { i18nInstance, initPromise } from "./instance";

/**
 * Calls `listener` with the current language once i18n is ready, then on every language change.
 * Lets code outside React (date formatting in @plane/utils) follow the interface language.
 */
export function onLanguageChange(listener: (language: string) => void): () => void {
  void initPromise.then(() => listener(i18nInstance.language));
  i18nInstance.on("languageChanged", listener);
  return () => i18nInstance.off("languageChanged", listener);
}
