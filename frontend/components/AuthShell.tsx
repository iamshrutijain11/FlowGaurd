"use client";
import {ReactNode} from "react";import {motion} from "framer-motion";import {Icon} from "./ui";import LangSwitch from "./LangSwitch";import StatusPipeline from "./StatusPipeline";import {useT} from "@/lib/i18n";
export default function AuthShell({title,sub,children}:{title:string;sub:string;children:ReactNode}){
  const {t}=useT();
  return <div className="mx-auto grid min-h-screen max-w-6xl items-center gap-10 px-4 py-8 lg:grid-cols-2">
    <div className="absolute right-4 top-4"><LangSwitch/></div>
    <div className="hidden lg:block"><span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-500"><Icon n="shield" className="h-6 w-6"/></span>
      <h1 className="h-grad mt-6 text-5xl font-extrabold leading-tight">{t("authHeadline")}</h1><p className="mt-4 max-w-md text-mute">{t("authBody")}</p>
      <div className="glass mt-8 max-w-lg p-5"><StatusPipeline stage="AWAITING_RESPONSE"/></div>
      <p className="mt-6 flex items-center gap-2 text-xs text-mute"><Icon n="shield" className="h-3.5 w-3.5"/>{t("brandTag")}</p></div>
    <motion.div initial={{opacity:0,y:16}} animate={{opacity:1,y:0}} className="glass mx-auto w-full max-w-md p-7">
      <p className="mb-5 flex items-center gap-2 font-bold lg:hidden"><Icon n="shield" className="h-5 w-5 text-brand"/>FlowGuard</p>
      <h2 className="text-2xl font-bold">{title}</h2><p className="mt-1 mb-6 text-sm text-mute">{sub}</p>{children}</motion.div></div>;
}
