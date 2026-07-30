"use client";

import { FileStack } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCurrentUser } from "@/features/auth/hooks";
import { cn } from "@/lib/utils";
import type { UserRole } from "@/types/api";
import { ADMIN_NAV, PRIMARY_NAV, SETTINGS_NAV } from "./nav-items";
import type { NavItem } from "./nav-items";

function isVisible(item: NavItem, role?: UserRole): boolean {
  if (!item.roles) return true;
  return role ? item.roles.includes(role) : false;
}

function NavLink({ item, active, onNavigate }: { item: NavItem; active: boolean; onNavigate?: () => void }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      onClick={onNavigate}
      className={cn(
        "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm font-medium transition-colors",
        active
          ? "bg-sidebar-primary/10 text-sidebar-primary"
          : "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
      )}
    >
      <Icon className="size-4 shrink-0" />
      <span className="truncate">{item.label}</span>
    </Link>
  );
}

export function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { data: user } = useCurrentUser();
  const showAdmin = isVisible(ADMIN_NAV[0], user?.role);

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-14 items-center gap-2 px-4">
        <div className="bg-primary text-primary-foreground flex size-7 shrink-0 items-center justify-center rounded-md">
          <FileStack className="size-4" />
        </div>
        <div className="min-w-0 leading-tight">
          <p className="truncate text-sm font-semibold">DocBrain</p>
          {user?.organization && (
            <p className="text-sidebar-foreground/60 truncate text-xs">{user.organization.name}</p>
          )}
        </div>
      </div>

      <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-2">
        <div className="space-y-1">
          {PRIMARY_NAV.filter((item) => isVisible(item, user?.role)).map((item) => (
            <NavLink key={item.href} item={item} active={pathname === item.href} onNavigate={onNavigate} />
          ))}
        </div>

        {showAdmin && (
          <div className="space-y-1">
            <p className="text-sidebar-foreground/50 px-2.5 text-xs font-medium tracking-wide uppercase">Admin</p>
            {ADMIN_NAV.map((item) => (
              <NavLink key={item.href} item={item} active={pathname === item.href} onNavigate={onNavigate} />
            ))}
          </div>
        )}
      </nav>

      <div className="border-sidebar-border border-t p-3">
        <NavLink item={SETTINGS_NAV} active={pathname === SETTINGS_NAV.href} onNavigate={onNavigate} />
      </div>
    </div>
  );
}

export function Sidebar() {
  return (
    <aside className="bg-sidebar border-sidebar-border hidden w-60 shrink-0 border-r lg:block">
      <SidebarContent />
    </aside>
  );
}
