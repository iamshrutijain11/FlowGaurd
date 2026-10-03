"use client";
import {motion} from "framer-motion";import {Doc,NextAction} from "@/types";import {useT} from "@/lib/i18n";import {Btn,Chip,Icon} from "./ui";import {isAvailable} from "@/lib/evidence";
export default function NextActionCard({a,docs,onGuidance,onEvidence,onComplete,completing,completed}:{a:NextAction;docs:Doc[];onGuidance:()=>void;onEvidence:()=>void;onComplete:()=>void;completing:boolean;completed:boolean}){
  const {t}=useT();const ext=!!a.official_source&&/^https?:\/\//.test(a.official_source);
  return <motion.section initial={{opacity:0,y:12}} animate={{opacity:1,y:0}} transition={{delay:.2}} className="glass p-5">
    <Chip tone="info" icon="cog">{t("suggestedAction")}</Chip>
    <h2 className="mt-2 text-lg font-semibold">{a.title}</h2><p className="mt-1 text-sm text-ink/80">{a.description}</p>
    {a.required_documents.length>0&&<><h3 className="mt-4 text-sm font-semibold">{t("usefulInfo")}</h3>
      <ul className="mt-2 grid gap-1.5 sm:grid-cols-2">{a.required_documents.map(d=>{const ok=isAvailable(d,docs);return <li key={d} className="flex items-center gap-2 text-sm"><span className={`flex h-5 w-5 items-center justify-center rounded-full ${ok?"bg-emerald-400/20 text-emerald-300":"border border-white/20 text-transparent"}`}><Icon n="check" className="h-3 w-3"/></span><span className={ok?"":"text-mute"}>{d}</span><span className="sr-only">{ok?t("haveIt"):t("notYet")}</span></li>;})}</ul></>}
    <div className="mt-4 rounded-xl border border-emerald-400/20 bg-emerald-400/[0.05] p-3"><Chip tone="ok" icon="shield">{t("verifiedGuidance")}</Chip>
      {a.official_source?(ext?<a href={a.official_source} target="_blank" rel="noopener noreferrer" className="mt-2 flex items-center gap-1.5 text-sm font-semibold text-emerald-300 underline-offset-2 hover:underline"><Icon n="link"/>{t("officialLink")}</a>:<p className="mt-2 text-sm">{a.official_source}</p>):<p className="mt-2 text-sm text-mute">{t("noSource")}</p>}</div>
    <div className="mt-5 flex flex-wrap gap-2"><Btn onClick={onGuidance}>{t("viewGuidance")}</Btn><Btn variant="ghost" onClick={onEvidence}>{t("prepEvidence")}</Btn>
      <Btn variant="ghost" onClick={onComplete} loading={completing} disabled={completed}>{completed&&<Icon n="check"/>}{t("markDone")}</Btn></div>
  </motion.section>;
}
