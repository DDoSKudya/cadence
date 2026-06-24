import { describe, expect, it } from "vitest";

import type { SettingsColumn } from "@/features/settings/types";
import {
  buildFullMeshTransitions,
  isTransitionAllowed,
  mergeOutgoingTransitions,
  transitionsFromMatrix,
} from "@/features/settings/workflow";

const columns: SettingsColumn[] = [
  { id: 1, name: "A", system_type: "backlog", color: "slate", position: 0, wip_limit: null },
  { id: 2, name: "B", system_type: "planned", color: "blue", position: 1, wip_limit: null },
  { id: 3, name: "C", system_type: "done", color: "green", position: 2, wip_limit: null },
];

describe("settings workflow helpers", () => {
  it("treats open workflow as allowing every transition", () => {
    const workflow = { enforced: false, transitions: [] };
    expect(isTransitionAllowed(workflow, 1, 2)).toBe(true);
  });

  it("builds a full mesh without self transitions", () => {
    expect(buildFullMeshTransitions(columns)).toEqual([
      { from_column_id: 1, to_column_id: 2 },
      { from_column_id: 1, to_column_id: 3 },
      { from_column_id: 2, to_column_id: 1 },
      { from_column_id: 2, to_column_id: 3 },
      { from_column_id: 3, to_column_id: 1 },
      { from_column_id: 3, to_column_id: 2 },
    ]);
  });

  it("bootstraps restrictions from an open workflow", () => {
    const workflow = { enforced: false, transitions: [] };
    const next = mergeOutgoingTransitions(workflow, 1, [2], columns);
    expect(next).toEqual([
      { from_column_id: 1, to_column_id: 2 },
      { from_column_id: 2, to_column_id: 1 },
      { from_column_id: 2, to_column_id: 3 },
      { from_column_id: 3, to_column_id: 1 },
      { from_column_id: 3, to_column_id: 2 },
    ]);
  });

  it("serializes matrix selections", () => {
    const matrix = {
      "1->2": true,
      "1->3": false,
      "2->1": true,
      "2->3": true,
      "3->1": false,
      "3->2": true,
    };
    expect(transitionsFromMatrix(columns, matrix)).toEqual([
      { from_column_id: 1, to_column_id: 2 },
      { from_column_id: 2, to_column_id: 1 },
      { from_column_id: 2, to_column_id: 3 },
      { from_column_id: 3, to_column_id: 2 },
    ]);
  });
});
