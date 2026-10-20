const assert=require('assert/strict'),fs=require('fs'),path=require('path'),os=require('os');
const {catalog}=require('./ima_catalog.cjs');
const profile={knowledge_base_id:'synthetic-library',knowledge_base_name:'Synthetic',default_page_size:2,default_max_pages_per_route:1};
const root=fs.mkdtempSync(path.join(os.tmpdir(),'research-catalog-test-'));
const write=(p,d)=>fs.writeFileSync(p,JSON.stringify(d));
(async()=>{
 const calls=[];const api=async(op,b)=>{assert.equal(op,'get_knowledge_list');calls.push({...b});if(b.folder_id==='folder-A')return{knowledge_list:[{media_id:'doc-B',title:'B.pdf',media_type:1},{media_id:'folder-A',title:'Cycle',media_type:99}],is_end:true,next_cursor:''};if(!b.cursor)return{knowledge_list:[{media_id:'folder-A',title:'A',media_type:99},{media_id:'doc-A',title:'A.pdf',media_type:1}],is_end:false,next_cursor:'real-next'};assert.equal(b.cursor,'real-next');return{knowledge_list:[{media_id:'doc-C',title:'C.pdf',media_type:1}],is_end:true,next_cursor:''};};
 const a=await catalog(profile,{out:path.join(root,'a'),'max-pages':1,'max-folders':10},api);assert.equal(a.status,'PARTIAL');assert.equal(calls.length,1);assert.equal(a.pending_folders[0].key,'root');
 const b=await catalog(profile,{out:path.join(root,'b'),resume:path.join(root,'a/ima-snapshot.json'),'max-pages':1,'max-folders':10},api);assert.equal(b.status,'VISIBLE_SCOPE_ENUMERATED');assert.equal(calls.length,3);assert.equal(b.items.length,4);assert.equal(b.folders.length,2);assert.equal(calls[1].cursor,'real-next');
 const unknown=await catalog(profile,{out:path.join(root,'unknown')},async()=>({info_list:[]}));assert.equal(unknown.status,'PARTIAL');assert.equal(unknown.blocked_folders.length,1);
 let unknownRetries=0;const stopped=await catalog(profile,{out:path.join(root,'unknown-resume'),resume:path.join(root,'unknown/ima-snapshot.json')},async()=>{unknownRetries++;});assert.equal(unknownRetries,0);assert.equal(stopped.status,'PARTIAL');
 const failed=await catalog(profile,{out:path.join(root,'fail')},async()=>{throw Error('synthetic access error');});assert.equal(failed.status,'ACCESS_FAILED');assert.equal(failed.pending_folders[0].key,'root');
 const recovered=await catalog(profile,{out:path.join(root,'recovered'),resume:path.join(root,'fail/ima-snapshot.json')},async()=>({knowledge_list:[],is_end:true,next_cursor:''}));assert.equal(recovered.status,'VISIBLE_SCOPE_ENUMERATED');
 const wrong=path.join(root,'wrong.json');write(wrong,{...a,knowledge_base_id:'another-library'});await assert.rejects(catalog(profile,{out:path.join(root,'wrong'),resume:wrong},api),/another library/);
 await assert.rejects(catalog(profile,{out:path.join(root,'a')},api),/new or empty/);
 console.log(JSON.stringify({ok:true,checks:['real-cursor resume','batch budget retained','recursive folders and cycle dedup','unknown remains blocked without replay','failed folder preserved for explicit retry','library identity','new-output guard']}));
})().catch(e=>{console.error(e);process.exitCode=1;});
