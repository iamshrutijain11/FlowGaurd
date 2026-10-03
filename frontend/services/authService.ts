import {api,USE_MOCK} from "@/lib/api";import {Me} from "@/types";import {mockMe} from "@/lib/mock";
export async function login(email:string,password:string){
  if(USE_MOCK){localStorage.setItem("fg_token","mock");return;}
  const d=await api<{access_token?:string;data?:{access_token?:string}}>("/auth/login",{method:"POST",body:JSON.stringify({email,password})});
  const token = d?.access_token || d?.data?.access_token;
  if(token) localStorage.setItem("fg_token",token);
}
export const register=(b:{name:string;email:string;password:string;preferred_language:string})=>USE_MOCK?Promise.resolve():api("/auth/register",{method:"POST",body:JSON.stringify(b)});
export const getMe=()=>USE_MOCK?Promise.resolve(mockMe):api<Me>("/auth/me");
export const logout=()=>localStorage.removeItem("fg_token");
export const isLoggedIn=()=>!!localStorage.getItem("fg_token");
