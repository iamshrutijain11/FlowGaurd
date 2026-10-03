"use client";
import Link from "next/link";import {usePathname,useRouter} from "next/navigation";import {useRef,useState} from "react";import {AnimatePresence,motion} from "framer-motion";
import {Icon} from "./ui";import LangSwitch from "./LangSwitch";import NotificationBell from "./NotificationBell";
import {useT} from "@/lib/i18n";import {useAsync} from "@/hooks/useAsync";import {useDismiss} from "@/hooks/useDismiss";import {getMe,logout} from "@/services/authService";
export default function Header(){
  const {t}=useT();const path=usePathname();const r=useRouter();const [drawer,setDrawer]=useState(false);const [um,setUm]=useState(false);const ref=useRef<HTMLDivElement>(null);
  const {data:me}=useAsync(getMe,[]);useDismiss(ref,um,()=>setUm(false));
  const links=[{href:"/dashboard",k:"dashboard"},{href:"/grievances/new",k:"newGrievance"}];
  const out=()=>{logout();r.push("/login");};
  return <header className="sticky top-0 z-40 border-b border-white/10 bg-[#0A0E1F]/70 backdrop-blur-xl">
    <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3">
      <Link href="/dashboard" className="flex items-center gap-2 font-bold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand rounded-lg">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500"><Icon n="shield" className="h-5 w-5"/></span>FlowGuard</Link>
      <nav className="hidden items-center gap-1 md:flex" aria-label="Main">{links.map(l=>{const on=path===l.href;
        return <Link key={l.href} href={l.href} aria-current={on?"page":undefined} className={`relative rounded-xl px-4 py-2 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand ${on?"text-white":"text-mute hover:text-ink"}`}>
          {on&&<motion.span layoutId="nav-pill" className="absolute inset-0 -z-10 rounded-xl bg-white/10"/>}{t(l.k)}</Link>;})}</nav>
      <div className="flex items-center gap-2"><LangSwitch/><NotificationBell/>
        <div ref={ref} className="relative hidden md:block">
          <button onClick={()=>setUm(!um)} aria-expanded={um} aria-label={me?.name??"Account"} className="flex items-center gap-2 rounded-xl border border-white/15 bg-white/5 py-1.5 pl-2 pr-3 text-sm hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"><Icon n="user" className="h-5 w-5"/><Icon n="chevron" className="h-3.5 w-3.5"/></button>
          <AnimatePresence>{um&&<motion.div initial={{opacity:0,y:-8}} animate={{opacity:1,y:0}} exit={{opacity:0,y:-8}} className="glass absolute right-0 top-12 w-60 bg-[#121735]/95 p-2">
            <div className="px-3 py-2"><p className="text-sm font-semibold">{me?.name}</p><p className="truncate text-xs text-mute">{me?.email}</p></div>
            <button onClick={out} className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm hover:bg-white/10"><Icon n="logout"/>{t("logout")}</button></motion.div>}</AnimatePresence></div>
        <button className="rounded-xl border border-white/15 bg-white/5 p-2 md:hidden focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand" aria-label={t("menu")} onClick={()=>setDrawer(true)}><Icon n="menu" className="h-5 w-5"/></button></div></div>
    <AnimatePresence>{drawer&&<motion.div className="fixed inset-0 z-50 md:hidden" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}}>
      <div className="absolute inset-0 bg-black/60" onClick={()=>setDrawer(false)}/>
      <motion.aside initial={{x:"100%"}} animate={{x:0}} exit={{x:"100%"}} transition={{type:"spring",damping:28,stiffness:300}} className="glass absolute right-0 top-0 h-full w-72 rounded-r-none bg-[#121735] p-5">
        <button autoFocus onClick={()=>setDrawer(false)} aria-label={t("close")} className="mb-4 ml-auto block rounded-lg p-1.5 hover:bg-white/10"><Icon n="x" className="h-5 w-5"/></button>
        <p className="mb-4 text-sm text-mute">{me?.name}</p>
        <nav className="flex flex-col gap-1">{links.map(l=><Link key={l.href} href={l.href} onClick={()=>setDrawer(false)} aria-current={path===l.href?"page":undefined} className={`rounded-xl px-4 py-3 text-sm font-medium ${path===l.href?"bg-white/10":"hover:bg-white/5"}`}>{t(l.k)}</Link>)}
          <button onClick={out} className="mt-2 flex items-center gap-2 rounded-xl px-4 py-3 text-left text-sm hover:bg-white/5"><Icon n="logout"/>{t("logout")}</button></nav></motion.aside></motion.div>}</AnimatePresence>
  </header>;
}
