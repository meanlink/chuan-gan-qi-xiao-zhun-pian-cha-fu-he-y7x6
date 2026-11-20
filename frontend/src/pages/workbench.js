import {datasets,jobs,holdbacks,validations} from '../api/entities.js';
import {workspace} from '../stores/workspace.js';
import {session} from '../stores/session.js';
import {heading} from '../components/common/shell.js';
import {table} from '../components/common/table.js';
import {esc,notify} from '../utils/dom.js';
import {submit} from '../hooks/forms.js';
import {HoldbackStatus,CaseStatus,Verdict} from '../constants/enums.js';
const bandColumns=[{key:'band',label:'温区'},{key:'n',label:'样本数'},{key:'low',label:'区间下界 °C'},{key:'high',label:'区间上界 °C'},{key:'tolerance',label:'容差 ±°C'},{key:'review',label:'验收结论'}];
export async function workbench(){
 workspace.datasets=await datasets.list();const m=workspace.meta;
 const [allJobs,allHoldbacks,allCases]=await Promise.all([jobs.list(),holdbacks.list(),validations.list()]);
 const completed=allJobs.filter(j=>j.status==='completed'),sealed=allHoldbacks.filter(h=>h.status==='sealed'),canWrite=session.user.role!=='viewer';
 const jobName=id=>{const j=allJobs.find(x=>x.id===id);return j?j.name:'#'+id;};
 const datasetName=id=>{const d=workspace.datasets.find(x=>x.id===id);return d?d.name:'#'+id;};
 const holdbackName=id=>{const h=allHoldbacks.find(x=>x.id===id);return h?h.name:'#'+id;};
 const intake=heading('03 / ANALYSIS LAB',m.workbench_title,'选择业务批次和分析口径。参数、输入指纹与计算结论随任务保存，便于复核和复现。','<button class="button" id="refresh-workbench">刷新验收状态 ↻</button>')+'<div class="workbench-grid"><section class="panel"><form id="job-form"><label>分析任务名称<input name="name" required minlength="2" value="'+esc(m.name)+' · 复核试算"></label><label>数据批次<select name="dataset_id" required>'+workspace.datasets.map(d=>'<option value="'+d.id+'">'+esc(d.name)+' · '+d.rows+' 条</option>').join('')+'</select></label><div class="parameter-grid">'+m.parameters.map(p=>'<label>'+esc(p.label)+(p.type==='select'?'<select name="param-'+esc(p.key)+'">'+p.options.map(o=>'<option value="'+esc(o.value)+'" '+(o.value==p.default?'selected':'')+'>'+esc(o.label)+'</option>').join('')+'</select>':'<input type="number" step="any" name="param-'+esc(p.key)+'" value="'+esc(p.default)+'" min="'+esc(p.min??'')+'" max="'+esc(p.max??'')+'" required>')+'</label>').join('')+'</div><button type="submit" class="primary" '+(session.user.role==='viewer'||!workspace.datasets.length?'disabled':'')+'>'+esc(m.action_label||'执行分析')+' ↗</button><p class="hint">提交后由后台任务计算。观察员可查看参数和结果，无法提交。</p></form></section><section class="method-sheet"><p class="eyebrow">METHOD / BUSINESS RULE</p><h2>'+esc(m.method)+'</h2><p>'+esc(m.tagline)+'</p><h3>业务判读边界</h3><ul>'+m.limitations.map(v=>'<li>'+esc(v)+'</li>').join('')+'</ul><div class="method-trace"><span>输入</span><strong>'+esc(m.dataset_name)+'</strong><span>输出</span><strong>可复核结果 / 参数版本 / 分发归档</strong></div></section></div>';
 const caseForm='<section class="panel"><div class="section-title"><h2>开立验证案</h2><span>用封存留样验收已完成分析</span></div><form id="case-form"><label>验证案名称<input name="name" required minlength="2" value="T-24 批次留样验收"></label><label>已完成分析<select name="job_id" id="case-job" required>'+completed.map(j=>'<option value="'+j.id+'">'+esc(j.name)+' · 补偿值 '+esc(j.params?.offset??0)+'°C</option>').join('')+'</select></label><div class="parameter-grid" id="tolerance-fields"></div><button type="submit" class="primary" '+(!canWrite||!completed.length?'disabled':'')+'>开立验证案</button><p class="hint">拟合补偿值的那批读数验收，偏差容易显得过小，因此验收只用封存留样复算。容差为各温区偏差区间允许的最大绝对偏差 °C；开案后须先锁定补偿值，才可启用留样。</p></form></section>';
 const holdbackList='<section class="panel"><div class="section-title"><h2>留样批</h2><span>'+allHoldbacks.length+' 批 · '+sealed.length+' 批封存中</span></div>'+(allHoldbacks.length?allHoldbacks.map(h=>'<article class="holdback-item"><div><strong>'+esc(h.name)+'</strong><p>'+h.rows+' 条 · 来自 '+esc(datasetName(h.dataset_id))+'</p><small>SHA256 '+esc(h.checksum.slice(0,18))+'…</small></div><span class="status">'+esc(HoldbackStatus[h.status]||h.status)+(h.case_id?' · 验证案 #'+h.case_id:'')+'</span></article>').join(''):'<div class="empty">尚无留样。接入数据时在「封存留样」中一并提交读数即可封存。</div>')+'<p class="hint">封存读数不开放查看、不参与普通分析；验收结论一经作出留样即消耗，验收失败也算用过。</p></section>';
 const caseCards=allCases.length?allCases.map(c=>{
  const job=allJobs.find(j=>j.id===c.job_id),released=job?job.released:false;
  const locked=c.locked_params?('补偿值 '+esc(c.locked_params.offset)+'°C · 置信度 '+esc(c.locked_params.confidence)+' · 重采样 '+esc(c.locked_params.resamples)+' 次'):'未锁定';
  const bands=(c.result&&c.result.bands)?table(bandColumns,c.result.bands.map(x=>({...x,review:x.pass?'在容差内 ✓':x.reason}))):'';
  let actions='';
  if(canWrite&&c.status==='open')actions='<button class="primary small" data-lock="'+c.id+'">锁定补偿值</button>';
  else if(canWrite&&c.status==='locked')actions=sealed.length?'<select class="holdback-pick" data-pick="'+c.id+'">'+sealed.map(h=>'<option value="'+h.id+'">'+esc(h.name)+' · '+h.rows+' 条</option>').join('')+'</select><button class="primary small" data-enable="'+c.id+'">启用留样并验收</button>':'<span class="hint">无封存中的留样可启用</span>';
  else if(canWrite&&c.status==='failed')actions='<button class="primary small" data-retry="'+c.id+'">恢复本案并重试</button>';
  else if(c.status==='queued'||c.status==='running')actions='<span class="hint">后台验收计算中，稍候刷新。</span>';
  return '<article class="case-card"><div class="case-head"><strong>'+esc(c.name)+'</strong><span class="status">'+esc(CaseStatus[c.status]||c.status)+'</span></div><p>基准分析：'+esc(jobName(c.job_id))+' · 放行状态：'+(released?'<b class="verdict released">已准许放行</b>':'<b class="verdict">未放行</b>')+'</p><p>锁定口径：'+locked+' · 留样：'+(c.holdback_id?esc(holdbackName(c.holdback_id)):'未启用')+'</p>'+(c.verdict?'<p>验收结论：<b class="verdict '+esc(c.verdict)+'">'+esc(Verdict[c.verdict]||c.verdict)+'</b> '+esc(c.result?.summary||'')+'</p>':'')+(c.error?'<p class="warning">'+esc(c.error)+'</p>':'')+bands+'<div class="case-actions">'+actions+'</div></article>';
 }).join(''):'<div class="empty">尚无验证案。选择一份已完成分析开立验证案，用封存留样独立验收。</div>';
 const validation='<section class="panel validation"><div class="section-title"><h2>留样验收</h2><span>锁定补偿值 · 独立留样复算 · 分温区放行</span></div><div class="validation-grid">'+caseForm+holdbackList+'</div><div class="section-title"><h2>验证案</h2><span>'+allCases.length+' 案</span></div><div class="case-list">'+caseCards+'</div></section>';
 return intake+validation;
}
async function fillTolerances(){
 const select=document.querySelector('#case-job'),box=document.querySelector('#tolerance-fields');
 if(!select||!box||!select.value)return;
 try{
  const j=await jobs.get(select.value),rows=j.result?.table?.rows||[];
  box.innerHTML=rows.length?rows.map(r=>'<label>温区 '+esc(r.band)+' 容差 °C<input type="number" step="any" min="0.0001" max="5" value="0.5" data-tol-band="'+esc(r.band)+'" required></label>').join(''):'<p class="hint">该分析没有温区结果，无法开立验证案。</p>';
 }catch(e){notify(e.message,true);}
}
export function bindWorkbench(refresh){
 submit(document.querySelector('#job-form'),async f=>{const params={};for(const p of workspace.meta.parameters){const value=f.get('param-'+p.key);params[p.key]=p.type==='number'?Number(value):value;}const j=await jobs.create({name:f.get('name'),dataset_id:Number(f.get('dataset_id')),params});workspace.selectedJob=j.id;notify('分析任务已提交');location.hash='#/results/'+j.id;});
 document.querySelector('#refresh-workbench')?.addEventListener('click',refresh);
 document.querySelector('#case-job')?.addEventListener('change',fillTolerances);
 fillTolerances();
 submit(document.querySelector('#case-form'),async f=>{
  const tolerances={};
  document.querySelectorAll('[data-tol-band]').forEach(input=>{tolerances[input.dataset.tolBand]=Number(input.value);});
  await validations.create({name:f.get('name'),job_id:Number(f.get('job_id')),tolerances});
  notify('验证案已开立，请先锁定补偿值');await refresh();
 });
 document.querySelectorAll('[data-lock]').forEach(b=>b.onclick=async()=>{try{await validations.lock(b.dataset.lock);notify('补偿值已锁定，可启用留样');await refresh();}catch(e){notify(e.message,true);}});
 document.querySelectorAll('[data-enable]').forEach(b=>b.onclick=async()=>{try{const pick=document.querySelector('[data-pick="'+b.dataset.enable+'"]');await validations.enable(Number(b.dataset.enable),Number(pick.value));notify('留样已启用，验收计算已排队');await refresh();}catch(e){notify(e.message,true);}});
 document.querySelectorAll('[data-retry]').forEach(b=>b.onclick=async()=>{try{await validations.retry(b.dataset.retry);notify('已恢复本案，重试不重复消耗留样');await refresh();}catch(e){notify(e.message,true);}});
}
