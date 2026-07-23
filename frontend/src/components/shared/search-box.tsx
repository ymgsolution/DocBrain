"use client";

import { Search, X } from "lucide-react";
import { useRef, useState } from "react";
import { InputGroup, InputGroupAddon, InputGroupButton, InputGroupInput } from "@/components/ui/input-group";

interface SearchBoxProps {
  defaultValue?: string;
  placeholder?: string;
  onValueChange: (value: string) => void;
  debounceMs?: number;
  className?: string;
}

// Uncontrolled by design: the input owns its own keystrokes, and only calls
// onValueChange (debounced) after the user pauses. The caller decides what
// to do with the value — e.g. the Explorer updates the URL, which then
// re-renders this component fresh rather than fighting over controlled state.
export function SearchBox({ defaultValue = "", placeholder, onValueChange, debounceMs = 300, className }: SearchBoxProps) {
  const [value, setValue] = useState(defaultValue);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  function handleChange(next: string) {
    setValue(next);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => onValueChange(next), debounceMs);
  }

  function handleClear() {
    clearTimeout(timer.current);
    setValue("");
    onValueChange("");
  }

  return (
    <InputGroup className={className}>
      <InputGroupAddon>
        <Search className="size-4" />
      </InputGroupAddon>
      <InputGroupInput
        placeholder={placeholder}
        value={value}
        onChange={(e) => handleChange(e.target.value)}
      />
      {value && (
        <InputGroupAddon align="inline-end">
          <InputGroupButton size="icon-xs" aria-label="Clear search" onClick={handleClear}>
            <X className="size-3.5" />
          </InputGroupButton>
        </InputGroupAddon>
      )}
    </InputGroup>
  );
}
