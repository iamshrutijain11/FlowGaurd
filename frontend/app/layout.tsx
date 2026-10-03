import "./globals.css";import type {Metadata,Viewport} from "next";import {Plus_Jakarta_Sans,Noto_Sans_Devanagari} from "next/font/google";import Providers from "./providers";
const lat=Plus_Jakarta_Sans({subsets:["latin"],variable:"--f-lat",display:"swap"});
const dev=Noto_Sans_Devanagari({subsets:["devanagari","latin"],variable:"--f-dev",display:"swap"});
export const metadata:Metadata={title:"FlowGuard",description:"Investor grievance tracking • Evidence-based"};
export const viewport:Viewport={themeColor:"#0A0E1F"};
export default function RootLayout({children}:{children:React.ReactNode}){
  return <html lang="en" className={`${lat.variable} ${dev.variable}`}><body><Providers>{children}</Providers></body></html>;
}
