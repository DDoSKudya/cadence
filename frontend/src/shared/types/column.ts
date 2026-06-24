export interface ColumnMeta {
  id: number;
  name: string;
  system_type: string;
  color: string;
  position: number;
  wip_limit: number | null;
  is_locked?: boolean;
  bound_status_ids?: number[];
}
