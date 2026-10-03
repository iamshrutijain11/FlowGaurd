"use client";
import {useT} from "@/lib/i18n";
export default function LangSwitch(){
  const {lang,setLang}=useT();
  return <div role="group" aria-label="Language" className="flex rounded-full border border-white/15 bg-white/5 p-0.5 text-xs font-semibold">
    {(["en","hi"] as const).map(l=><button key={l} aria-pressed={lang===l} onClick={()=>setLang(l)} className={`rounded-full px-2.5 py-1 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand ${lang===l?"bg-indigo-500 text-white":"text-mute hover:text-ink"}`}>{l==="en"?"EN":"हि"}</button>)}
  </div>;
}
