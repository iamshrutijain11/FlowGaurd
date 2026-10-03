"use client";
import {useState} from "react";import Link from "next/link";import {useRouter} from "next/navigation";
import AuthShell from "@/components/AuthShell";import {Btn,Icon} from "@/components/ui";import {login} from "@/services/authService";import {useT} from "@/lib/i18n";
export default function Login(){
  const {t}=useT();const r=useRouter();const [email,setE]=useState("demo@flowguard.app");const [pw,setP]=useState("");const [show,setShow]=useState(false);const [busy,setBusy]=useState(false);const [err,setErr]=useState("");const [v,setV]=useState<{e?:string;p?:string}>({});
  async function go(e:React.FormEvent){e.preventDefault();const n:typeof v={};
    if(!/^\S+@\S+\.\S+$/.test(email))n.e=t("valEmail");if(pw.length<8&&process.env.NEXT_PUBLIC_USE_MOCK!=="true")n.p=t("valPw");setV(n);if(n.e||n.p)return;
    setBusy(true);setErr("");try{await login(email,pw);r.push("/dashboard");}catch(x){setErr((x as Error).message);}finally{setBusy(false);}}
  return <AuthShell title={t("login")} sub={t("loginSub")}><form onSubmit={go} noValidate className="space-y-4">
    <div><label htmlFor="em" className="lbl">{t("email")}</label><input id="em" type="email" autoComplete="email" value={email} onChange={e=>setE(e.target.value)} className="input" aria-invalid={!!v.e}/>{v.e&&<p className="err">{v.e}</p>}</div>
    <div><label htmlFor="pw" className="lbl">{t("password")}</label><div className="relative"><input id="pw" type={show?"text":"password"} autoComplete="current-password" value={pw} onChange={e=>setP(e.target.value)} className="input pr-11" aria-invalid={!!v.p}/>
      <button type="button" onClick={()=>setShow(!show)} aria-label={show?t("hidePw"):t("showPw")} className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-mute hover:text-ink"><Icon n={show?"eyeoff":"eye"} className="h-5 w-5"/></button></div>{v.p&&<p className="err">{v.p}</p>}</div>
    {err&&<p role="alert" className="err">{err}</p>}
    <Btn type="submit" loading={busy} className="w-full">{t("login")}</Btn>
    <p className="text-center text-sm text-mute">{t("noAccount")} <Link href="/register" className="font-semibold text-brand hover:underline">{t("register")}</Link></p></form></AuthShell>;
}
