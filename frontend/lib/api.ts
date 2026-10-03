export const API_BASE=process.env.NEXT_PUBLIC_API_URL??"";
export const USE_MOCK=process.env.NEXT_PUBLIC_USE_MOCK==="true";
export const getToken=()=>typeof window!=="undefined"?localStorage.getItem("fg_token"):null; // MVP strategy: JWT in localStorage
export async function api<T>(path:string,init:RequestInit={}):Promise<T>{
  const t=getToken();
  const headers:Record<string,string>={...(init.body instanceof FormData?{}:{"Content-Type":"application/json"}),...(t?{Authorization:`Bearer ${t}`}:{})};
  const r=await fetch(`${API_BASE}/api/v1${path}`,{...init,headers});
  const j=await r.json();
  if(!j.success)throw new Error(j.error?.message??"Request failed");
  return j.data as T;
}
