import { sourceLabel } from "@/features/archive/labels";
import { translateColumnLabel, translateStatusLabel } from "@/lib/workflow-labels";
import { t } from "@/i18n";

import type { BreakdownItem } from "./types";

const CYCLE_BUCKET_KEYS: Record<string, string> = {
  bucket_0_1d: "analytics.cycleBucket0to1d",
  bucket_1_3d: "analytics.cycleBucket1to3d",
  bucket_3_7d: "analytics.cycleBucket3to7d",
  bucket_7d_plus: "analytics.cycleBucket7dPlus",
};

export function columnBreakdownLabel(item: BreakdownItem): string {
  return translateColumnLabel(item.name ?? item.key, item.system_type);
}

export function telegramActionLabel(slug: string): string {
  return translateStatusLabel(null, slug);
}

export function cycleBucketLabel(bucket: string): string {
  const key = CYCLE_BUCKET_KEYS[bucket];
  return key ? t(key) : bucket;
}

export { sourceLabel };
