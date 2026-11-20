import {api} from './client.js';
export const datasets={list:()=>api('/datasets'),get:id=>api('/datasets/'+id),create:data=>api('/datasets',{method:'POST',body:JSON.stringify(data)})};
export const jobs={list:()=>api('/jobs'),get:id=>api('/jobs/'+id),create:data=>api('/jobs',{method:'POST',body:JSON.stringify(data)}),approve:id=>api('/jobs/'+id+'/approve',{method:'POST'})};
export const reports={list:()=>api('/reports'),create:data=>api('/reports',{method:'POST',body:JSON.stringify(data)}),toggle:id=>api('/reports/'+id+'/toggle',{method:'POST'}),deliveries:()=>api('/deliveries')};
export const holdbacks={list:()=>api('/holdbacks')};
export const validations={list:()=>api('/validation-cases'),get:id=>api('/validation-cases/'+id),create:data=>api('/validation-cases',{method:'POST',body:JSON.stringify(data)}),lock:id=>api('/validation-cases/'+id+'/lock',{method:'POST'}),enable:(id,holdback_id)=>api('/validation-cases/'+id+'/enable',{method:'POST',body:JSON.stringify({holdback_id})}),retry:id=>api('/validation-cases/'+id+'/retry',{method:'POST'})};
