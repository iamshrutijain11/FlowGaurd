"use client";
import {useState} from "react";import Link from "next/link";import {useRouter} from "next/navigation";
import AuthShell from "@/components/AuthShell";import {Btn,Icon} from "@/components/ui";import {register} from "@/services/authService";import {L,useT} from "@/lib/i18n";
export default function Register(){
  const {t,lang,setLang}=useT();const r=useRouter();const [f,setF]=useState({name:"",email:"",password:""});const [show,setShow]=useState(false);const [busy,setBusy]=useState(false);const [err,setErr]=useState("");const [v,setV]=useState<Record<string,string>>({});
  async function go(e:React.FormEvent){e.preventDefault();const n:Record<string,string>={};
    if(!f.name.trim())n.name=t("valReq");if(!/^\S+@\S+\.\S+$/.test(f.email))n.email=t("valEmail");if(f.password.length<8)n.password=t("valPw");setV(n);if(Object.keys(n).length)return;
    setBusy(true);setErr("");try{await register({...f,preferred_language:lang});r.push("/login");}catch(x){setErr((x as Error).message);}finally{setBusy(false);}}
  const fld=(k:"name"|"email"|"password",label:string,type:string,ac:string)=><div><label htmlFor={k} className="lbl">{label}</label><div className="relative"><input id={k} type={k==="password"&&show?"text":type} autoComplete={ac} value={f[k]} onChange={e=>setF({...f,[k]:e.target.value})} className={`input ${k==="password"?"pr-11":""}`} aria-invalid={!!v[k]}/>
    {k==="password"&&<button type="button" onClick={()=>setShow(!show)} aria-label={show?t("hidePw"):t("showPw")} className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-mute hover:text-ink"><Icon n={show?"eyeoff":"eye"} className="h-5 w-5"/></button>}</div>{v[k]&&<p className="err">{v[k]}</p>}</div>;
  return <AuthShell title={t("register")} sub={t("registerSub")}><form onSubmit={go} noValidate className="space-y-4">
    {fld("name",t("fullName"),"text","name")}{fld("email",t("email"),"email","email")}{fld("password",t("password"),"password","new-password")}
    <div><label htmlFor="lg" className="lbl">{t("language")}</label><select id="lg" value={lang} onChange={e=>setLang(e.target.value as L)} className="input"><option value="en">English</option><option value="hi">हिन्दी</option></select></div>
    {err&&<p role="alert" className="err">{err}</p>}<Btn type="submit" loading={busy} className="w-full">{t("register")}</Btn>
    <p className="text-center text-sm text-mute">{t("haveAccount")} <Link href="/login" className="font-semibold text-brand hover:underline">{t("login")}</Link></p></form></AuthShell>;
}
