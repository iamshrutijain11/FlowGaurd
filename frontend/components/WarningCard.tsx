"use client";
import {useState} from "react";import {AnimatePresence,motion} from "framer-motion";import {Warning,GEvent} from "@/types";import {useT} from "@/lib/i18n";import {Chip,Icon} from "./ui";import {fmtDate} from "@/lib/format";
export default function WarningCard({w,events}:{w:Warning;events:GEvent[]}){
  const {t,lang}=useT();const [open,setOpen]=useState(false);const ev=events.find(e=>e.id===w.based_on_event);
  return <motion.section initial={{opacity:0,y:12}} animate={{opacity:1,y:0}} className="glass pulse-glow border-amber-400/40 bg-amber-400/[0.07] p-5" aria-labelledby="warn-h">
    <div className="flex items-start gap-3"><span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-400/15 text-amber-300"><Icon n="alert" className="h-5 w-5"/></span>
      <div><Chip tone="warn" icon="cog">{t("warningLabel")}</Chip><h2 id="warn-h" className="mt-2 text-lg font-semibold">{t("delayTitle")}</h2><p className="mt-1 text-sm text-ink/80">{t("delayBody")}</p></div></div>
    <button onClick={()=>setOpen(!open)} aria-expanded={open} className="mt-4 flex items-center gap-1.5 rounded-lg text-sm font-semibold text-amber-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand">{t("why")}<motion.span animate={{rotate:open?180:0}}><Icon n="chevron"/></motion.span></button>
    <AnimatePresence initial={false}>{open&&<motion.div initial={{height:0,opacity:0}} animate={{height:"auto",opacity:1}} exit={{height:0,opacity:0}} className="overflow-hidden">
      <div className="mt-3 space-y-2 rounded-xl border border-white/10 bg-black/20 p-4 text-sm">
        {w.reason&&<p>{w.reason}</p>}
        {ev&&<p className="text-mute">{t("basedOn")}: <span className="text-ink">{ev.description}</span> ({fmtDate(ev.event_time,lang)})</p>}
        <p className="flex flex-wrap gap-3 text-xs text-mute">{(w.rule||w.rule_id)&&<span>{t("rule")}: {w.rule||w.rule_id}</span>}{w.triggered_at&&<span>{t("triggeredOn")}: {fmtDate(w.triggered_at,lang)}</span>}</p></div></motion.div>}</AnimatePresence>
  </motion.section>;
}
