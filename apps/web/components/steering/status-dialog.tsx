/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import type { FormEvent } from "react";
import { Button } from "@makeplane/propel/components/button";
import {
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogHeading,
  DialogMain,
  DialogTitle,
} from "@makeplane/propel/components/dialog";
import { DateSelect } from "@plane/blocks/property-select";
import { useTranslation } from "@plane/i18n";
import { getDate, renderFormattedPayloadDate } from "@plane/utils";
// types
import type { TIssueSteeringPayload, TSteeringWaitingFor } from "@/services/steering.service";
import { STEERING_WAITING_FOR } from "@/services/steering.service";
// local imports
import { SteeringSelect } from "./select";

type TSteeringStatusDialogProps = {
  /** The status that needs more information: « En attente » needs its cause, « Terminé » its closure. */
  kind: "waiting" | "done" | null;
  onClose: () => void;
  onSubmit: (payload: TIssueSteeringPayload) => Promise<boolean>;
};

const textAreaClassName =
  "w-full rounded-md border border-subtle bg-surface-1 px-3 py-2 text-13 text-primary outline-none placeholder:text-placeholder focus:border-accent-strong";

export function SteeringStatusDialog(props: TSteeringStatusDialogProps) {
  const { kind, onClose, onSubmit } = props;
  const { t } = useTranslation();
  const [waitingFor, setWaitingFor] = useState<TSteeringWaitingFor | null>(null);
  const [closureDate, setClosureDate] = useState<string | null>(renderFormattedPayloadDate(new Date()) ?? null);
  const [closureComment, setClosureComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const canSubmit = kind === "waiting" ? !!waitingFor : !!closureDate && !!closureComment.trim();

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!canSubmit || isSubmitting) return;
    setIsSubmitting(true);
    const saved = await onSubmit(
      kind === "waiting"
        ? { status: "waiting", waiting_for: waitingFor }
        : { status: "done", closure_date: closureDate, closure_comment: closureComment.trim() }
    );
    setIsSubmitting(false);
    if (saved) {
      setWaitingFor(null);
      setClosureComment("");
    }
  };

  return (
    <Dialog
      open={!!kind}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent size="sm">
        <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
          <DialogMain>
            <DialogHeader>
              <DialogHeading>
                <DialogTitle>
                  {kind === "waiting" ? t("steering.task.dialog.waiting_title") : t("steering.task.dialog.done_title")}
                </DialogTitle>
                <DialogDescription>
                  {kind === "waiting"
                    ? t("steering.task.dialog.waiting_description")
                    : t("steering.task.dialog.done_description")}
                </DialogDescription>
              </DialogHeading>
            </DialogHeader>
            <DialogBody tabIndex={0}>
              {kind === "waiting" ? (
                <SteeringSelect
                  value={waitingFor}
                  options={STEERING_WAITING_FOR.map((value) => ({
                    value,
                    label: t(`steering.task.waiting_for.${value}`),
                  }))}
                  placeholder={t("steering.task.fields.waiting_for")}
                  ariaLabel={t("steering.task.fields.waiting_for")}
                  onChange={setWaitingFor}
                />
              ) : (
                <div className="flex flex-col gap-3">
                  <div className="flex flex-col gap-1 text-12 text-secondary">
                    {t("steering.task.fields.closure_date")}
                    <DateSelect
                      value={closureDate ? (getDate(closureDate) ?? null) : null}
                      onChange={(date) => setClosureDate(date ? (renderFormattedPayloadDate(date) ?? null) : null)}
                      maxDate={new Date()}
                      variant="select-md"
                    />
                  </div>
                  <label className="flex flex-col gap-1 text-12 text-secondary">
                    {t("steering.task.fields.closure_comment")}
                    <textarea
                      rows={3}
                      value={closureComment}
                      onChange={(event) => setClosureComment(event.target.value)}
                      className={textAreaClassName}
                    />
                  </label>
                </div>
              )}
            </DialogBody>
          </DialogMain>
          <DialogActions>
            <Button variant="secondary" size="md" stretch="auto" label={t("common.cancel")} onClick={onClose} />
            <Button
              type="submit"
              variant="primary"
              size="md"
              stretch="auto"
              label={t("steering.save")}
              loading={isSubmitting}
              disabled={!canSubmit}
            />
          </DialogActions>
        </form>
      </DialogContent>
    </Dialog>
  );
}
