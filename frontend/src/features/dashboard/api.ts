import { apiClient } from "@/lib/api-client";
import type { DashboardSummary, PagedActivity } from "./types";

export const dashboardApi = {
  getSummary(): Promise<DashboardSummary> {
    return apiClient.get<DashboardSummary>("/dashboard/summary");
  },

  getActivity(params?: { page?: number; size?: number }): Promise<PagedActivity> {
    return apiClient.get<PagedActivity>("/dashboard/activity", params);
  },
};
