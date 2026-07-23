"use client";

import { useState } from "react";
import { Plus, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { InputGroup, InputGroupInput } from "@/components/ui/input-group";
import { useTags } from "@/features/taxonomy/hooks";

const MAX_TAGS = 10;

interface TagInputProps {
  value: string[];
  onChange: (names: string[]) => void;
}

// Distinct from the Explorer's TagFilterCombobox: this one lets the user
// type a brand-new tag name (the backend creates it on the fly), not just
// pick from existing tags. A plain controlled dropdown rather than the
// Popover/Command primitives, since those toggle open on trigger click —
// which would fight with keeping the list open while the user types.
export function TagInput({ value, onChange }: TagInputProps) {
  const [text, setText] = useState("");
  const [focused, setFocused] = useState(false);
  const { data: existingTags } = useTags();

  const normalized = (s: string) => s.trim().toLowerCase();
  const selectedSet = new Set(value.map(normalized));

  function addTag(name: string) {
    const trimmed = name.trim();
    if (!trimmed || value.length >= MAX_TAGS || selectedSet.has(normalized(trimmed))) return;
    onChange([...value, trimmed]);
    setText("");
  }

  function removeTag(name: string) {
    onChange(value.filter((t) => t !== name));
  }

  const suggestions = (existingTags ?? [])
    .filter((tag) => !selectedSet.has(normalized(tag.name)))
    .filter((tag) => !text || tag.name.toLowerCase().includes(text.toLowerCase()))
    .slice(0, 6);

  const exactMatch = suggestions.some((tag) => normalized(tag.name) === normalized(text));
  const showDropdown = focused && value.length < MAX_TAGS && (suggestions.length > 0 || (text && !exactMatch));

  return (
    <div className="space-y-2">
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {value.map((name) => (
            <Badge key={name} variant="secondary" className="gap-1 pr-1">
              {name}
              <button
                type="button"
                aria-label={`Remove ${name} tag`}
                onClick={() => removeTag(name)}
                className="hover:bg-background/60 rounded-full p-0.5"
              >
                <X className="size-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}

      <div className="relative">
        <InputGroup>
          <InputGroupInput
            placeholder={value.length >= MAX_TAGS ? `Maximum ${MAX_TAGS} tags` : "Add a tag…"}
            disabled={value.length >= MAX_TAGS}
            value={text}
            onFocus={() => setFocused(true)}
            onBlur={() => setTimeout(() => setFocused(false), 120)}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === ",") {
                e.preventDefault();
                addTag(text);
              } else if (e.key === "Backspace" && !text && value.length > 0) {
                removeTag(value[value.length - 1]);
              }
            }}
          />
        </InputGroup>

        {showDropdown && (
          <div className="bg-popover text-popover-foreground ring-foreground/10 absolute top-full left-0 z-10 mt-1 w-full max-w-64 rounded-lg p-1 text-sm shadow-md ring-1">
            {suggestions.map((tag) => (
              <button
                key={tag.id}
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => addTag(tag.name)}
                className="hover:bg-muted flex w-full items-center rounded-md px-2 py-1.5 text-left"
              >
                {tag.name}
              </button>
            ))}
            {text && !exactMatch && (
              <button
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => addTag(text)}
                className="hover:bg-muted flex w-full items-center gap-1.5 rounded-md px-2 py-1.5 text-left"
              >
                <Plus className="size-3.5" />
                Create &ldquo;{text}&rdquo;
              </button>
            )}
          </div>
        )}
      </div>
      <p className="text-muted-foreground text-xs">{value.length}/{MAX_TAGS} tags</p>
    </div>
  );
}
