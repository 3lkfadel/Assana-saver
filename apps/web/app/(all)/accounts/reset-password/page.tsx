/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { EAuthModes } from "@plane/constants";
// components
import { ResetPasswordForm } from "@/components/account/auth-forms/reset-password";
import { AuthHeader } from "@/components/auth-screens/header";
import { AuthScreenLayout } from "@/components/auth-screens/layout";
// helpers
import { EPageTypes } from "@/helpers/authentication.helper";
// layouts
import DefaultLayout from "@/layouts/default-layout";
import { AuthenticationWrapper } from "@/lib/wrappers/authentication-wrapper";

function ResetPasswordPage() {
  return (
    <DefaultLayout>
      <AuthenticationWrapper pageType={EPageTypes.NON_AUTHENTICATED}>
        <AuthScreenLayout>
          <AuthHeader type={EAuthModes.SIGN_IN} />
          <ResetPasswordForm />
        </AuthScreenLayout>
      </AuthenticationWrapper>
    </DefaultLayout>
  );
}

export default ResetPasswordPage;
