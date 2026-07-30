import { redirect } from "next/navigation";

// Invitations moved into a tab on /admin/people. Kept as a redirect rather
// than deleted so existing bookmarks and any link already sent round still
// land somewhere useful — on the invitations tab specifically, not a generic
// landing page.
export default function InvitationsRedirectPage() {
  redirect("/admin/people?tab=invitations");
}
