/* Read-only IMA adapter. Reuses the installed ima-skill; never logs signed URLs or credentials. */
const fs=require('fs');const path=require('path');const os=require('os');const crypto=require('crypto');
const ROOT=path.resolve(__dirname,'..');
const stamp=()=>new Date().toISOString();
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const write=(p,d)=>fs.writeFileSync(p,JSON.stringify(d,null,2)+'\n',{flag:'wx'});
function configHome(env=process.env,home=os.homedir()){return env.CODEX_HOME||path.join(home,'.codex');}
function profilePath(opt={},env=process.env,home=os.homedir()){
  if(opt.profile)return path.resolve(opt.profile);
  if(env.FINANCIAL_RESEARCH_IMA_PROFILE)return path.resolve(env.FINANCIAL_RESEARCH_IMA_PROFILE);
  const local=path.join(configHome(env,home),'config','financial-research-report','ima-source-profile.json');
  return fs.existsSync(local)?local:path.join(ROOT,'assets','ima-source-profile.json');
}
function validateProfile(profile){
  if(profile.access_mode!=='read_only')throw Error('Only read_only profiles supported');
  if(typeof profile.knowledge_base_id!=='string'||!profile.knowledge_base_id.trim())throw Error('IMA library is not configured. See references/team-setup.md; use --profile or setup_ima.cjs init.');
  if(typeof profile.knowledge_base_name!=='string'||!profile.knowledge_base_name.trim())throw Error('knowledge_base_name is required');
  if(!Array.isArray(profile.default_queries)||profile.default_queries.some(q=>typeof q!=='string'||!q.trim()))throw Error('default_queries must contain non-empty strings');
  for(const k of ['api_key','client_id','apiKey','clientId','IMA_OPENAPI_CLIENTID','IMA_OPENAPI_APIKEY'])if(k in profile)throw Error('Keep credentials in ima-skill configuration, never in the research profile');
  positive(profile.default_page_size,'default_page_size',50);positive(profile.default_max_pages_per_route,'default_max_pages_per_route',100);positive(profile.default_max_download_mb,'default_max_download_mb',512);
  return profile;
}
function fresh(dir){if(fs.existsSync(dir)&&fs.readdirSync(dir).length)throw Error('Output must be new or empty; previous runs are preserved');fs.mkdirSync(dir,{recursive:true});}
function positive(value,name,max=1000){const n=Number(value);if(!Number.isInteger(n)||n<1||n>max)throw Error('Invalid '+name);return n;}
function args(argv){const out={queries:[],ids:[]};for(let i=0;i<argv.length;i++){const k=argv[i];if(!k.startsWith('--')||!argv[i+1]||argv[i+1].startsWith('--'))throw Error('Expected --option value');const v=argv[++i];if(k==='--query')out.queries.push(v);else if(k==='--id')out.ids.push(v);else if(['--out','--profile','--ima-skill','--previous','--resume','--folder','--max-pages','--page-size','--max-mb','--snapshot'].includes(k))out[k.slice(2)]=v;else throw Error('Unknown option '+k);}return out;}
function normalized(item,kb,route,at,previous){
  const id=item.media_id;if(!id)throw Error('IMA entry has no media_id');
  const metadata_hash=hash(Buffer.from(JSON.stringify([item.title,item.media_type,item.parent_folder_id,item.tags||[]])));
  const prior=previous.get(id);
  return {media_id:id,knowledge_base_id:kb,title:item.title||'',media_type:item.media_type,parent_folder_id:item.parent_folder_id||null,tags:item.tags||[],
    published_at:null,publication_status:'UNKNOWN_VERIFY_IN_ORIGINAL',metadata_hash,
    search_highlight:typeof item.highlight_content==='string'?item.highlight_content:null,
    change:!prior?'first_seen':prior.metadata_hash===metadata_hash?'seen_same_metadata':'metadata_changed',
    first_seen_at:prior?.first_seen_at||at,observed_at:at,discovered_via:[route],read_scope:'headline',access:'not_accessed'};
}
function pagination(data,current,seen){
  const hasEnd=Object.hasOwn(data,'is_end'),hasNext=Object.hasOwn(data,'next_cursor');
  if(hasEnd&&typeof data.is_end!=='boolean')throw Error('Malformed IMA is_end; expected boolean');
  if(hasNext&&typeof data.next_cursor!=='string')throw Error('Malformed IMA next_cursor; expected string');
  if(data.is_end===true)return{done:true,next:'',state:'COMPLETE',mode:'cursor',issue:null};
  const next=data.next_cursor;
  if(!hasEnd&&!hasNext)return{done:false,next:null,state:'UNKNOWN',mode:'not_exposed',issue:'PAGINATION_NOT_EXPOSED'};
  if(!next)return{done:false,next:null,state:'UNKNOWN',mode:'incomplete',issue:'NEXT_CURSOR_MISSING'};
  if(next===current||seen.has(next))return{done:false,next:null,state:'UNKNOWN',mode:'incomplete',issue:'CURSOR_CYCLE'};
  return{done:false,next,state:'MORE_AVAILABLE',mode:'cursor',issue:null};
}
function catalogSearch(profile,opt){
  if(!opt.snapshot)throw Error('catalog-search needs --snapshot from inventory or merged metadata');
  if(!opt.queries.length)throw Error('catalog-search needs at least one --query');
  if(opt.resume||opt.folder)throw Error('catalog-search is local title/tag matching; resume and folder are not supported');
  const source=read(opt.snapshot);
  if(source.knowledge_base_id!==profile.knowledge_base_id)throw Error('Snapshot belongs to another knowledge base');
  if(!Array.isArray(source.items))throw Error('Catalog snapshot needs items');
  const at=stamp(),items=new Map(),queries=[];
  const fold=s=>String(s).normalize('NFKC').toLocaleLowerCase().trim();
  for(const query of opt.queries){
    if(!fold(query))throw Error('Catalog query cannot be blank');
    const key='catalog:'+query;let matched=0;
    for(const raw of source.items){
      const searchable=[raw.title||'',...(raw.tags||[])].map(v=>typeof v==='object'?JSON.stringify(v):String(v)).join('\n');
      if(!fold(searchable).includes(fold(query)))continue;
      matched++;const x=normalized(raw,profile.knowledge_base_id,key,at,new Map()),old=items.get(x.media_id);
      x.first_seen_at=raw.first_seen_at||at;x.change='catalog_match';
      x.discovered_via=[...new Set([...(old?.discovered_via||raw.discovered_via||[]),key])];items.set(x.media_id,x);
    }
    queries.push({route:key,operation:'local_title_tag_match',attempted_at:at,query,returned:matched,outcome:matched?'results':'no_results'});
  }
  return{snapshot_version:1,provider:'ima',knowledge_base_name:profile.knowledge_base_name,knowledge_base_id:profile.knowledge_base_id,
    started_at:at,finished_at:stamp(),status:'CATALOG_MATCHES_ONLY',scope:'Local title/tag substring matches over the supplied metadata snapshot; not server full-text search or full-library coverage',
    catalog_source:{path:path.resolve(opt.snapshot),sha256:hash(fs.readFileSync(opt.snapshot)),status:source.status||null,scope:source.scope||null,items:source.items.length,recorded_at:source.finished_at||source.created_at||null},
    queries,routes:[],items:[...items.values()],failure:null};
}
async function discover(profile,opt,api){
  const previous=opt.previous?read(opt.previous):null,resume=opt.resume?read(opt.resume):null;
  for(const old of [previous,resume])if(old&&old.knowledge_base_id!==profile.knowledge_base_id)throw Error('Snapshot belongs to another knowledge base');
  const prev=new Map((previous?.items||[]).map(x=>[x.media_id,x]));
  const items=new Map((resume?.items||[]).map(x=>[x.media_id,x]));
  const history=resume?.queries||[];const routes=resume?.routes||[];
  if(opt.inventoryOnly&&opt.queries.length)throw Error('inventory does not accept search queries; use discover separately');
  const selected=opt.inventoryOnly?[]:(opt.queries.length?opt.queries:profile.default_queries);
  const planned=[{kind:'list',key:'list:'+(opt.folder||'root'),folder_id:opt.folder||null},...selected.map(q=>({kind:'search',key:'search:'+q,query:q}))];
  if(resume&&JSON.stringify(routes.map(x=>x.key))!==JSON.stringify(planned.map(x=>x.key)))throw Error('Resume requires the same folder and queries');
  const limit=positive(opt['page-size']||profile.default_page_size,'page-size',50);
  const budget=positive(opt['max-pages']||profile.default_max_pages_per_route,'max-pages',100);
  const result={snapshot_version:1,provider:'ima',knowledge_base_name:profile.knowledge_base_name,knowledge_base_id:profile.knowledge_base_id,started_at:stamp(),
    status:'PARTIAL',scope:'Only recorded folder/list/search routes; not a complete library or date-window scan',queries:history,routes,items:[],failure:null};
  try{
    for(const plan of planned){
      let route=routes.find(x=>x.key===plan.key);
      if(!route){route={...plan,cursor:'',done:false,pages:0};routes.push(route);}
      if(route.done)continue;
      // A resume must advance a server-supplied cursor. Replaying an unpageable first page is not progress.
      if(resume&&(route.pagination_state==='UNKNOWN'||route.stop_reason&&route.pagination_state!=='MORE_AVAILABLE')){
        route.resume_supported=false;route.resume_skipped_at=stamp();
        route.recovery='Use a new discovery cycle to retry the endpoint, or inventory real folders and catalog-search their metadata. No cursor is invented.';
        continue;
      }
      const seen=new Set(history.filter(q=>q.route===route.key).map(q=>q.input_cursor));seen.add(route.cursor);
      for(let n=0;n<budget;n++){
        const operation=route.kind==='list'?'get_knowledge_list':'search_knowledge';
        const body={knowledge_base_id:profile.knowledge_base_id,cursor:route.cursor};
        if(route.kind==='list'){body.limit=limit;if(route.folder_id)body.folder_id=route.folder_id;}else body.query=route.query;
        const at=stamp();const data=await api(operation,body);const batch=data.knowledge_list||data.info_list||[];
        if(!Array.isArray(batch))throw Error('Malformed IMA list');
        const page=pagination(data,route.cursor,seen);
        history.push({route:route.key,operation,attempted_at:at,input_cursor:route.cursor,returned:batch.length,outcome:batch.length?'results':'no_results',
          response_fields:Object.keys(data),pagination_fields:{is_end:Object.hasOwn(data,'is_end'),next_cursor:Object.hasOwn(data,'next_cursor')},
          pagination_mode:page.mode,pagination_issue:page.issue});
        for(const raw of batch){const x=normalized(raw,profile.knowledge_base_id,route.key,at,prev),old=items.get(x.media_id);
          if(old)x.discovered_via=[...new Set([...old.discovered_via,route.key])];items.set(x.media_id,x);}
        route.pages++;route.done=page.done;route.pagination_state=page.state;route.pagination_mode=page.mode;
        route.pagination_issue=page.issue;route.resume_supported=page.state==='MORE_AVAILABLE';
        delete route.stop_reason;
        if(page.issue){
          route.stop_reason=page.issue==='PAGINATION_NOT_EXPOSED'?'Pagination not exposed: response has neither is_end nor next_cursor; completeness unverified':'Pagination cannot advance: '+page.issue;
          route.recovery='Use real folder inventory plus local catalog-search for title/tag discovery; split remote queries for content leads. Neither proves full-text completeness.';
          break;
        }
        route.cursor=page.next||'';if(route.done)break;seen.add(route.cursor);
      }
    }
    result.status=routes.every(x=>x.done)?'QUERIES_COMPLETE':'PARTIAL';
  }catch(e){result.status='ACCESS_FAILED';result.failure={code:e.code??null,msg:e.msg||e.message};}
  result.items=[...items.values()];result.finished_at=stamp();return result;
}
function fileExtension(item,b){
  const ext=path.extname(item.title||'').toLowerCase();
  if(ext==='.pdf'&&b.subarray(0,5).toString()!=='%PDF-')throw Error('PDF signature mismatch');
  if(['.docx','.xlsx','.pptx'].includes(ext)&&b.subarray(0,2).toString()!=='PK')throw Error('Office ZIP signature mismatch');
  if(!['.pdf','.docx','.xlsx','.pptx','.doc','.xls','.ppt','.txt','.md','.csv'].includes(ext))throw Error('Unsupported sample file type; use the matching IMA module');
  return ext;
}
function allowedMediaUrl(raw){const u=new URL(raw);if(u.protocol!=='https:'||!(u.hostname==='ima.qq.com'||u.hostname.endsWith('.myqcloud.com')))throw Error('Unexpected IMA media destination');return u;}
async function download(info,maxBytes,fetcher=fetch){
  const target=allowedMediaUrl(info.url);const headers={...info.headers};
  for(const k of Object.keys(headers))if(/ima-openapi-clientid|ima-openapi-apikey/i.test(k))throw Error('Long-lived credentials cannot be forwarded to media hosts');
  const response=await fetcher(target,{headers,redirect:'manual',signal:AbortSignal.timeout(45000)});
  if(!response.ok)throw Error('Original download HTTP '+response.status);
  const size=Number(response.headers.get('content-length'));if(size>maxBytes)throw Error('Download exceeds configured size limit');
  const parts=[];let total=0;for await(const chunk of response.body){total+=chunk.length;if(total>maxBytes){throw Error('Download exceeds configured size limit');}parts.push(chunk);}
  return Buffer.concat(parts);
}
async function fetchOriginals(profile,opt,api,out,fetcher=fetch){
  const snapshot=read(opt.snapshot);if(snapshot.knowledge_base_id!==profile.knowledge_base_id)throw Error('Snapshot belongs to another knowledge base');
  if(!opt.ids.length)throw Error('Select original media with --id; never bulk-download the library');
  const selected=[...new Set(opt.ids)].map(id=>{const x=snapshot.items.find(x=>x.media_id===id);if(!x||x.media_type===99)throw Error('Selected file is absent from snapshot or is a folder');return x;});
  const result={provider:'ima',knowledge_base_name:profile.knowledge_base_name,knowledge_base_id:profile.knowledge_base_id,created_at:stamp(),status:'COMPLETE',files:[],failure:null};
  try{for(const item of selected){
    const data=await api('get_media_info',{media_id:item.media_id});
    if(data.media_type===11){result.status='PARTIAL';result.files.push({...item,read_scope:'not_read',access:'not_accessed',status:'NOTES_MODULE_REQUIRED'});continue;}
    if(!data.url_info?.url)throw Error('Original URL unavailable; use IMA client');
    const bytes=await download(data.url_info,positive(opt['max-mb']||profile.default_max_download_mb,'max-mb',512)*1024*1024,fetcher);
    const ext=fileExtension(item,bytes);const digest=hash(bytes);const filename=digest+ext;const target=path.join(out,filename);
    if(!fs.existsSync(target))fs.writeFileSync(target,bytes,{flag:'wx'});
    result.files.push({...item,path:path.resolve(target),sha256:digest,bytes:bytes.length,retrieved_at:stamp(),
      access:'not_accessed',read_scope:'not_read',status:'DOWNLOADED_NOT_READ',original_retrieval:{operation:'get_media_info',media_id:item.media_id},
      limitation:'Original downloaded; not yet read. Extract and inspect the relevant pages/tables before supporting claims. Signed URL and headers intentionally not persisted.'});
  }}catch(e){result.status='ACCESS_FAILED';result.failure={code:e.code??null,msg:e.msg||e.message};}
  return result;
}
async function main(){
  const [command,...raw]=process.argv.slice(2);if(!['inventory','discover','fetch','catalog-search'].includes(command))throw Error('Use inventory, discover, catalog-search or fetch; see references/ima-source.md');
  const opt=args(raw);opt.inventoryOnly=command==='inventory';if(!opt.out)throw Error('--out required');
  const profile=validateProfile(read(profilePath(opt)));
  if(command==='catalog-search'){
    const result=catalogSearch(profile,opt),out=path.resolve(opt.out);fresh(out);write(path.join(out,'ima-snapshot.json'),result);
    console.log(JSON.stringify({status:result.status,count:result.items.length,output:out,network_called:false,full_text_complete:false}));return;
  }
  const skill=opt['ima-skill']||process.env.IMA_SKILL_DIR||path.join(configHome(),'skills','ima-skill');
  const {imaApi}=require(path.join(skill,'ima_api.cjs'));
  const api=async(operation,body)=>{const raw=await imaApi('openapi/wiki/v1/'+operation,body,{baseUrl:'https://ima.qq.com'});const r=JSON.parse(raw);if(r.code!==0){const e=Error(r.msg||'IMA error');e.code=r.code;throw e;}return r.data||{};};
  const out=path.resolve(opt.out);fresh(out);
  const result=command==='fetch'?await fetchOriginals(profile,opt,api,out):await discover(profile,opt,api);
  write(path.join(out,command==='fetch'?'ima-evidence.json':'ima-snapshot.json'),result);
  console.log(JSON.stringify({status:result.status,knowledge_base:profile.knowledge_base_name,count:(result.items||result.files).length,output:out,failure:result.failure,
    blocked_routes:(result.routes||[]).filter(r=>!r.done&&r.resume_supported===false).map(r=>({key:r.key,issue:r.pagination_issue||'LEGACY_UNKNOWN',recovery:r.recovery}))}));
  if(result.status==='ACCESS_FAILED')process.exitCode=1;
}
if(require.main===module)main().catch(e=>{console.error(JSON.stringify({msg:e.msg||e.message,code:e.code??null}));process.exitCode=1;});
module.exports={discover,pagination,catalogSearch,normalized,fileExtension,allowedMediaUrl,download,fetchOriginals,configHome,profilePath,validateProfile};
