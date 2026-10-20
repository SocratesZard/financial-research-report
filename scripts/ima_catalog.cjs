/* Read-only visible-folder inventory with real cursors and resumable batch budgets. */
const fs=require('fs'),path=require('path');
const adapter=require('./ima_source.cjs');
const stamp=()=>new Date().toISOString();
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const write=(p,v)=>fs.writeFileSync(p,JSON.stringify(v,null,2)+'\n');
function integer(v,name,max){const n=Number(v);if(!Number.isInteger(n)||n<1||n>max)throw Error('Invalid '+name);return n;}
async function catalog(profile,opt,api){
 const out=path.resolve(opt.out);if(fs.existsSync(out)&&fs.readdirSync(out).length)throw Error('Use a new or empty output directory');
 const old=opt.resume?read(opt.resume):null;
 if(old&&old.knowledge_base_id!==profile.knowledge_base_id)throw Error('Resume belongs to another library');
 if(old&&opt.folder&&old.start_folder_id!==opt.folder)throw Error('Resume must use the same start folder');
 const maxFolders=integer(opt['max-folders']||50,'max-folders',10000);
 const maxPages=integer(opt['max-pages']||profile.default_max_pages_per_route,'max-pages',100);
 const pageSize=integer(opt['page-size']||profile.default_page_size,'page-size',50);
 fs.mkdirSync(out,{recursive:true});
 const start=old?.start_folder_id||opt.folder||null;
 const folders=new Map((old?.folders||[]).map(x=>[x.key,{...x}]));
 const queue=old?[...old.pending_folders]:[{key:start||'root',folder_id:start,title:start?'Selected folder':'Root'}];
 const known=new Set([...folders.keys(),...queue.map(x=>x.key)]);
 const blocked=[...(old?.blocked_folders||[])];
 const items=new Map((old?.items||[]).map(x=>[x.media_id,{...x}]));
 const result={snapshot_version:1,provider:'ima',knowledge_base_name:profile.knowledge_base_name,knowledge_base_id:profile.knowledge_base_id,started_at:stamp(),start_folder_id:start,status:'PARTIAL',scope:'Only recursively visible folder metadata in the selected scope; no original downloads, content reading, server full-text search or full-library guarantee.',folders:[],pending_folders:[],blocked_folders:blocked,items:[],failure:null};
 function save(){result.finished_at=stamp();result.folders=[...folders.values()];result.pending_folders=queue;result.items=[...items.values()];write(path.join(out,'ima-snapshot.json'),result);}
 for(let step=0;step<maxFolders&&queue.length;step++){
  const plan=queue.shift(),previous=folders.get(plan.key);
  const folderOut=path.join(out,'folders',String(step+1).padStart(4,'0'));fs.mkdirSync(folderOut,{recursive:true});
  const opts={queries:[],inventoryOnly:true,'max-pages':maxPages,'page-size':pageSize};
  if(plan.folder_id)opts.folder=plan.folder_id;
  if(previous?.snapshot_path)opts.resume=previous.snapshot_path;
  const snapshot=await adapter.discover(profile,opts,api);
  const snapshotPath=path.join(folderOut,'ima-snapshot.json');write(snapshotPath,snapshot);
  const route=snapshot.routes[0];folders.set(plan.key,{...plan,snapshot_path:snapshotPath,status:snapshot.status,pages:route?.pages||0,done:route?.done===true,pagination_state:route?.pagination_state||'UNKNOWN'});
  for(const item of snapshot.items){
   const prior=items.get(item.media_id);const merged={...item,discovered_via:[...new Set([...(prior?.discovered_via||[]),...item.discovered_via])]};items.set(item.media_id,merged);
   if(item.media_type===99&&!known.has(item.media_id)){known.add(item.media_id);queue.push({key:item.media_id,folder_id:item.media_id,title:item.title});}
  }
  if(snapshot.status==='ACCESS_FAILED'){queue.unshift(plan);result.failure=snapshot.failure;result.status='ACCESS_FAILED';save();return result;}
  let deferred=false;
  if(!route?.done){
   if(route?.pagination_state==='MORE_AVAILABLE'){queue.unshift(plan);deferred=true;}
   else blocked.push({...plan,issue:route?.pagination_issue||'UNKNOWN'});
  }
  // A route gets one page budget per invocation; defer it until the next explicit resume.
  save();
  if(deferred)break;
 }
 result.status=queue.length||blocked.length?'PARTIAL':'VISIBLE_SCOPE_ENUMERATED';save();return result;
}
async function main(){
 const opt={};const argv=process.argv.slice(2);
 for(let i=0;i<argv.length;i+=2){if(!['--out','--resume','--folder','--profile','--ima-skill','--max-folders','--max-pages','--page-size'].includes(argv[i])||!argv[i+1])throw Error('Expected supported --option value');opt[argv[i].slice(2)]=argv[i+1];}
 if(!opt.out)throw Error('--out is required');
 const profile=adapter.validateProfile(read(adapter.profilePath(opt)));
 const skill=opt['ima-skill']||process.env.IMA_SKILL_DIR||path.join(adapter.configHome(),'skills','ima-skill');
 const {imaApi}=require(path.join(skill,'ima_api.cjs'));
 const api=async(operation,body)=>{const r=JSON.parse(await imaApi('openapi/wiki/v1/'+operation,body,{baseUrl:'https://ima.qq.com'}));if(r.code!==0){const e=Error(r.msg||'IMA request failed');e.code=r.code;throw e;}return r.data||{};};
 const r=await catalog(profile,opt,api);console.log(JSON.stringify({status:r.status,folders:r.folders.length,items:r.items.length,pending:r.pending_folders.length,blocked:r.blocked_folders.length,failure:r.failure}));if(r.status==='ACCESS_FAILED')process.exitCode=1;
}
if(require.main===module)main().catch(e=>{console.error(JSON.stringify({error:e.message}));process.exitCode=1;});
module.exports={catalog};
