"use client";
import {ReactNode,useEffect} from "react";import {AnimatePresence,motion} from "framer-motion";import {Icon} from "./ui";import {useT} from "@/lib/i18n";
export default function Modal({open,onClose,title,children}:{open:boolean;onClose:()=>void;title:string;children:ReactNode}){
  const {t}=useT();
  useEffect(()=>{if(!open)return;const k=(e:KeyboardEvent)=>e.key==="Escape"&&onClose();document.addEventListener("keydown",k);document.body.style.overflow="hidden";
    return()=>{document.removeEventListener("keydown",k);document.body.style.overflow="";};},[open,onClose]);
  return <AnimatePresence>{open&&<motion.div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-4" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}}>
    <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose}/>
    <motion.div role="dialog" aria-modal="true" aria-label={title} initial={{y:40,opacity:0}} animate={{y:0,opacity:1}} exit={{y:30,opacity:0}} transition={{type:"spring",damping:26,stiffness:300}}
      className="glass relative max-h-[85vh] w-full overflow-y-auto rounded-b-none bg-[#121735]/95 p-6 sm:max-w-lg sm:rounded-2xl">
      <div className="mb-4 flex items-start justify-between gap-3"><h2 className="text-lg font-semibold">{title}</h2>
        <button autoFocus onClick={onClose} aria-label={t("close")} className="rounded-lg p-1.5 text-mute hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"><Icon n="x" className="h-5 w-5"/></button></div>
      {children}</motion.div></motion.div>}</AnimatePresence>;
}
