import {Stage} from "@/types";import type {IconName,Tone} from "@/components/ui";
export const STAGES:Stage[]=["FILED","ACKNOWLEDGED","AWAITING_RESPONSE","RESPONSE_RECEIVED","RESOLVED"];
export const stageSteps=(s:Stage):Stage[]=>s==="FURTHER_ACTION"?[...STAGES.slice(0,4),"FURTHER_ACTION"]:STAGES;
export const stageTone:Record<Stage,Tone>={FILED:"info",ACKNOWLEDGED:"info",AWAITING_RESPONSE:"brand",RESPONSE_RECEIVED:"ok",RESOLVED:"ok",FURTHER_ACTION:"neutral"};
export const stageIcon:Record<Stage,IconName>={FILED:"file",ACKNOWLEDGED:"inbox",AWAITING_RESPONSE:"clock",RESPONSE_RECEIVED:"mail",RESOLVED:"check",FURTHER_ACTION:"arrow"};
