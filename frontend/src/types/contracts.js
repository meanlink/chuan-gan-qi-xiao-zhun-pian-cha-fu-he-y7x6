/** @typedef {{id:number,name:string,source:string,rows:number,checksum:string,holdbacks?:Holdback[]}} Dataset */
/** @typedef {{id:number,name:string,dataset_id:number,status:string,result:Object,approved:boolean,released:boolean}} AnalysisJob */
/** @typedef {{id:number,name:string,job_id:number,destination:string,next_run:number,enabled:boolean}} ReportSchedule */
/** @typedef {{id:number,name:string,dataset_id:number,rows:number,checksum:string,status:string,case_id:number|null}} Holdback */
/** @typedef {{id:number,name:string,job_id:number,tolerances:Object,locked_params:Object|null,holdback_id:number|null,status:string,verdict:string,result:Object}} ValidationCase */
export {};
