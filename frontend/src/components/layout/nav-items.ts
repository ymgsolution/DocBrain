import {
  FolderTree,
  LayoutDashboard,
  ClipboardCheck,
  FileText,
  Settings,
  Tags,
  Trash2,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { UserRole } from "@/types/api";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  roles?: UserRole[]; // omitted = visible to everyone
}

// Data-driven so a future nav item (e.g. an "AI Insights" module) is a
// one-line addition here, not a restructure of the sidebar component.
export const PRIMARY_NAV: NavItem[] = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Documents", href: "/documents", icon: FileText },
  { label: "Pending Reviews", href: "/reviews", icon: ClipboardCheck, roles: ["REVIEWER", "ADMIN"] },
  { label: "Trash", href: "/trash", icon: Trash2 },
];

export const ADMIN_NAV: NavItem[] = [
  { label: "Categories", href: "/admin/categories", icon: FolderTree, roles: ["ADMIN"] },
  { label: "Tags", href: "/admin/tags", icon: Tags, roles: ["ADMIN"] },
];

export const SETTINGS_NAV: NavItem = { label: "Settings", href: "/settings", icon: Settings };
