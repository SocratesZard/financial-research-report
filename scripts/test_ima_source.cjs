/* Offline adapter invariants; fictional metadata, no account/network access. */
const assert=require('assert/strict');const fs=require('fs');const os=require('os');const path=require('path');
const {discover,pagination,catalogSearch,normalized,allowedMediaUrl,download,fetchOriginals,profilePath,validateProfile}=require('./ima_source.cjs');
const {spawnSync}=require('child_process');
const profile={knowledge_base_id:'synthetic-kb',knowledge_base_name:'SYNTHETIC',default_queries:['alpha'],default_max_pages_per_route:1,default_page_size:2,default_max_download_mb:1};
const raw={media_id:'synthetic-media',title:'synthetic.pdf',media_type:1,parent_folder_id:'root'};
const checks=[];async function check(name,fn){await fn();checks.push(name);}
(async()=>{
await check('Pagination budget preserves partial scope and next cursor',async()=>{
 const r=await discover(profile,{queries:['alpha']},async()=>({knowledge_list:[raw],is_end:false,next_cursor:'NEXT'}));
 assert.equal(r.status,'PARTIAL');assert.equal(r.items.length,1);assert.equal(r.routes[0].cursor,'NEXT');assert.equal(r.items[0].published_at,null);
});
await check('Missing cursor never becomes complete',async()=>{
 const r=await discover(profile,{queries:['alpha']},async()=>({info_list:[raw]}));assert.equal(r.status,'PARTIAL');assert.ok(r.routes[0].stop_reason);
});
await check('Inventory paginates the selected folder without invoking keyword search',async()=>{
 let calls=0;const r=await discover(profile,{inventoryOnly:true,queries:[],folder:'synthetic-folder','max-pages':2},async(op,body)=>{
  assert.equal(op,'get_knowledge_list');assert.equal(body.folder_id,'synthetic-folder');calls++;
  assert.equal(body.cursor,calls===1?'':'NEXT');
  return{knowledge_list:calls===1?[raw]:[],is_end:calls===2,next_cursor:calls===1?'NEXT':''};
 });
 assert.equal(calls,2);assert.equal(r.status,'QUERIES_COMPLETE');assert.equal(r.routes.length,1);assert.equal(r.routes[0].pagination_state,'COMPLETE');
 await assert.rejects(()=>discover(profile,{inventoryOnly:true,queries:['alpha']},async()=>({})),/does not accept/);
});
await check('Search highlights and actual response shape remain metadata with unknown pagination',async()=>{
 const r=await discover(profile,{queries:['alpha']},async(op)=>op==='get_knowledge_list'?{knowledge_list:[],is_end:true}:{info_list:[{...raw,highlight_content:'synthetic excerpt'}]});
 assert.equal(r.status,'PARTIAL');assert.equal(r.routes[1].pagination_state,'UNKNOWN');assert.deepEqual(r.queries[1].response_fields,['info_list']);
 assert.equal(r.items[0].search_highlight,'synthetic excerpt');assert.equal(r.items[0].read_scope,'headline');assert.equal(r.items[0].access,'not_accessed');
});
await check('Business failure stops dependent calls',async()=>{
 let calls=0;const r=await discover(profile,{queries:['alpha','beta']},async()=>{calls++;const e=Error('synthetic denied');e.code=220030;throw e;});assert.equal(calls,1);assert.equal(r.status,'ACCESS_FAILED');assert.equal(r.failure.code,220030);
});
await check('Known metadata does not imply content unchanged or original publication',()=>{
 const a=normalized(raw,'synthetic-kb','q','2024-01-01T00:00:00Z',new Map());
 const b=normalized(raw,'synthetic-kb','q','2024-01-02T00:00:00Z',new Map([[a.media_id,a]]));assert.equal(b.change,'seen_same_metadata');assert.equal(b.published_at,null);assert.equal(b.first_seen_at,a.first_seen_at);
});
await check('Reject unrelated media host and long-lived credential forwarding',async()=>{
 assert.throws(()=>allowedMediaUrl('https://example.com/a'));assert.throws(()=>allowedMediaUrl('http://ima.qq.com/a'));
 await assert.rejects(()=>download({url:'https://x.myqcloud.com/a',headers:{'ima-openapi-apikey':'synthetic'}},99),/credentials/);
});
await check('Streaming byte limit enforced',async()=>{
 await assert.rejects(()=>download({url:'https://x.myqcloud.com/a'},4,async()=>({ok:true,headers:new Map(),body:(async function*(){yield Buffer.from('12345');})()})),/limit/);
});
const td=fs.mkdtempSync(path.join(os.tmpdir(),'ima-adapter-test-'));
try{
await check('Unpageable search resume does not replay its first page or claim completion',async()=>{
 const first=await discover(profile,{queries:['alpha']},async(op)=>op==='get_knowledge_list'?{knowledge_list:[],is_end:true}:{info_list:[raw]});
 assert.equal(first.routes[1].pagination_mode,'not_exposed');assert.equal(first.routes[1].pagination_issue,'PAGINATION_NOT_EXPOSED');
 assert.equal(first.routes[1].resume_supported,false);
 const snapshot=path.join(td,'unpageable.json');fs.writeFileSync(snapshot,JSON.stringify(first));let calls=0;
 const resumed=await discover(profile,{queries:['alpha'],resume:snapshot},async()=>{calls++;throw Error('must not replay');});
 assert.equal(calls,0);assert.equal(resumed.status,'PARTIAL');assert.equal(resumed.queries.length,first.queries.length);assert.ok(resumed.routes[1].resume_skipped_at);
});
await check('Legacy unknown search skips replay while a valid list cursor still advances',async()=>{
 const first=await discover(profile,{queries:['alpha']},async(op)=>op==='get_knowledge_list'?{knowledge_list:[raw],next_cursor:'REAL_NEXT',is_end:false}:{info_list:[raw]});
 delete first.routes[1].pagination_issue;delete first.routes[1].resume_supported;
 const snapshot=path.join(td,'legacy-unknown.json');fs.writeFileSync(snapshot,JSON.stringify(first));let calls=0;
 const resumed=await discover(profile,{queries:['alpha'],resume:snapshot},async(op,b)=>{calls++;assert.equal(op,'get_knowledge_list');assert.equal(b.cursor,'REAL_NEXT');return{knowledge_list:[],is_end:true};});
 assert.equal(calls,1);assert.equal(resumed.routes[0].done,true);assert.equal(resumed.status,'PARTIAL');
});
await check('A new cycle retries previously blocked search instead of caching the block forever',async()=>{
 const first=await discover(profile,{queries:['alpha']},async(op)=>op==='get_knowledge_list'?{knowledge_list:[],is_end:true}:{info_list:[raw]});
 const snapshot=path.join(td,'previous-blocked.json');fs.writeFileSync(snapshot,JSON.stringify(first));let searchCalls=0;
 const next=await discover(profile,{queries:['alpha'],previous:snapshot},async(op)=>{if(op==='search_knowledge')searchCalls++;return{info_list:[raw],is_end:true};});
 assert.equal(searchCalls,1);assert.equal(next.status,'QUERIES_COMPLETE');
});
await check('Cursor cycles longer than one page stop before returning to an earlier page',async()=>{
 let calls=0;const next=['A','B','A'];
 const r=await discover(profile,{inventoryOnly:true,queries:[],'max-pages':9},async()=>({knowledge_list:[raw],is_end:false,next_cursor:next[calls++]}));
 assert.equal(calls,3);assert.equal(r.status,'PARTIAL');assert.equal(r.routes[0].pagination_issue,'CURSOR_CYCLE');assert.equal(r.routes[0].resume_supported,false);
});
await check('A short or empty unpageable response never proves a complete search',()=>{
 for(const n of [0,7,100])assert.equal(pagination({info_list:Array(n).fill(raw)},'',new Set()).issue,'PAGINATION_NOT_EXPOSED');
 assert.throws(()=>pagination({is_end:'true'},'',new Set()),/expected boolean/);
 assert.throws(()=>pagination({next_cursor:12},'',new Set()),/expected string/);
 assert.equal(pagination({is_end:true},'',new Set()).done,true);
});
await check('Catalog matching supplements titles and tags without using highlights as full text',()=>{
 const snapshot=path.join(td,'catalog.json');fs.writeFileSync(snapshot,JSON.stringify({knowledge_base_id:'synthetic-kb',status:'MERGED_SCOPE_UNKNOWN',items:[raw,{...raw,media_id:'extra',title:'ALPHA analysis.pdf',tags:['optics'],search_highlight:'must not count as original'},{...raw,media_id:'highlight-only',title:'unrelated.pdf',highlight_content:'alpha'}]}));
 const result=catalogSearch(profile,{snapshot,queries:['alpha','optics']});
 assert.equal(result.status,'CATALOG_MATCHES_ONLY');assert.equal(result.items.length,1);assert.equal(result.items[0].media_id,'extra');assert.equal(result.items[0].read_scope,'headline');assert.equal(result.items[0].access,'not_accessed');assert.equal(result.items[0].published_at,null);
 assert.ok(result.items[0].discovered_via.includes('catalog:alpha'));assert.ok(result.items[0].discovered_via.includes('catalog:optics'));assert.equal(result.catalog_source.status,'MERGED_SCOPE_UNKNOWN');
 assert.throws(()=>catalogSearch({...profile,knowledge_base_id:'other'},{snapshot,queries:['alpha']}),/another knowledge base/);
 assert.throws(()=>catalogSearch(profile,{snapshot,queries:[]}),/at least one/);
});
await check('Catalog CLI works without loading an API helper or credentials and preserves existing output',()=>{
 const snapshot=path.join(td,'catalog-cli.json'),personal=path.join(td,'catalog-profile.json'),out=path.join(td,'catalog-cli-result');
 fs.writeFileSync(snapshot,JSON.stringify({knowledge_base_id:'synthetic-kb',items:[raw]}));fs.writeFileSync(personal,JSON.stringify({...profile,access_mode:'read_only'}));
 const args=[path.join(__dirname,'ima_source.cjs'),'catalog-search','--profile',personal,'--snapshot',snapshot,'--query','synthetic','--ima-skill',path.join(td,'missing-helper'),'--out',out];
 const result=spawnSync(process.execPath,args,{encoding:'utf8'});assert.equal(result.status,0,result.stderr);assert.equal(JSON.parse(result.stdout).network_called,false);
 const saved=fs.readFileSync(path.join(out,'ima-snapshot.json'));assert.notEqual(spawnSync(process.execPath,args).status,0);assert.deepEqual(fs.readFileSync(path.join(out,'ima-snapshot.json')),saved);
});
await check('Profile precedence is explicit, environment, personal, then unconfigured template',()=>{
 const home=path.join(td,'home'),env={CODEX_HOME:path.join(td,'codex')};
 assert.equal(profilePath({profile:'explicit.json'},{...env,FINANCIAL_RESEARCH_IMA_PROFILE:'env.json'},home),path.resolve('explicit.json'));
 assert.equal(profilePath({}, {...env,FINANCIAL_RESEARCH_IMA_PROFILE:'env.json'},home),path.resolve('env.json'));
 assert.equal(profilePath({},env,home),path.resolve(__dirname,'../assets/ima-source-profile.json'));
 const local=path.join(env.CODEX_HOME,'config/financial-research-report/ima-source-profile.json');fs.mkdirSync(path.dirname(local),{recursive:true});fs.writeFileSync(local,'{}');assert.equal(profilePath({},env,home),local);
});
await check('Unconfigured or credential-bearing research profiles fail before API work',()=>{
 const p={...profile,access_mode:'read_only'};assert.equal(validateProfile(p),p);
 assert.throws(()=>validateProfile({...p,knowledge_base_id:null}),/not configured/);
 assert.throws(()=>validateProfile({...p,api_key:'SYNTHETIC'}),/credentials/);
 assert.throws(()=>validateProfile({...p,default_page_size:51}),/default_page_size/);
});
await check('Setup creates a personal profile and refuses to overwrite it',()=>{
 const out=path.join(td,'new-profile.json'),script=path.join(__dirname,'setup_ima.cjs');
 const params=[script,'init','--name','Synthetic library','--kb-id','synthetic-library','--out',out];
 const r=spawnSync(process.execPath,params,{encoding:'utf8'});assert.equal(r.status,0,r.stderr);
 assert.equal(JSON.parse(fs.readFileSync(out,'utf8')).knowledge_base_id,'synthetic-library');
 const before=fs.readFileSync(out);assert.notEqual(spawnSync(process.execPath,params).status,0);assert.deepEqual(fs.readFileSync(out),before);
});
await check('Library discovery follows real cursors without persisting cover URLs or arbitrary fields',()=>{
 const helper=path.join(td,'mock-ima');fs.mkdirSync(helper);
 fs.writeFileSync(path.join(helper,'ima_api.cjs'),`exports.imaApi=async(op,b)=>{if(op!=='openapi/wiki/v1/search_knowledge_base')throw Error('wrong endpoint');if(b.query!=='synthetic')throw Error('wrong query');return JSON.stringify({code:0,data:{info_list:[{id:'synthetic-kb',name:'Synthetic',cover_url:'DO_NOT_PERSIST'}],is_end:b.cursor==='NEXT',next_cursor:'NEXT'}});};`);
 const out=path.join(td,'libraries.json');const r=spawnSync(process.execPath,[path.join(__dirname,'setup_ima.cjs'),'libraries','--query','synthetic','--ima-skill',helper,'--out',out],{encoding:'utf8'});assert.equal(r.status,0,r.stderr);
 const text=fs.readFileSync(out,'utf8'),data=JSON.parse(text);assert.equal(data.status,'QUERIES_COMPLETE');assert.equal(data.queries.length,2);assert.equal(data.items.length,1);assert.ok(!text.includes('DO_NOT_PERSIST'));
});
await check('Fetch retains bytes/hash but does not mark original read or expose signed URL',async()=>{
 const snap=path.join(td,'snapshot.json');fs.writeFileSync(snap,JSON.stringify({knowledge_base_id:'synthetic-kb',items:[raw]}));
 const r=await fetchOriginals(profile,{snapshot:snap,ids:[raw.media_id]},async()=>({media_type:1,url_info:{url:'https://x.myqcloud.com/a?sign=SYNTHETIC_SECRET',headers:{'X-IMA-Sign':'SYNTHETIC_SECRET'}}}),td,async()=>({ok:true,headers:new Map(),body:(async function*(){yield Buffer.from('%PDF-synthetic');})()}));
 assert.equal(r.status,'COMPLETE');assert.equal(r.files[0].status,'DOWNLOADED_NOT_READ');assert.equal(r.files[0].read_scope,'not_read');assert.ok(fs.readFileSync(r.files[0].path).equals(Buffer.from('%PDF-synthetic')));assert.ok(!JSON.stringify(r).includes('SYNTHETIC_SECRET'));
});
await check('Resume continues remaining page and rejects a different plan',async()=>{
 const first=await discover(profile,{queries:['alpha']},async()=>({info_list:[raw],is_end:false,next_cursor:'N'}));const resume=path.join(td,'resume.json');fs.writeFileSync(resume,JSON.stringify(first));
 const next=await discover(profile,{queries:['alpha'],resume},async(op,body)=>{assert.equal(body.cursor,'N');return{info_list:[],is_end:true};});assert.equal(next.status,'QUERIES_COMPLETE');assert.equal(next.items.length,1);
 await assert.rejects(()=>discover(profile,{queries:['different'],resume},async()=>({})),/same folder and queries/);
});
}finally{assert.equal(path.dirname(path.resolve(td)),path.resolve(os.tmpdir()));fs.rmSync(td,{recursive:true,force:true});}
console.log(JSON.stringify({ok:true,checks,scope:'OFFLINE_STRUCTURAL_ONLY'}));
})().catch(e=>{console.error(e);process.exitCode=1;});
