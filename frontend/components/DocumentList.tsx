"use client";
import {useState} from "react";import {motion} from "framer-motion";import {Doc,ExtStatus} from "@/types";import {useT} from "@/lib/i18n";import {Chip,Icon,IconName,Tone} from "./ui";import {fmtDT} from "@/lib/format";import {downloadDocument} from "@/services/documentService";
const EXT:Record<ExtStatus,[IconName,Tone]>={PENDING:["clock","neutral"],PROCESSING:["clock","info"],COMPLETED:["check","ok"],PARTIAL:["alert","warn"],FAILED:["x","bad"]};
export default function DocumentList({docs}:{docs:Doc[]}){
  const {t,lang}=useT();
  const [dlId,setDlId]=useState<string|null>(null);
  const handleDownload=async(d:Doc)=>{
    if(d.preview_url&&!d.download_url){window.open(d.preview_url,"_blank");return;}
    setDlId(d.id);
    try{await downloadDocument(d.id,d.file_name);}catch(e){console.error(e);}finally{setDlId(null);}
  };
  return <section id="documents" className="glass p-5"><h2 className="text-lg font-semibold">{t("documents")}</h2>
    {!docs.length&&<p className="mt-3 text-sm text-mute">{t("noDocs")}</p>}
    <ul className="mt-3 space-y-3">{docs.map((d,i)=>{const [ic,tone]=EXT[d.extraction_status]??EXT.PENDING;const dl=d.download_url??d.preview_url;
      return <motion.li key={d.id} initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} transition={{delay:i*.07}} className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
        <div className="flex items-start gap-3"><span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-indigo-400/15 text-indigo-200"><Icon n="file" className="h-5 w-5"/></span>
          <div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold">{d.file_name}</p>
            <p className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-mute">{t("dt."+d.document_type)} · {fmtDT(d.uploaded_at,lang)}</p>
            <div className="mt-2 flex flex-wrap gap-2"><Chip tone={tone} icon={ic}>{t("ext."+d.extraction_status)}</Chip>
              {dl&&<button type="button" onClick={()=>handleDownload(d)} disabled={dlId===d.id} className="chip border-white/15 bg-white/5 hover:bg-white/10 cursor-pointer disabled:opacity-50"><Icon n="download" className="h-3.5 w-3.5"/>{dlId===d.id?t("loading"):d.download_url?t("download"):t("preview")}</button>}</div></div></div>
        {d.extracted_data&&Object.keys(d.extracted_data).length>0&&<div className="mt-3 rounded-lg border border-dashed border-indigo-300/30 bg-indigo-400/[0.06] p-3">
          <Chip tone="brand" icon="spark">{t("extracted")}</Chip><p className="mt-1 text-xs text-mute">{t("extractedNote")}</p>
          <dl className="mt-2 grid gap-x-4 gap-y-1 text-sm sm:grid-cols-2">{Object.entries(d.extracted_data).map(([k,v])=><div key={k}><dt className="text-xs text-mute">{t("field."+k)}</dt><dd>{v.value} <span className="text-xs text-mute">({Math.round(v.confidence*100)}%)</span></dd></div>)}</dl></div>}
      </motion.li>;})}</ul></section>;
}
