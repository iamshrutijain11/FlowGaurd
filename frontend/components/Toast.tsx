"use client";
import {createContext,ReactNode,useCallback,useContext,useState} from "react";import {AnimatePresence,motion} from "framer-motion";import {Icon,Tone,TONE} from "./ui";
const Ctx=createContext<(m:string,tone?:Tone)=>void>(()=>{});
export const useToast=()=>useContext(Ctx);
export function ToastProvider({children}:{children:ReactNode}){
  const [list,set]=useState<{id:number;m:string;tone:Tone}[]>([]);
  const push=useCallback((m:string,tone:Tone="ok")=>{const id=Date.now()+Math.random();set(l=>[...l,{id,m,tone}]);setTimeout(()=>set(l=>l.filter(x=>x.id!==id)),4000);},[]);
  return <Ctx.Provider value={push}>{children}
    <div aria-live="polite" className="fixed bottom-4 right-4 z-[60] flex max-w-[calc(100vw-2rem)] flex-col gap-2">
      <AnimatePresence>{list.map(x=><motion.div key={x.id} layout initial={{opacity:0,y:16}} animate={{opacity:1,y:0}} exit={{opacity:0,x:40}} className={`glass flex items-center gap-2 border px-4 py-3 text-sm ${TONE[x.tone]}`}><Icon n={x.tone==="ok"?"check":"alert"}/>{x.m}</motion.div>)}</AnimatePresence>
    </div></Ctx.Provider>;
}
