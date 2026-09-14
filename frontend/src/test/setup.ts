import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'
class FakeEventSource { static instances:FakeEventSource[]=[];onopen:null|(()=>void)=null; onerror:null|(()=>void)=null;closed=false;constructor(_url:string){FakeEventSource.instances.push(this)} addEventListener(){} close(){this.closed=true} }
Object.defineProperty(globalThis,'EventSource',{value:FakeEventSource,writable:true})
afterEach(()=>{cleanup();FakeEventSource.instances.forEach(source=>source.close());FakeEventSource.instances=[]})
