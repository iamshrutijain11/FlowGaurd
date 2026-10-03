import {Doc} from "@/types";
// Display helper only: marks backend-provided checklist items as available when the record or an uploaded file covers them.
export const isAvailable = (item: unknown, docs?: Doc[]) => {
  if (!item) return false;
  const s = typeof item === "string" ? item.toLowerCase() : typeof item === "object" ? JSON.stringify(item).toLowerCase() : String(item).toLowerCase();
  return /reference|submission|complaint id/.test(s) || (docs || []).some(d => d?.document_type && s.includes(d.document_type.toLowerCase().replace(/_/g, " ").split(" ")[0]));
};
