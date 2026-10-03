"use client";
import {motion} from "framer-motion";import {Stage} from "@/types";import {useT} from "@/lib/i18n";import {Icon} from "./ui";import {stageIcon,stageSteps} from "@/lib/stage";
export default function StatusPipeline({stage}:{stage:Stage}){
  const {t}=useT();const steps=stageSteps(stage);const n=steps.length;const cur=steps.indexOf(stage);
  const node=(s:Stage,i:number)=>{const done=i<cur,now=i===cur;
    return <span className="relative flex h-10 w-10 items-center justify-center">
      {now&&<span className="ping-slow absolute inset-0 rounded-full bg-indigo-400/40"/>}
      <motion.span initial={{scale:.6,opacity:0}} animate={{scale:now?1.1:1,opacity:1}} transition={{delay:i*.12,type:"spring",stiffness:260,damping:18}}
        className={`relative flex h-9 w-9 items-center justify-center rounded-full border-2 text-xs font-bold ${now?"border-indigo-300 bg-indigo-500 text-white shadow-[0_0_24px_rgba(129,140,248,.55)]":done?"border-emerald-400/60 bg-emerald-400/15 text-emerald-300":"border-white/15 bg-white/5 text-mute/60"}`}>
        {done?<Icon n="check"/>:now?<Icon n={stageIcon[s]}/>:i+1}</motion.span></span>;};
  return <ol aria-label={t("pipelineTitle")}>
    <div className="relative hidden md:grid" style={{gridTemplateColumns:`repeat(${n},1fr)`}}>
      <span aria-hidden className="absolute top-5 h-0.5 rounded bg-white/10" style={{left:`${50/n}%`,right:`${50/n}%`}}/>
      <motion.span aria-hidden className="absolute top-5 h-0.5 origin-left rounded bg-gradient-to-r from-emerald-400 to-indigo-400" style={{left:`${50/n}%`,right:`${50/n}%`}} initial={{scaleX:0}} animate={{scaleX:cur/(n-1)}} transition={{duration:.9,ease:"easeOut"}}/>
      {steps.map((s,i)=><li key={s} title={t("help."+s)} aria-current={i===cur?"step":undefined} className="relative flex flex-col items-center px-1 text-center">
        {node(s,i)}<span className={`mt-2 text-sm ${i===cur?"font-bold text-white":i<cur?"text-ink":"text-mute/60"}`}>{t("stage."+s)}</span>
        {i===cur&&<span className="mt-1 max-w-[9rem] text-xs text-mute">{t("help."+s)}</span>}</li>)}
    </div>
    <div className="relative md:hidden">{steps.map((s,i)=><li key={s} aria-current={i===cur?"step":undefined} className="relative flex gap-4 pb-5 last:pb-0">
      {i<n-1&&<span aria-hidden className={`absolute left-5 top-10 h-[calc(100%-2.5rem)] w-0.5 ${i<cur?"bg-emerald-400/50":"bg-white/10"}`}/>}
      {node(s,i)}<div className="pt-1.5"><p className={`text-sm ${i===cur?"font-bold text-white":i<cur?"text-ink":"text-mute/60"}`}>{t("stage."+s)}</p>{i===cur&&<p className="text-xs text-mute">{t("help."+s)}</p>}</div></li>)}</div>
  </ol>;
}
