"use client";
import {RefObject,useEffect} from "react";
export function useDismiss(ref:RefObject<HTMLElement>,open:boolean,close:()=>void){
  useEffect(()=>{if(!open)return;
    const d=(e:MouseEvent)=>{if(ref.current&&!ref.current.contains(e.target as Node))close();};
    const k=(e:KeyboardEvent)=>e.key==="Escape"&&close();
    document.addEventListener("mousedown",d);document.addEventListener("keydown",k);
    return()=>{document.removeEventListener("mousedown",d);document.removeEventListener("keydown",k);};},[open,ref,close]);
}
