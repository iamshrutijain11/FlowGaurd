import {api,API_BASE,getToken,USE_MOCK} from "@/lib/api";
import {Doc} from "@/types";import {mockD} from "@/lib/mock";
export const MAX_MB=10;
export const getDocuments=(id:string)=>USE_MOCK?Promise.resolve(mockD):api<Doc[]>(`/grievances/${id}/documents`);
/** returns an i18n key describing the problem, or null if the file is acceptable */
export function validateFile(f:File):string|null{
  if(!["application/pdf","image/png","image/jpeg"].includes(f.type))return "errType";
  return f.size>MAX_MB*1048576?"errSize":null;
}
export function uploadDocument(id:string,file:File,documentType:string,onProgress?:(p:number)=>void):Promise<Doc|undefined>{
  if(USE_MOCK)return new Promise(res=>{let p=0;const t=setInterval(()=>{p+=20;onProgress?.(Math.min(p,100));if(p>=100){clearInterval(t);res({id:"new",file_name:file.name,document_type:documentType,uploaded_at:new Date().toISOString(),extraction_status:"PENDING"});}},180);});
  return new Promise((res,rej)=>{
    const f=new FormData();f.append("file",file);f.append("document_type",documentType);
    const x=new XMLHttpRequest();x.open("POST",`${API_BASE}/grievances/${id}/documents`);
    const t=getToken();if(t)x.setRequestHeader("Authorization",`Bearer ${t}`);
    x.upload.onprogress=e=>e.lengthComputable&&onProgress?.(Math.round(e.loaded/e.total*100));
    x.onload=()=>{try{const j=JSON.parse(x.responseText);j.success?res(j.data):rej(new Error(j.error?.message??"Upload failed"));}catch{rej(new Error("Upload failed"));}};
    x.onerror=()=>rej(new Error("Network error"));x.send(f);
  });
}

export async function downloadDocument(docId:string,fileName:string):Promise<void>{
  if(USE_MOCK)return;
  const t=getToken();
  const res=await fetch(`${API_BASE}/documents/${docId}/download`,{
    headers:t?{Authorization:`Bearer ${t}`}:{},
  });
  if(!res.ok)throw new Error("Failed to download document");
  const blob=await res.blob();
  const url=window.URL.createObjectURL(blob);
  const a=document.createElement("a");
  a.href=url;
  a.download=fileName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

