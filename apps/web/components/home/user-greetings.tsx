/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane types
import { useTranslation } from "@plane/i18n";
import type { IUser } from "@plane/types";
// hooks
import { useCurrentTime } from "@/hooks/use-current-time";

export interface IUserGreetingsView {
  user: IUser;
}

/** The greeting of the home page, in Jost, with the date in the language of the interface. */
export function UserGreetingsView(props: IUserGreetingsView) {
  const { user } = props;
  // current time hook
  const { currentTime } = useCurrentTime();
  // store hooks
  const { t, currentLocale } = useTranslation();

  const timeZone = user?.user_timezone || undefined;
  const hour = Number(
    new Intl.DateTimeFormat("en-US", { timeZone, hour: "numeric", hourCycle: "h23" }).format(currentTime)
  );
  const greeting = hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";

  const day = new Intl.DateTimeFormat(currentLocale, {
    timeZone,
    weekday: "long",
    day: "numeric",
    month: "long",
  }).format(currentTime);
  const time = new Intl.DateTimeFormat(currentLocale, { timeZone, hour: "2-digit", minute: "2-digit" }).format(
    currentTime
  );

  return (
    <div className="mt-10 mb-8 flex flex-col gap-1">
      <p className="text-body-sm-medium text-tertiary first-letter:uppercase">
        {day}, {time}
      </p>
      <h2 className="font-heading text-32 leading-tight font-medium tracking-tight text-primary">
        {t(`home.greeting.${greeting}`, { name: user?.first_name || user?.display_name })}
      </h2>
    </div>
  );
}
