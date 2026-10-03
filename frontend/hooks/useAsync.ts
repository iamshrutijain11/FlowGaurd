"use client";
import {useCallback,useEffect,useState} from "react";
export function useAsync<T>(fn:()=>Promise<T>,deps:unknown[]=[]){
  const [s,set]=useState<{data?:T;loading:boolean;error?:string}>({loading:true});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run=useCallback(()=>{set(p=>({...p,loading:true,error:undefined}));return fn().then(d=>set({data:d,loading:false})).catch((e:Error)=>set({loading:false,error:e.message}));},deps);
  useEffect(()=>{run();},[run]);
  return {...s,reload:run};
}
