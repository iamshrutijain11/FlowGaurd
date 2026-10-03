import {api,USE_MOCK} from "@/lib/api";
import {Grievance,GEvent,NextAction,Explanation,Summary} from "@/types";
import {mockG,mockE,mockN,mockX,mockS} from "@/lib/mock";
export const getGrievances=()=>USE_MOCK?Promise.resolve([mockG]):api<Grievance[]>("/grievances");
export const getGrievance=(id:string)=>USE_MOCK?Promise.resolve(mockG):api<Grievance>(`/grievances/${id}`);
export const createGrievance=(d:Record<string,unknown>)=>USE_MOCK?Promise.resolve(mockG):api<Grievance>("/grievances",{method:"POST",body:JSON.stringify(d)});
export const getEvents=(id:string)=>USE_MOCK?Promise.resolve([...mockE]):api<GEvent[]>(`/grievances/${id}/events`);
export const getNextAction=(id:string)=>USE_MOCK?Promise.resolve(mockN):api<NextAction>(`/grievances/${id}/next-action`);
export const getAIExplanation=(id:string)=>USE_MOCK?Promise.resolve(mockX):api<Explanation>(`/grievances/${id}/explanation`);
export const getSummary=()=>USE_MOCK?Promise.resolve(mockS):api<Summary>("/dashboard/summary");
// Records the user's own action as an event (POST /grievances/{id}/events with allowed type FOLLOW_UP_SENT)
export async function markNextActionCompleted(id:string){
  if(USE_MOCK){mockE.push({id:"e"+mockE.length,grievance_id:id,event_type:"FOLLOW_UP_SENT",event_time:new Date().toISOString(),source:"USER",description:"Suggested follow-up marked as completed.",metadata:{}});return;}
  await api(`/grievances/${id}/events`,{method:"POST",body:JSON.stringify({event_type:"FOLLOW_UP_SENT",description:"Suggested follow-up marked as completed."})});
}
