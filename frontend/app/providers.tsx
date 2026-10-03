"use client";
import {ReactNode} from "react";import {MotionConfig} from "framer-motion";import {LangProvider} from "@/lib/i18n";import {ToastProvider} from "@/components/Toast";import Shell from "@/components/Shell";
export default function Providers({children}:{children:ReactNode}){
  return <MotionConfig reducedMotion="user"><LangProvider><ToastProvider><Shell>{children}</Shell></ToastProvider></LangProvider></MotionConfig>;
}
