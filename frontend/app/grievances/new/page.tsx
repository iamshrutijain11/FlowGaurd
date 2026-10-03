"use client";
import {useState} from "react";import {useRouter} from "next/navigation";import {AnimatePresence,motion} from "framer-motion";
import {Btn,Chip,Icon} from "@/components/ui";import DropZone,{UpState} from "@/components/DropZone";import {useToast} from "@/components/Toast";import {useT} from "@/lib/i18n";
import {createGrievance} from "@/services/grievanceService";import {uploadDocument} from "@/services/documentService";import {fmtSize} from "@/lib/format";
const CATS=["ACKNOWLEDGEMENT","RESPONSE","SCREENSHOT","SUPPORTING_EVIDENCE"];
const REQ=["complaint_id","entity_name","issue_type","issue_description","submission_date"];
type Up={state:UpState;progress:number;error?:string};
export default function NewGrievance(){
  const {t}=useT();const r=useRouter();const toast=useToast();const [step,setStep]=useState(0);const [f,setF]=useState<Record<string,string>>({});const [miss,setMiss]=useState<string[]>([]);
  const [files,setFiles]=useState<Record<string,File>>({});const [up,setUp]=useState<Record<string,Up>>({});const [busy,setBusy]=useState(false);const [gid,setGid]=useState<string>();const [err,setErr]=useState("");
  const u=(k:string)=>(e:React.ChangeEvent<HTMLInputElement|HTMLTextAreaElement|HTMLSelectElement>)=>setF({...f,[k]:e.target.value});
  const today=new Date().toISOString().slice(0,10);
  const next=()=>{const m=REQ.filter(k=>!f[k]?.trim());setMiss(m);if(!m.length)setStep(1);};
  const setU=(c:string,p:Partial<Up>)=>setUp(s=>({...s,[c]:{...{state:"idle" as UpState,progress:0},...s[c],...p}}));
  async function submit(){setBusy(true);setErr("");let id=gid;
    try{if(!id){const g=await createGrievance({...f,submission_date:new Date(f.submission_date).toISOString(),acknowledgement_date:f.acknowledgement_date?new Date(f.acknowledgement_date).toISOString():undefined,current_stage:f.current_stage||undefined});id=g.id;setGid(id);}
      let failed=0;
      for(const c of CATS){const file=files[c];if(!file||up[c]?.state==="done")continue;setU(c,{state:"uploading",progress:0,error:undefined});
        try{await uploadDocument(id,file,c,p=>setU(c,{progress:p}));setU(c,{state:"done",progress:100});}catch(e){failed++;setU(c,{state:"error",error:(e as Error).message});}}
      if(!failed){toast(t("created"));r.push(`/grievances/${id}`);}else setErr(t("uploadFailed"));
    }catch(e){setErr((e as Error).message);}finally{setBusy(false);}}
  const fld=(k:string,label:string,el:React.ReactNode)=><div><label htmlFor={k} className="lbl">{label}</label>{el}{miss.includes(k)&&<p className="err">{t("valReq")}</p>}</div>;
  const steps=["step.1","step.2","step.3"];
  return <div className="mx-auto max-w-3xl space-y-6"><h1 className="h-grad text-3xl font-extrabold">{t("newGrievance")}</h1>
    <ol className="flex items-center" aria-label="Progress">{steps.map((s,i)=><li key={s} aria-current={i===step?"step":undefined} className="flex flex-1 items-center last:flex-none">
      <span className={`flex items-center gap-2 text-sm ${i<=step?"text-white":"text-mute"}`}><span className={`flex h-8 w-8 items-center justify-center rounded-full border text-xs font-bold ${i<step?"border-emerald-400/50 bg-emerald-400/15 text-emerald-300":i===step?"border-indigo-300 bg-indigo-500":"border-white/15"}`}>{i<step?<Icon n="check"/>:i+1}</span><span className="hidden sm:inline">{t(s)}</span></span>
      {i<2&&<span className="mx-3 h-0.5 flex-1 overflow-hidden rounded bg-white/10"><motion.span className="block h-full bg-indigo-400" animate={{width:i<step?"100%":"0%"}}/></span>}</li>)}</ol>
    <AnimatePresence mode="wait"><motion.div key={step} initial={{opacity:0,x:16}} animate={{opacity:1,x:0}} exit={{opacity:0,x:-16}} transition={{duration:.2}}>
      {step===0&&<div className="glass space-y-4 p-6">
        <div className="grid gap-4 sm:grid-cols-2">
          {fld("complaint_id",t("complaintId"),<input id="complaint_id" value={f.complaint_id??""} onChange={u("complaint_id")} className="input"/>)}
          {fld("entity_name",t("entityName"),<input id="entity_name" value={f.entity_name??""} onChange={u("entity_name")} className="input"/>)}</div>
        {fld("issue_type",t("issueType"),<input id="issue_type" value={f.issue_type??""} onChange={u("issue_type")} className="input"/>)}
        {fld("issue_description",t("issueDesc"),<textarea id="issue_description" rows={4} value={f.issue_description??""} onChange={u("issue_description")} className="input"/>)}
        <div className="grid gap-4 sm:grid-cols-3">
          {fld("submission_date",t("subDate"),<input id="submission_date" type="date" max={today} value={f.submission_date??""} onChange={u("submission_date")} className="input"/>)}
          {fld("acknowledgement_date",t("ackDate"),<input id="acknowledgement_date" type="date" max={today} value={f.acknowledgement_date??""} onChange={u("acknowledgement_date")} className="input"/>)}
          {fld("current_stage",t("statusKnown"),<select id="current_stage" value={f.current_stage??""} onChange={u("current_stage")} className="input"><option value="">{t("notSure")}</option>{["FILED","ACKNOWLEDGED","AWAITING_RESPONSE","RESPONSE_RECEIVED"].map(s=><option key={s} value={s}>{t("stage."+s)}</option>)}</select>)}</div>
        <div className="flex justify-end"><Btn onClick={next}>{t("continue")}<Icon n="arrow"/></Btn></div></div>}
      {step===1&&<div className="space-y-4"><p className="text-sm text-mute">{t("uploadHint")}</p>
        <div className="grid gap-4 sm:grid-cols-2">{CATS.map(c=><DropZone key={c} label={t("dt."+c)} file={files[c]} state={up[c]?.state} progress={up[c]?.progress} error={up[c]?.error} disabled={busy}
          onFile={x=>{setFiles({...files,[c]:x});setU(c,{state:"idle",progress:0,error:undefined});}} onRemove={()=>{const n={...files};delete n[c];setFiles(n);}}/>)}</div>
        <div className="flex justify-between"><Btn variant="ghost" onClick={()=>setStep(0)}>{t("back")}</Btn><Btn onClick={()=>setStep(2)}>{t("continue")}<Icon n="arrow"/></Btn></div></div>}
      {step===2&&<div className="glass space-y-5 p-6"><h2 className="text-lg font-semibold">{t("reviewTitle")}</h2>
        <dl className="grid gap-3 text-sm sm:grid-cols-2">{[["complaintId","complaint_id"],["entityName","entity_name"],["issueType","issue_type"],["subDate","submission_date"],["ackDate","acknowledgement_date"]].map(([l,k])=><div key={k}><dt className="text-xs text-mute">{t(l)}</dt><dd>{f[k]||"–"}</dd></div>)}
          <div><dt className="text-xs text-mute">{t("statusKnown")}</dt><dd>{f.current_stage?t("stage."+f.current_stage):t("notSure")}</dd></div><div className="sm:col-span-2"><dt className="text-xs text-mute">{t("issueDesc")}</dt><dd>{f.issue_description}</dd></div></dl>
        <ul className="space-y-2">{CATS.map(c=>{const x=files[c];const s=up[c];return <li key={c} className="flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.04] p-3 text-sm">
          <span className="min-w-0"><span className="block text-xs text-mute">{t("dt."+c)}</span><span className="block truncate">{x?`${x.name} · ${fmtSize(x.size)}`:t("skipped")}</span></span>
          {s?.state==="uploading"&&<Chip tone="info">{t("uploading")} {s.progress}%</Chip>}{s?.state==="done"&&<Chip tone="ok" icon="check">{t("uploaded")}</Chip>}{s?.state==="error"&&<Chip tone="bad" icon="alert">{s.error??t("uploadFailed")}</Chip>}</li>;})}</ul>
        {err&&<p role="alert" className="err">{err}</p>}
        <div className="flex flex-wrap justify-between gap-2"><Btn variant="ghost" disabled={busy||!!gid} onClick={()=>setStep(1)}>{t("back")}</Btn>
          <div className="flex gap-2">{gid&&err&&<Btn variant="ghost" onClick={()=>r.push(`/grievances/${gid}`)}>{t("goToCase")}</Btn>}<Btn loading={busy} onClick={submit}>{gid?t("retryUploads"):t("submit")}</Btn></div></div></div>}
    </motion.div></AnimatePresence></div>;
}
