/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Select, SelectContent, SelectItem, SelectList, SelectTrigger } from "@makeplane/propel/components/select";

export type TSteeringSelectOption<T extends string> = { value: T; label: string };

type TSteeringSelectProps<T extends string> = {
  value: T | null;
  options: TSteeringSelectOption<T>[];
  onChange: (value: T) => void;
  ariaLabel: string;
  placeholder?: string;
  variant?: "secondary" | "ghost";
  size?: "md" | "lg";
  disabled?: boolean;
};

/** A single-choice list over the referential (branch, entity, role, person). */
export function SteeringSelect<T extends string>(props: TSteeringSelectProps<T>) {
  const { value, options, onChange, ariaLabel, placeholder, variant = "secondary", size = "md", disabled } = props;

  return (
    <Select<T>
      items={Object.fromEntries(options.map((option) => [option.value, option.label]))}
      value={value}
      onValueChange={(next) => next && onChange(next)}
      disabled={disabled}
    >
      <SelectTrigger size={size} variant={variant} placeholder={placeholder} aria-label={ariaLabel} />
      <SelectContent side="bottom" align="start">
        <SelectList>
          {options.map((option) => (
            <SelectItem key={option.value} value={option.value} size={size} label={option.label} />
          ))}
        </SelectList>
      </SelectContent>
    </Select>
  );
}
