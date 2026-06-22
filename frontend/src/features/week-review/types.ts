export interface WeekOpenTask {
  id: number;
  title: string;
  column_name: string;
}

export interface WeekReviewStats {
  tasks_total: number;
  tasks_closed: number;
  tasks_open: number;
}

export interface WeekReviewResponse {
  week: {
    id: number;
    iso_year: number;
    iso_week: number;
    starts_on: string;
    ends_on: string;
    review_notes: string;
    closed_at: string | null;
  };
  stats: WeekReviewStats;
  open_tasks: WeekOpenTask[];
}

export interface WeekCloseResult {
  week: WeekReviewResponse["week"];
  result: {
    week_id: number;
    carried_over: number;
    open_tasks_before_close: number;
  };
}
