import {api,USE_MOCK} from "@/lib/api";import {Notif} from "@/types";import {mockNotifs} from "@/lib/mock";
export const getNotifications=()=>USE_MOCK?Promise.resolve(mockNotifs.map(n=>({...n}))):api<Notif[]>("/notifications");
export const markRead=(id:string)=>{if(USE_MOCK){const n=mockNotifs.find(x=>x.id===id);if(n)n.read=true;return Promise.resolve();}return api(`/notifications/${id}/read`,{method:"PATCH"});};
