"use client";
import {motion} from "framer-motion";import {Explanation} from "@/types";import {useT} from "@/lib/i18n";import {Chip,Icon,IconName} from "./ui";
function toText(v: any): string | undefined {
  if (v === null || v === undefined) return undefined;
  if (typeof v === "string") return v.trim() || undefined;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  if (Array.isArray(v)) {
    const items = v.map(toText).filter(Boolean);
    return items.length ? items.join(", ") : undefined;
  }
  if (typeof v === "object") {
    try {
      return Object.entries(v).map(([k, val]) => `${k}: ${toText(val)}`).join("; ");
    } catch {
      return JSON.stringify(v);
    }
  }
  return String(v);
}

export default function ExplanationCard({x}:{x:Explanation}){
  const {t}=useT();
  const rows:[string,IconName,string|undefined][]=[
    ["situation","clock",toText(x?.current_situation)],
    ["happened","layers",toText(x?.timeline_summary)],
    ["missing","file",toText(x?.missing_information)],
    ["next","arrow",toText(x?.next_step_summary)],
  ];
  const warnExp = toText(x?.warning_explanation);

  return <motion.section initial={{opacity:0,y:12}} animate={{opacity:1,y:0}} transition={{delay:.1}} className="glass border-violet-400/25 bg-gradient-to-br from-violet-500/[0.12] to-indigo-500/[0.05] p-5">
    <div className="flex items-center justify-between gap-2"><h2 className="text-lg font-semibold">{t("aiTitle")}</h2><Chip tone="brand" icon="spark">{t("src.AI")}</Chip></div>
    {warnExp&&<div className="mt-3 rounded-xl border border-amber-400/30 bg-amber-400/10 p-3 text-sm text-amber-200">
      <div className="flex items-center gap-1.5 font-semibold text-amber-300"><Icon n="alert" className="h-4 w-4"/>{t("warningLabel")}</div>
      <p className="mt-1 text-xs text-amber-100/90">{warnExp}</p></div>}
    <dl className="mt-4 space-y-4">{rows.map(([k,ic,v])=><div key={k} className="flex gap-3"><span className="mt-0.5 text-violet-300"><Icon n={ic}/></span>
      <div><dt className="text-sm font-semibold">{t(k)}</dt><dd className={`text-sm ${v?"text-ink/85":"text-mute"}`}>{v??t("unavailable")}</dd></div></div>)}</dl>
    <p className="mt-4 border-t border-white/10 pt-3 text-xs italic text-mute">{t("aiLabel")}</p>
  </motion.section>;
}
