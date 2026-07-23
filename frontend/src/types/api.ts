export type UserRole = "EMPLOYEE" | "REVIEWER" | "ADMIN";

export interface ApiErrorField {
  field: string;
  message: string;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    correlationId: string;
    fields?: ApiErrorField[];
  };
}

export interface PagedResponse<T> {
  items: T[];
  page: number;
  size: number;
  total: number;
  totalPages: number;
}
