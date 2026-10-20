/* Local configuration and read-only library discovery; never accepts credentials as CLI options. */
const fs=require('fs'),path=require('path'),os=require('os');
const {configHome,profilePath,validateProfile}=require('./ima_source.cjs');
const ROOT=path.resolve(__dirname,'..');
function parse(raw){const out={};for(let i=0;i<raw.length;i++){const k=raw[i],v=raw[++i];if(!['--name','--kb-id','--out','--profile','--ima-skill','--query','--max-pages'].includes(k)||v===undefined||v.startsWith('--'))throw Error('Expected documented --option value');out[k.slice(2)]=v;}return out;}
function read(p){return JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));}
function writeNew(p,data){fs.mkdirSync(path.dirname(p),{recursive:true});fs.writeFileSync(p,JSON.stringify(data,null,2)+'\n',{flag:'wx'});}
async function main(){
 const [command,...raw]=process.argv.slice(2),opt=parse(raw);
 const helperDir=opt['ima-skill']||process.env.IMA_SKILL_DIR||path.join(configHome(),'skills','ima-skill');
 if(command==='init'){
  if(!opt.name||!opt['kb-id'])throw Error('init needs --name and --kb-id obtained from your own authorized IMA account');
  const p=read(path.join(ROOT,'assets/ima-source-profile.json'));p.knowledge_base_name=opt.name;p.knowledge_base_id=opt['kb-id'];p.notes='Personal read-only research profile. Credentials are managed separately by ima-skill.';
  validateProfile(p);const target=path.resolve(opt.out||path.join(configHome(),'config','financial-research-report','ima-source-profile.json'));writeNew(target,p);
  console.log(JSON.stringify({ok:true,profile_path:target,note:'Profile created; IMA access permission has not been verified.'}));return;
 }
 if(command==='check'){
  let issue=null;const p=profilePath(opt);try{validateProfile(read(p));}catch(e){issue=e.message;}
  const credentialsPresent=Boolean((process.env.IMA_OPENAPI_CLIENTID&&process.env.IMA_OPENAPI_APIKEY)||(fs.existsSync(path.join(os.homedir(),'.config','ima','client_id'))&&fs.existsSync(path.join(os.homedir(),'.config','ima','api_key'))));
  const result={node_version:process.version,node_supported:Number(process.versions.node.split('.')[0])>=18,profile_valid:issue===null,profile_issue:issue,ima_helper_present:fs.existsSync(path.join(helperDir,'ima_api.cjs')),credential_presence_only:credentialsPresent,network_called:false,permission_verified:false};
  result.ok=result.node_supported&&result.profile_valid&&result.ima_helper_present&&credentialsPresent;
  console.log(JSON.stringify(result));if(!result.ok)process.exitCode=1;return;
 }
 if(command==='libraries'){
  if(!opt.out)throw Error('libraries needs --out <new-json-file>');const target=path.resolve(opt.out);if(fs.existsSync(target))throw Error('Output exists; choose a new file');
  const budget=Number(opt['max-pages']||3);if(!Number.isInteger(budget)||budget<1||budget>100)throw Error('max-pages must be 1..100');
  const {imaApi}=require(path.join(helperDir,'ima_api.cjs'));const result={status:'PARTIAL',scope:'Recorded name-search pages only; no original-file permission implied',items:[],queries:[],cursor:'',failure:null};const seen=new Set();
  try{for(let n=0;n<budget;n++){
   const raw=await imaApi('openapi/wiki/v1/search_knowledge_base',{query:opt.query||'',cursor:result.cursor,limit:20},{baseUrl:'https://ima.qq.com'});const r=JSON.parse(raw);
   if(r.code!==0){const e=Error(r.msg||'IMA error');e.code=r.code;throw e;}const data=r.data||{},items=data.info_list||[];if(!Array.isArray(items))throw Error('Malformed library response');
   for(const item of items){if(typeof item.id!=='string'||!item.id)throw Error('Library result missing id');if(!seen.has(item.id)){seen.add(item.id);result.items.push({id:item.id,name:item.name||''});}}
   result.queries.push({attempted_at:new Date().toISOString(),returned:items.length,response_fields:Object.keys(data)});
   if(data.is_end===true){result.status='QUERIES_COMPLETE';result.cursor='';break;}
   if(!data.next_cursor||data.next_cursor===result.cursor){result.stop_reason='Pagination unknown: missing or repeated cursor';break;}result.cursor=data.next_cursor;
  }}catch(e){result.status='ACCESS_FAILED';result.failure={code:e.code??null,msg:e.msg||e.message};}
  writeNew(target,result);console.log(JSON.stringify({status:result.status,count:result.items.length,output:target,failure:result.failure}));if(result.status==='ACCESS_FAILED')process.exitCode=1;return;
 }
 throw Error('Use init, check or libraries; see references/team-setup.md');
}
if(require.main===module)main().catch(e=>{console.error(JSON.stringify({msg:e.msg||e.message,code:e.code??null}));process.exitCode=1;});
