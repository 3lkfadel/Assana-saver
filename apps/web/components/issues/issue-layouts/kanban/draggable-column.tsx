/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { combine } from "@atlaskit/pragmatic-drag-and-drop/combine";
import { draggable, dropTargetForElements } from "@atlaskit/pragmatic-drag-and-drop/element/adapter";
import { attachClosestEdge, extractClosestEdge } from "@atlaskit/pragmatic-drag-and-drop-hitbox/closest-edge";
import { cn } from "@plane/utils";

export const KANBAN_COLUMN_DRAG_TYPE = "KANBAN_COLUMN";

export type TKanbanColumnDropEdge = "left" | "right";

/** True when the drag source is a whole kanban column (as opposed to a work item card). */
export const isKanbanColumnDrag = (data: Record<string | symbol, unknown> | undefined) =>
  data?.type === KANBAN_COLUMN_DRAG_TYPE;

type TDraggableKanbanColumn = {
  columnId: string;
  isEnabled: boolean;
  className?: string;
  headerClassName?: string;
  /** Doubles as the drag handle. Without a header the column cannot be dragged. */
  header?: ReactNode;
  children: ReactNode;
  onReorder: (sourceColumnId: string, targetColumnId: string, edge: TKanbanColumnDropEdge) => void;
};

/**
 * Kanban column that can be reordered by dragging its header onto another column.
 * When disabled it renders exactly like a plain column.
 */
export function DraggableKanbanColumn(props: TDraggableKanbanColumn) {
  const { columnId, isEnabled, className, headerClassName, header, children, onReorder } = props;
  // refs
  const columnRef = useRef<HTMLDivElement | null>(null);
  const headerRef = useRef<HTMLDivElement | null>(null);
  // states
  const [isDragging, setIsDragging] = useState(false);
  const [dropEdge, setDropEdge] = useState<TKanbanColumnDropEdge | null>(null);

  useEffect(() => {
    const column = columnRef.current;
    const handle = headerRef.current;
    if (!isEnabled || !column || !handle) return;

    const data = { type: KANBAN_COLUMN_DRAG_TYPE, id: columnId };
    const getEdge = (edgeData: Record<string | symbol, unknown>) => {
      const edge = extractClosestEdge(edgeData);
      return edge === "left" || edge === "right" ? edge : null;
    };

    return combine(
      draggable({
        element: column,
        dragHandle: handle,
        getInitialData: () => data,
        onDragStart: () => setIsDragging(true),
        onDrop: () => setIsDragging(false),
      }),
      dropTargetForElements({
        element: column,
        canDrop: ({ source }) => isKanbanColumnDrag(source.data) && source.data.id !== columnId,
        getData: ({ input, element }) => attachClosestEdge(data, { input, element, allowedEdges: ["left", "right"] }),
        onDrag: ({ self }) => setDropEdge(getEdge(self.data)),
        onDragLeave: () => setDropEdge(null),
        onDrop: ({ self, source }) => {
          setDropEdge(null);
          const edge = getEdge(self.data);
          if (edge) onReorder(String(source.data.id), columnId, edge);
        },
      })
    );
  }, [columnId, isEnabled, onReorder]);

  return (
    <div ref={columnRef} className={cn(className, { "opacity-50": isDragging })}>
      {dropEdge && (
        <div
          className={cn(
            "pointer-events-none absolute inset-y-0 z-[3] w-0.5 rounded-full bg-accent-primary",
            dropEdge === "left" ? "-left-[9px]" : "-right-[9px]"
          )}
        />
      )}
      {header && (
        <div ref={headerRef} className={cn(headerClassName, { "cursor-grab active:cursor-grabbing": isEnabled })}>
          {header}
        </div>
      )}
      {children}
    </div>
  );
}
