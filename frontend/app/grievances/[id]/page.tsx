"use client";
import Link from "next/link";import {useParams} from "next/navigation";import {useState} from "react";import {motion} from "framer-motion";
import {Btn,Chip,ErrorBox,Icon,Skeleton} from "@/components/ui";import StatusPipeline from "@/components/StatusPipeline";import WarningCard from "@/components/WarningCard";import ExplanationCard from "@/components/ExplanationCard";
import NextActionCard from "@/components/NextActionCard";import Timeline from "@/components/Timeline";import DocumentList from "@/components/DocumentList";import Modal from "@/components/Modal";import {useToast} from "@/components/Toast";
import {useT} from "@/lib/i18n";import {useAsync} from "@/hooks/useAsync";import {getGrievance,getEvents,getNextAction,getAIExplanation,markNextActionCompleted} from "@/services/grievanceService";import {getDocuments} from "@/services/documentService";
import {daysSince,fmtDate} from "@/lib/format";import {stageIcon,stageTone} from "@/lib/stage";import {isAvailable} from "@/lib/evidence";
export default function Detail(){
  const {id}=useParams<{id:string}>();const {t,lang}=useT();const toast=useToast();
  const g=useAsync(()=>getGrievance(id),[id]);const ev=useAsync(()=>getEvents(id),[id]);const dc=useAsync(()=>getDocuments(id),[id]);const na=useAsync(()=>getNextAction(id),[id]);const ai=useAsync(()=>getAIExplanation(id),[id]);
  const [modal,setModal]=useState<"guide"|"evidence"|null>(null);const [busy,setBusy]=useState(false);const [done,setDone]=useState(false);
  if(g.error)return <ErrorBox msg={g.error} onRetry={g.reload}/>;
  if(!g.data)return <div className="space-y-4"><Skeleton className="h-52"/><Skeleton className="h-32"/><div className="grid gap-4 lg:grid-cols-5"><Skeleton className="h-64 lg:col-span-3"/><Skeleton className="h-64 lg:col-span-2"/></div></div>;
  const x=g.data;const docs=dc.data??[];const events=ev.data??[];const warn=(x.warning&&x.warning.type==="POTENTIAL_DELAY"?x.warning:undefined)??x.warnings?.find(w=>w.type==="POTENTIAL_DELAY");const d=daysSince(x.status_updated_at);
  async function complete(){setBusy(true);try{await markNextActionCompleted(id);setDone(true);toast(t("doneToast"));ev.reload();}catch(e){toast((e as Error).message,"bad");}finally{setBusy(false);}}
  return <div className="space-y-6">
    <Link href="/dashboard" className="inline-flex items-center gap-1 text-sm text-mute hover:text-ink"><span className="rotate-180"><Icon n="arrow"/></span>{t("backToDash")}</Link>
    <motion.section initial={{opacity:0,y:14}} animate={{opacity:1,y:0}} className="glass relative overflow-hidden p-6 sm:p-8"><div aria-hidden className="absolute -right-16 -top-16 h-56 w-56 rounded-full bg-indigo-500/25 blur-3xl"/>
      <div className="flex flex-wrap items-center gap-2"><Chip tone={stageTone[x.current_stage]} icon={stageIcon[x.current_stage]} className="!px-3 !py-1 !text-sm">{t("stage."+x.current_stage)}</Chip>
        {warn&&<Chip tone="warn" icon="alert" className="!px-3 !py-1 !text-sm">{t("delayed")}</Chip>}<Chip icon="file">{t("recordedFact")}</Chip></div>
      <h1 className="h-grad mt-3 text-3xl font-extrabold sm:text-4xl">{x.complaint_id}</h1><p className="mt-1 text-mute">{x.entity_name}</p>
      <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-3"><div><dt className="text-xs text-mute">{t("issue")}</dt><dd>{x.issue_type}</dd></div><div><dt className="text-xs text-mute">{t("submittedOn")}</dt><dd>{fmtDate(x.submission_date,lang)}</dd></div>
        <div><dt className="text-xs text-mute">{t("latestUpdate")}</dt><dd>{fmtDate(x.status_updated_at,lang)} · {d?t("updatedAgo",{n:d}):t("updatedToday")}</dd></div></dl>
      <div className="mt-5 flex flex-wrap gap-2" aria-label={t("quickActions")}><Btn onClick={()=>setModal("guide")}>{t("viewGuidance")}</Btn><Btn variant="ghost" onClick={()=>setModal("evidence")}>{t("prepEvidence")}</Btn></div></motion.section>
    <section className="glass p-5 sm:p-6" aria-label={t("pipelineTitle")}><h2 className="mb-5 text-lg font-semibold">{t("pipelineTitle")}</h2><StatusPipeline stage={x.current_stage}/></section>
    <div className="grid gap-6 lg:grid-cols-5">
      <div className="space-y-6 lg:col-span-3">
        {warn&&<WarningCard w={warn} events={events}/>}
        {ai.error?<ErrorBox msg={ai.error} onRetry={ai.reload}/>:ai.data?<ExplanationCard x={ai.data}/>:<Skeleton className="h-56"/>}
        {na.error?<ErrorBox msg={na.error} onRetry={na.reload}/>:na.data?<NextActionCard a={na.data} docs={docs} onGuidance={()=>setModal("guide")} onEvidence={()=>setModal("evidence")} onComplete={complete} completing={busy} completed={done}/>:<Skeleton className="h-56"/>}</div>
      <div className="space-y-6 lg:col-span-2">
        {dc.error?<ErrorBox msg={dc.error} onRetry={dc.reload}/>:dc.loading&&!dc.data?<Skeleton className="h-40"/>:<DocumentList docs={docs}/>}
        {ev.error?<ErrorBox msg={ev.error} onRetry={ev.reload}/>:ev.loading&&!ev.data?<Skeleton className="h-64"/>:<Timeline events={events}/>}</div></div>
    <Modal open={modal==="guide"} onClose={()=>setModal(null)} title={t("guidanceTitle")}>{na.data&&(()=>{
      const src = typeof na.data.official_source === "string" ? na.data.official_source : (na.data.official_source ? JSON.stringify(na.data.official_source) : "");
      const match = src.match(/https?:\/\/[^\s)]+/);
      const url = match ? match[0] : null;
      return <div className="space-y-4">
        <div><Chip tone="info" icon="cog">{t("suggestedAction")}</Chip><p className="mt-2 font-semibold">{typeof na.data.title === "string" ? na.data.title : JSON.stringify(na.data.title)}</p><p className="text-sm text-ink/80">{typeof na.data.description === "string" ? na.data.description : JSON.stringify(na.data.description)}</p></div>
        <div className="rounded-xl border border-emerald-400/20 bg-emerald-400/[0.05] p-3"><Chip tone="ok" icon="shield">{t("verifiedGuidance")}</Chip>
          {src?(url?<a href={url} target="_blank" rel="noopener noreferrer" className="mt-2 flex items-center gap-1.5 text-sm font-semibold text-emerald-300 hover:underline"><Icon n="link"/>{src.length > 50 && !src.startsWith("http") ? src : t("officialLink")}</a>:<p className="mt-2 text-sm">{src}</p>):<p className="mt-2 text-sm text-mute">{t("noSource")}</p>}</div></div>;
    })()}</Modal>
    <Modal open={modal==="evidence"} onClose={()=>setModal(null)} title={t("evidenceTitle")}><div className="space-y-4">
      {na.data&&(()=>{
        const raw = Array.isArray(na.data.required_documents) ? na.data.required_documents : na.data.required_documents ? [na.data.required_documents] : [];
        return <ul className="space-y-2">{raw.map((item, idx)=>{
          const r = typeof item === "string" ? item : (typeof item === "object" && item !== null ? ((item as any).name || (item as any).title || JSON.stringify(item)) : String(item));
          const ok=isAvailable(r,docs);
          return <li key={`${r}-${idx}`} className="flex items-center justify-between gap-3 text-sm"><span>{r}</span><Chip tone={ok?"ok":"neutral"} icon={ok?"check":undefined}>{ok?t("haveIt"):t("notYet")}</Chip></li>;
        })}</ul>;
      })()}
      <div><p className="mb-2 text-xs text-mute">{t("yourFiles")}</p>{docs.length?<ul className="space-y-1 text-sm">{docs.map(dd=><li key={dd.id} className="flex items-center gap-2"><Icon n="file" className="h-4 w-4 text-indigo-300"/>{dd.file_name}</li>)}</ul>:<p className="text-sm text-mute">{t("noDocs")}</p>}</div>
      <p className="text-xs text-mute">{t("usefulInfo")}</p></div></Modal>
  </div>;
}
