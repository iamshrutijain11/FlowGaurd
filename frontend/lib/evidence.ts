import {Doc} from "@/types";
// Display helper only: marks backend-provided checklist items as available when the record or an uploaded file covers them.
export const isAvailable=(item:string,docs:Doc[])=>{const s=item.toLowerCase();
  return /reference|submission|complaint id/.test(s)||docs.some(d=>s.includes(d.document_type.toLowerCase().replace(/_/g," ").split(" ")[0]));};
