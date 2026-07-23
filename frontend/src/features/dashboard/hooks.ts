"use client";

import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "./api";

export const dashboardKeys = {
  summary: ["dashboard", "summary"] as const,
  activity: (size: number) => ["dashboard", "activity", size] as const,
};

export function useDashboardSummary() {
  return useQuery({
    queryKey: dashboardKeys.summary,
    queryFn: dashboardApi.getSummary,
  });
}

export function useDashboardActivity(size = 8) {
  return useQuery({
    queryKey: dashboardKeys.activity(size),
    queryFn: () => dashboardApi.getActivity({ size }),
  });
}
