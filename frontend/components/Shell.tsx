"use client";
import {ReactNode,useEffect,useState} from "react";import {usePathname,useRouter} from "next/navigation";import {motion} from "framer-motion";
import Header from "./Header";import {Icon} from "./ui";import {useT} from "@/lib/i18n";import {isLoggedIn} from "@/services/authService";
export default function Shell({children}:{children:ReactNode}){
  const path=usePathname();const r=useRouter();const {t}=useT();const auth=path==="/login"||path==="/register";const [ok,setOk]=useState(false);
  useEffect(()=>{if(auth){setOk(true);return;}if(isLoggedIn())setOk(true);else r.replace("/login");},[auth,r]);
  return <div className="relative min-h-screen overflow-x-hidden">
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,#1b1f4a_0%,#0A0E1F_60%)]">
      <div className="orb -left-24 top-10 h-96 w-96 bg-indigo-600"/><div className="orb -right-24 top-1/3 h-[28rem] w-[28rem] bg-violet-700" style={{animationDelay:"-8s"}}/><div className="orb bottom-0 left-1/3 h-80 w-80 bg-sky-700 opacity-20"/></div>
    {!auth&&<Header/>}
    {ok&&<motion.main key={path} initial={{opacity:0,y:12}} animate={{opacity:1,y:0}} transition={{duration:.35,ease:"easeOut"}} className={auth?"":"mx-auto max-w-6xl px-4 py-6 sm:py-8"}>{children}</motion.main>}
    {!auth&&<footer className="mx-auto flex max-w-6xl items-center justify-center gap-2 px-4 pb-8 text-xs text-mute"><Icon n="shield" className="h-3.5 w-3.5"/>{t("brandTag")}</footer>}
  </div>;
}
