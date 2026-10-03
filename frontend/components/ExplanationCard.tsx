"use client";
import {motion} from "framer-motion";import {Explanation} from "@/types";import {useT} from "@/lib/i18n";import {Chip,Icon,IconName} from "./ui";
export default function ExplanationCard({x}:{x:Explanation}){
  const {t}=useT();
  const rows:[string,IconName,string|undefined][]=[["situation","clock",x.current_situation],["happened","layers",x.timeline_summary],["missing","file",x.missing_information?.length?x.missing_information.join(", "):undefined],["next","arrow",x.next_step_summary]];
  return <motion.section initial={{opacity:0,y:12}} animate={{opacity:1,y:0}} transition={{delay:.1}} className="glass border-violet-400/25 bg-gradient-to-br from-violet-500/[0.12] to-indigo-500/[0.05] p-5">
    <div className="flex items-center justify-between gap-2"><h2 className="text-lg font-semibold">{t("aiTitle")}</h2><Chip tone="brand" icon="spark">{t("src.AI")}</Chip></div>
    <dl className="mt-4 space-y-4">{rows.map(([k,ic,v])=><div key={k} className="flex gap-3"><span className="mt-0.5 text-violet-300"><Icon n={ic}/></span>
      <div><dt className="text-sm font-semibold">{t(k)}</dt><dd className={`text-sm ${v?"text-ink/85":"text-mute"}`}>{v??t("unavailable")}</dd></div></div>)}</dl>
    <p className="mt-4 border-t border-white/10 pt-3 text-xs italic text-mute">{t("aiLabel")}</p>
  </motion.section>;
}
