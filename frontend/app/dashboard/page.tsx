"use client";
import Link from "next/link";import {useEffect,useState} from "react";import {motion} from "framer-motion";
import {Chip,ErrorBox,Icon,IconName,Skeleton} from "@/components/ui";import {useT} from "@/lib/i18n";import {useAsync} from "@/hooks/useAsync";
import {getGrievances,getNextAction,getSummary} from "@/services/grievanceService";import {getMe} from "@/services/authService";
import {Grievance,NextAction} from "@/types";import {daysSince,fmtDate} from "@/lib/format";import {STAGES,stageIcon,stageTone} from "@/lib/stage";
const item={hidden:{opacity:0,y:14},show:{opacity:1,y:0}};
const wrap={hidden:{},show:{transition:{staggerChildren:.08}}};
function NextLine({id}:{id:string}){const {t}=useT();const [a,setA]=useState<NextAction|null|undefined>();useEffect(()=>{getNextAction(id).then(setA).catch(()=>setA(null));},[id]);
  return <p className="mt-3 flex items-center gap-2 border-t border-white/10 pt-3 text-sm text-ink/85"><Icon n="arrow" className="h-4 w-4 text-brand"/>{a?a.title:a===null?t("noNext"):"…"}</p>;}
export default function Dashboard(){
  const {t,lang}=useT();const g=useAsync(getGrievances,[]);const s=useAsync(getSummary,[]);const me=useAsync(getMe,[]);
  const cards:[string,string,number|undefined,IconName,string][]=[["active","activeSub",s.data?.active,"layers","text-sky-300 bg-sky-400/15"],["onTrack","onTrackSub",s.data?.on_track,"check","text-emerald-300 bg-emerald-400/15"],["delayed","delayedSub",s.data?.potentially_delayed,"alert","text-amber-300 bg-amber-400/15"],["resolved","resolvedSub",s.data?.resolved,"shield","text-indigo-200 bg-indigo-400/15"]];
  const list=g.data??[];const count=(st:string)=>list.filter(x=>x.current_stage===st).length;
  return <div className="space-y-8">
    <section className="glass relative overflow-hidden p-6 sm:p-8"><div aria-hidden className="absolute -right-10 -top-10 h-48 w-48 rounded-full bg-violet-500/20 blur-3xl"/>
      <p className="text-sm text-mute">{t("hello")}{me.data?`, ${me.data.name}`:""}</p>
      <h1 className="h-grad mt-1 max-w-2xl text-3xl font-extrabold leading-tight sm:text-4xl">{t("heroTitle")}</h1><p className="mt-3 max-w-2xl text-sm text-mute sm:text-base">{t("heroBody")}</p>
      <Link href="/grievances/new" className="btn-primary mt-5"><Icon n="plus"/>{t("newGrievance")}</Link></section>
    <motion.div variants={wrap} initial="hidden" animate="show" className="grid grid-cols-2 gap-3 lg:grid-cols-4">{cards.map(([k,sub,v,ic,c])=>
      <motion.div key={k} variants={item} className="glass glass-hover p-4"><span className={`flex h-10 w-10 items-center justify-center rounded-xl ${c}`}><Icon n={ic} className="h-5 w-5"/></span>
        {s.loading&&v===undefined?<Skeleton className="mt-3 h-8 w-12"/>:<p className="mt-3 text-3xl font-bold">{v??"–"}</p>}<p className="text-sm font-medium">{t(k)}</p><p className="text-xs text-mute">{t(sub)}</p></motion.div>)}</motion.div>
    {s.error&&<ErrorBox msg={s.error} onRetry={s.reload}/>}
    {list.length>0&&<section className="glass p-5"><h2 className="font-semibold">{t("journeyTitle")}</h2><p className="text-xs text-mute">{t("journeySub")}</p>
      <ul className="mt-4 grid grid-cols-5 gap-2">{STAGES.map(st=>{const c=count(st);return <li key={st} className={`rounded-xl border p-2 text-center ${c?"border-indigo-400/40 bg-indigo-400/10":"border-white/10 opacity-60"}`}>
        <Icon n={stageIcon[st]} className="mx-auto h-4 w-4"/><p className="mt-1 text-lg font-bold">{c}</p><p className="text-[10px] leading-tight text-mute sm:text-xs">{t("stage."+st)}</p></li>;})}</ul></section>}
    <section><h2 className="mb-3 text-lg font-semibold">{t("yourCases")}</h2>
      {g.error&&<ErrorBox msg={g.error} onRetry={g.reload}/>}
      {g.loading&&!g.data&&<div className="grid gap-4 md:grid-cols-2"><Skeleton className="h-44"/><Skeleton className="h-44"/></div>}
      {g.data&&!list.length&&<div className="glass p-10 text-center"><Icon n="inbox" className="mx-auto h-10 w-10 text-mute"/><p className="mt-3 font-semibold">{t("emptyTitle")}</p><p className="mx-auto mt-1 max-w-sm text-sm text-mute">{t("emptyBody")}</p><Link href="/grievances/new" className="btn-primary mt-5"><Icon n="plus"/>{t("newGrievance")}</Link></div>}
      <motion.div variants={wrap} initial="hidden" animate="show" className="grid gap-4 md:grid-cols-2">{list.map((x:Grievance)=>{const w=x.warnings?.some(w=>w.type==="POTENTIAL_DELAY");const d=daysSince(x.status_updated_at);
        return <motion.div key={x.id} variants={item}><Link href={`/grievances/${x.id}`} className={`glass glass-hover block p-5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand ${w?"border-amber-400/40":""}`}>
          <div className="flex items-start justify-between gap-2"><div><p className="font-bold">{x.complaint_id}</p><p className="text-sm text-mute">{x.entity_name}</p></div>
            {w&&<Chip tone="warn" icon="alert">{t("delayed")}</Chip>}</div>
          <p className="mt-2 text-sm">{x.issue_type}</p>
          <div className="mt-3 flex flex-wrap items-center gap-2"><Chip tone={stageTone[x.current_stage]} icon={stageIcon[x.current_stage]}>{t("stage."+x.current_stage)}</Chip>
            <span className="text-xs text-mute">{t("submitted")} {fmtDate(x.submission_date,lang)} · {d?t("updatedAgo",{n:d}):t("updatedToday")}</span></div>
          <NextLine id={x.id}/></Link></motion.div>;})}</motion.div></section></div>;
}
