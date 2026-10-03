"use client";
import {motion} from "framer-motion";import {GEvent} from "@/types";import {useT} from "@/lib/i18n";import {Chip,Icon,IconName,Tone} from "./ui";import {fmtDT} from "@/lib/format";
const SRC:Record<string,[IconName,Tone]>={USER:["user","info"],SYSTEM:["cog","warn"],AI:["bot","brand"],ADMIN:["shield","neutral"]};
export default function Timeline({events}:{events:GEvent[]}){
  const {t,lang}=useT();const sorted=[...events].sort((a,b)=>+new Date(a.event_time)-+new Date(b.event_time));
  const label=(k:string)=>{const v=t("ev."+k);return v==="ev."+k?k.replace(/_/g," ").toLowerCase().replace(/^./,c=>c.toUpperCase()):v;};
  return <section className="glass p-5"><h2 className="text-lg font-semibold">{t("timeline")}</h2><p className="mt-0.5 text-xs text-mute">{t("timelineSub")}</p>
    <ol className="relative mt-4 space-y-5 border-l border-white/15 pl-6">{sorted.map((e,i)=>{const [ic,tone]=SRC[e.source]??SRC.SYSTEM;
      return <motion.li key={e.id} initial={{opacity:0,x:-10}} whileInView={{opacity:1,x:0}} viewport={{once:true,margin:"-30px"}} transition={{delay:Math.min(i,4)*.05}} className="relative">
        <span className={`absolute -left-[2.15rem] flex h-7 w-7 items-center justify-center rounded-full border bg-[#121735] ${tone==="warn"?"border-amber-400/50 text-amber-300":tone==="brand"?"border-indigo-400/50 text-indigo-200":"border-sky-400/40 text-sky-300"}`}><Icon n={ic} className="h-3.5 w-3.5"/></span>
        <p className="text-sm font-semibold">{label(e.event_type)}</p><p className="text-sm text-ink/80">{e.description}</p>
        <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-mute"><time dateTime={e.event_time}>{fmtDT(e.event_time,lang)}</time><Chip tone={tone} className="!py-0">{t("src."+e.source)}</Chip></p></motion.li>;})}</ol></section>;
}
