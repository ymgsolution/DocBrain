"use client";

import { SearchBox } from "@/components/shared/search-box";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { TagFilterCombobox } from "./tag-filter-combobox";
import { useCategories } from "@/features/taxonomy/hooks";
import type { DocumentListFilters, DocumentSort } from "@/features/documents/types";
import type { ReviewStatus } from "@/types/document";

const REVIEW_STATUS_OPTIONS: { value: ReviewStatus | "all"; label: string }[] = [
  { value: "all", label: "Any review status" },
  { value: "overdue", label: "Overdue" },
  { value: "due_soon", label: "Due soon" },
  { value: "ok", label: "Up to date" },
];

const SORT_OPTIONS: { value: DocumentSort; label: string }[] = [
  { value: "updated_at", label: "Last updated" },
  { value: "created_at", label: "Newest" },
  { value: "title", label: "Title (A–Z)" },
];

interface DocumentFiltersProps {
  filters: DocumentListFilters;
  onChange: (patch: Partial<DocumentListFilters>) => void;
}

export function DocumentFilters({ filters, onChange }: DocumentFiltersProps) {
  const { data: categories } = useCategories();

  const categoryLabels: Record<string, string> = { all: "All Categories" };
  categories?.forEach((category) => {
    categoryLabels[category.id] = category.name;
  });
  const reviewStatusLabels = Object.fromEntries(REVIEW_STATUS_OPTIONS.map((o) => [o.value, o.label]));
  const sortLabels = Object.fromEntries(SORT_OPTIONS.map((o) => [o.value, o.label]));

  return (
    <div className="flex flex-col gap-3">
      <SearchBox
        defaultValue={filters.q ?? ""}
        placeholder="Search documents…"
        onValueChange={(q) => onChange({ q: q || undefined })}
        className="max-w-md"
      />
      <div className="flex flex-wrap items-center gap-2">
        <Select
          value={filters.categoryId ?? "all"}
          onValueChange={(value) => onChange({ categoryId: value === "all" || !value ? undefined : value })}
        >
          <SelectTrigger size="sm" className="w-44">
            <SelectValue placeholder="All Categories">
              {(value: string) => categoryLabels[value] ?? "All Categories"}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            {categories?.map((category) => (
              <SelectItem key={category.id} value={category.id}>
                {category.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={filters.reviewStatus ?? "all"}
          onValueChange={(value) =>
            onChange({ reviewStatus: value === "all" ? undefined : (value as ReviewStatus) })
          }
        >
          <SelectTrigger size="sm" className="w-44">
            <SelectValue placeholder="Any review status">
              {(value: string) => reviewStatusLabels[value] ?? "Any review status"}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {REVIEW_STATUS_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <TagFilterCombobox
          selectedTagIds={filters.tagId ?? []}
          onChange={(tagId) => onChange({ tagId })}
        />

        <Select
          value={filters.sort ?? "updated_at"}
          onValueChange={(value) => onChange({ sort: value as DocumentSort })}
        >
          <SelectTrigger size="sm" className="ml-auto w-40">
            <SelectValue>{(value: string) => sortLabels[value] ?? "Sort"}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            {SORT_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
