"use client";

import { useState } from "react";
import { Tags, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { useTags } from "@/features/taxonomy/hooks";

interface TagFilterComboboxProps {
  selectedTagIds: string[];
  onChange: (tagIds: string[]) => void;
}

export function TagFilterCombobox({ selectedTagIds, onChange }: TagFilterComboboxProps) {
  const [open, setOpen] = useState(false);
  const { data: tags } = useTags();

  function toggle(tagId: string) {
    onChange(
      selectedTagIds.includes(tagId)
        ? selectedTagIds.filter((id) => id !== tagId)
        : [...selectedTagIds, tagId],
    );
  }

  const selectedTags = (tags ?? []).filter((tag) => selectedTagIds.includes(tag.id));

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger
          render={
            <Button variant="outline" size="sm" className="gap-1.5">
              <Tags className="size-3.5" />
              Tags
              {selectedTagIds.length > 0 && (
                <Badge variant="secondary" className="ml-0.5">
                  {selectedTagIds.length}
                </Badge>
              )}
            </Button>
          }
        />
        <PopoverContent className="w-64 p-0" align="start">
          <Command>
            <CommandInput placeholder="Search tags…" />
            <CommandList>
              <CommandEmpty>No tags found.</CommandEmpty>
              <CommandGroup>
                {tags?.map((tag) => (
                  <CommandItem key={tag.id} value={tag.name} onSelect={() => toggle(tag.id)}>
                    <span className="flex-1">{tag.name}</span>
                    {selectedTagIds.includes(tag.id) && <span className="text-primary text-xs">Selected</span>}
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      {selectedTags.map((tag) => (
        <Badge key={tag.id} variant="outline" className="gap-1 pr-1">
          {tag.name}
          <button
            type="button"
            aria-label={`Remove ${tag.name} filter`}
            onClick={() => toggle(tag.id)}
            className="hover:bg-muted rounded-full p-0.5"
          >
            <X className="size-3" />
          </button>
        </Badge>
      ))}
    </div>
  );
}
