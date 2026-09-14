export type Incident={id:string;service:string;severity:string;title:string;status:string;opened_at:string;updated_at:string;resolved_at:string|null}
export type IncidentFilters={service?:string;severity?:string;from?:string;to?:string}
export type IncidentDetail=Incident&{fingerprint:string;logs:{id:string;timestamp:string;severity:string;message:string}[];timeline:{to:string;at:string;actor:string}[];analysis:{summary:string;severity_reason:string;candidates:{cause:string;reasoning:string;evidence_log_ids:string[]}[];checklist:string[]}}
export class ApiError extends Error{constructor(message:string,public status:number){super(message)}}
async function parse<T>(r:Response):Promise<T>{if(!r.ok){const p=await r.json().catch(()=>null);throw new ApiError(p?.error?.message??'요청을 처리하지 못했습니다.',r.status)}return r.json()}
export async function fetchIncidents(f:IncidentFilters={},signal?:AbortSignal){const q=new URLSearchParams(Object.entries(f).filter(([,v])=>v) as [string,string][]);return parse<Incident[]>(await fetch(`/api/incidents?${q}`,{signal}))}
export async function fetchIncident(id:string){return parse<IncidentDetail>(await fetch(`/api/incidents/${id}`))}
export async function changeStatus(id:string,status:string){return parse<Incident>(await fetch(`/api/incidents/${id}/status`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status,actor:'dashboard'})}))}
