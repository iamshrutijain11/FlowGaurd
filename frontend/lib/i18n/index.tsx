"use client";
import {createContext,ReactNode,useContext,useEffect,useState} from "react";
import {en} from "./en";import {hi} from "./hi";
export type L="en"|"hi";
type TFn=(k:string,v?:Record<string,string|number>)=>string;
const C=createContext<{lang:L;setLang:(l:L)=>void;t:TFn}>({lang:"en",setLang:()=>{},t:k=>k});
export function LangProvider({children}:{children:ReactNode}){
  const [lang,set]=useState<L>("en");
  useEffect(()=>{if(localStorage.getItem("fg_lang")==="hi")set("hi");},[]);
  useEffect(()=>{document.documentElement.lang=lang;},[lang]);
  const setLang=(l:L)=>{set(l);localStorage.setItem("fg_lang",l);};
  const d:Record<string,string>=lang==="hi"?hi:en;
  const t:TFn=(k,v)=>{let s=d[k]??k;if(v)for(const x in v)s=s.replace(`{${x}}`,String(v[x]));return s;};
  return <C.Provider value={{lang,setLang,t}}>{children}</C.Provider>;
}
export const useT=()=>useContext(C);
