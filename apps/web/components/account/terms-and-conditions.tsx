/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { EAuthModes } from "@plane/constants";

interface TermsAndConditionsProps {
  authType?: EAuthModes;
}

/** Infinity Planning is internal to the group: there are no public terms to accept at sign-in. */
export function TermsAndConditions(_props: TermsAndConditionsProps) {
  return null;
}
