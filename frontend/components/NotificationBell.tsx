"use client";
import {useEffect,useRef,useState} from "react";import {useRouter} from "next/navigation";import {AnimatePresence,motion} from "framer-motion";
import {Chip,Icon,IconName,Skeleton,Tone} from "./ui";import {useT} from "@/lib/i18n";import {useAsync} from "@/hooks/useAsync";import {useDismiss} from "@/hooks/useDismiss";
import {getNotifications,markRead} from "@/services/notificationService";import {fmtDT} from "@/lib/format";
const META:Record<string,[IconName,Tone]>={STATUS_CHANGED:["layers","info"],POTENTIAL_DELAY:["alert","warn"],FOLLOW_UP_DUE:["clock","brand"],DOCUMENT_REQUIRED:["file","info"],GRIEVANCE_RESOLVED:["check","ok"]};
export default function NotificationBell(){
  const {t,lang}=useT();const r=useRouter();const [open,setOpen]=useState(false);const ref=useRef<HTMLDivElement>(null);
  const {data,loading,reload}=useAsync(getNotifications,[]);useDismiss(ref,open,()=>setOpen(false));
  useEffect(()=>{const i=setInterval(reload,30000);return()=>clearInterval(i);},[reload]); // polling keeps the bell fresh
  const unread=data?.filter(n=>!n.read).length??0;
  return <div ref={ref} className="relative">
    <button onClick={()=>setOpen(!open)} aria-label={`${t("notifications")}${unread?` (${unread})`:""}`} aria-expanded={open} className="relative rounded-xl border border-white/15 bg-white/5 p-2 text-ink transition hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand">
      <Icon n="bell" className="h-5 w-5"/>{unread>0&&<span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-amber-400 px-1 text-[10px] font-bold text-slate-900">{unread}</span>}</button>
    <AnimatePresence>{open&&<motion.div initial={{opacity:0,y:-8,scale:.98}} animate={{opacity:1,y:0,scale:1}} exit={{opacity:0,y:-8}} transition={{duration:.18}} className="glass fixed inset-x-3 top-16 z-50 max-h-[70vh] overflow-y-auto bg-[#121735]/95 p-2 sm:absolute sm:inset-x-auto sm:right-0 sm:top-12 sm:w-96">
      <p className="px-3 py-2 text-sm font-semibold">{t("notifications")}</p>
      {loading&&!data&&<Skeleton className="m-2 h-16"/>}
      {data&&!data.length&&<p className="px-3 py-6 text-center text-sm text-mute">{t("noNotifs")}</p>}
      {data?.map(n=>{const [ic,tone]=META[n.notification_type]??["bell","neutral"];
        return <button key={n.id} onClick={async()=>{await markRead(n.id);reload();setOpen(false);if(n.grievance_id)r.push(`/grievances/${n.grievance_id}`);}} className="flex w-full gap-3 rounded-xl p-3 text-left transition hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand">
          <Chip tone={tone} icon={ic} className="h-7 shrink-0">{""}</Chip>
          <span className="min-w-0 flex-1"><span className="flex items-center gap-2 text-sm font-medium">{n.title}{!n.read&&<span className="h-2 w-2 rounded-full bg-amber-400" aria-label="unread"/>}</span>
            <span className="mt-0.5 block text-xs text-mute">{n.message}</span>
            <span className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-mute/80">{t("nt."+n.notification_type)} · {fmtDT(n.created_at,lang)}{n.channel&&<Chip className="!py-0 text-[10px]" icon="mail">{t("simulated")}</Chip>}</span></span></button>;})}
    </motion.div>}</AnimatePresence></div>;
}
