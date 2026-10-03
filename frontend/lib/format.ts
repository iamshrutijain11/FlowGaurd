const loc=(l:string)=>l==="hi"?"hi-IN":"en-IN";
export const fmtDate=(s:string,l:string)=>new Date(s).toLocaleDateString(loc(l),{day:"numeric",month:"short",year:"numeric"});
export const fmtDT=(s:string,l:string)=>new Date(s).toLocaleString(loc(l),{day:"numeric",month:"short",hour:"numeric",minute:"2-digit"});
export const daysSince=(s:string)=>Math.max(0,Math.floor((Date.now()-new Date(s).getTime())/864e5));
export const fmtSize=(b:number)=>b>1048576?(b/1048576).toFixed(1)+" MB":Math.max(1,Math.round(b/1024))+" KB";
