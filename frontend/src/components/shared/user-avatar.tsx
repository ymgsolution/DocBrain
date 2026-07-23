import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { getInitials } from "@/lib/format";
import { cn } from "@/lib/utils";

interface UserAvatarProps {
  name: string;
  className?: string;
}

export function UserAvatar({ name, className }: UserAvatarProps) {
  return (
    <Avatar className={cn("size-8", className)}>
      <AvatarFallback className="bg-primary/10 text-primary text-xs font-medium">
        {getInitials(name)}
      </AvatarFallback>
    </Avatar>
  );
}
