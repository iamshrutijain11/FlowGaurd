"use client";
import {useId,useState} from "react";import {motion} from "framer-motion";import {Icon} from "./ui";import {useT} from "@/lib/i18n";import {validateFile} from "@/services/documentService";import {fmtSize} from "@/lib/format";
export type UpState="idle"|"uploading"|"done"|"error";
export default function DropZone({label,file,state="idle",progress=0,error,onFile,onRemove,disabled}:{label:string;file?:File;state?:UpState;progress?:number;error?:string;onFile:(f:File)=>void;onRemove:()=>void;disabled?:boolean}){
  const {t}=useT();const id=useId();const [drag,setDrag]=useState(false);const [bad,setBad]=useState<string>();
  const take=(f?:File)=>{if(!f)return;const v=validateFile(f);setBad(v??undefined);if(!v)onFile(f);};
  const msg=bad?t(bad):error;
  return <div className={`glass p-4 transition ${drag?"border-indigo-300 bg-indigo-400/10":""} ${state==="error"||bad?"border-rose-400/40":""}`}>
    <p className="mb-2 text-sm font-semibold">{label}</p>
    {!file?<label htmlFor={id} onDragOver={e=>{e.preventDefault();setDrag(true);}} onDragLeave={()=>setDrag(false)} onDrop={e=>{e.preventDefault();setDrag(false);take(e.dataTransfer.files[0]);}}
      className={`flex cursor-pointer flex-col items-center gap-1 rounded-xl border-2 border-dashed px-3 py-6 text-center transition focus-within:ring-2 focus-within:ring-brand ${drag?"border-indigo-300":"border-white/20 hover:border-white/40"}`}>
      <motion.span animate={{y:drag?-4:0}} className="text-indigo-300"><Icon n="upload" className="h-6 w-6"/></motion.span><span className="text-sm">{t("dropHere")}</span><span className="text-xs text-mute">{t("fileRules")}</span>
      <input id={id} type="file" className="sr-only" accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg" disabled={disabled} onChange={e=>{take(e.target.files?.[0]);e.target.value="";}}/></label>
    :<div><div className="flex items-center gap-3"><Icon n="file" className="h-5 w-5 text-indigo-300"/><div className="min-w-0 flex-1"><p className="truncate text-sm">{file.name}</p><p className="text-xs text-mute">{fmtSize(file.size)}</p></div>
      {state==="done"?<motion.span initial={{scale:0}} animate={{scale:1}} className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-400/20 text-emerald-300"><Icon n="check"/></motion.span>
        :state==="idle"||state==="error"?<button type="button" onClick={onRemove} disabled={disabled} className="rounded-lg px-2 py-1 text-xs text-mute hover:bg-white/10 hover:text-ink">{t("remove")}</button>:null}</div>
      {(state==="uploading"||state==="done")&&<div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/10" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}><motion.div className="h-full bg-gradient-to-r from-indigo-400 to-emerald-400" animate={{width:`${progress}%`}}/></div>}
      {state==="done"&&<p className="mt-1.5 text-xs text-emerald-300">{t("uploaded")}</p>}</div>}
    {msg&&<p role="alert" className="err">{msg}</p>}
  </div>;
}
