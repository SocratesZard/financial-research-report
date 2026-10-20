/* Render every slide at two viewports; DOM checks plus screenshots, optional vector PDF. */
const fs=require('fs');const path=require('path');const {pathToFileURL}=require('url');
const args=process.argv.slice(2);const input=args[0],out=args[1];
if(!input||!out)throw Error('Usage: node qa_deck.cjs report.html qa-dir [--modules node_modules] [--pdf output.pdf]');
const option=k=>{const i=args.indexOf(k);return i<0?null:args[i+1];};
const modules=option('--modules');const {chromium}=modules?require(path.join(path.resolve(modules),'playwright')):require('playwright');
(async()=>{
 fs.mkdirSync(out,{recursive:true});
 const launch={headless:true};const executable=option('--browser');
 if(executable)launch.executablePath=path.resolve(executable);
 else if(fs.existsSync(chromium.executablePath()))launch.executablePath=chromium.executablePath();
 const browser=await chromium.launch(launch);
 const result={input:path.resolve(input),checked_at:new Date().toISOString(),viewports:[],pdf:null};
 try{
  for(const [width,height] of [[1280,720],[390,844]]){
   const page=await browser.newPage({viewport:{width,height}});const errors=[];
   page.on('pageerror',e=>errors.push(e.message));
   await page.goto(pathToFileURL(path.resolve(input)).href);await page.evaluate(()=>document.fonts.ready);
   const count=await page.locator('.slide').count();const slides=[];
   for(let i=0;i<count;i++){
    await page.evaluate(n=>window.deck.showSlide(n),i);await page.waitForTimeout(220);
    const metrics=await page.locator('.slide.active').evaluate(s=>{
     const root=s.getBoundingClientRect();const problems=[];const eps=2;
     for(const el of s.querySelectorAll('header,h1,h2,h3,p,table,svg,footer,.footer-sources,.toc,.cover-note,article,figure,figcaption,.kpi-strip')){
      const b=el.getBoundingClientRect();
      if(b.left<root.left-eps||b.top<root.top-eps||b.right>root.right+eps||b.bottom>root.bottom+eps)problems.push({kind:'outside-slide',tag:el.tagName,text:el.textContent.slice(0,65)});
      if(el.scrollHeight>el.clientHeight+3&&el.clientHeight>0)problems.push({kind:'container-overflow',tag:el.tagName,text:el.textContent.slice(0,65)});
     }
     const grid=s.querySelector('.body-grid');if(grid){const limit=grid.getBoundingClientRect().bottom;for(const el of grid.querySelectorAll('table,p,svg,figure,figcaption,.kpi-strip'))if(el.getBoundingClientRect().bottom>limit+eps)problems.push({kind:'body-overflow',text:el.textContent.slice(0,65)});}
     const chartMetrics=[];
     for(const svg of s.querySelectorAll('svg')){
      const vb=svg.viewBox.baseVal;const labels=[...svg.querySelectorAll('text')];
      for(const t of labels){const b=t.getBBox();if(b.x<vb.x-1||b.y<vb.y-1||b.x+b.width>vb.x+vb.width+1||b.y+b.height>vb.y+vb.height+1)problems.push({kind:'chart-label-outside-viewbox',chart:svg.dataset.chartId,text:t.textContent.slice(0,65)});}
      for(let a=0;a<labels.length;a++)for(let b=a+1;b<labels.length;b++){
       const x=labels[a].getBBox(),y=labels[b].getBBox();
       if(x.x+x.width>y.x+2&&y.x+y.width>x.x+2&&x.y+x.height>y.y+2&&y.y+y.height>x.y+2)problems.push({kind:'chart-label-overlap',chart:svg.dataset.chartId,text:labels[a].textContent+' / '+labels[b].textContent});
      }
      chartMetrics.push({id:svg.dataset.chartId,type:svg.dataset.chartType,labelCount:labels.length,minAuthoredFont:Math.min(...labels.map(t=>parseFloat(getComputedStyle(t).fontSize)))});
     }
     const heading=s.querySelector('header h2'),header=s.querySelector('header');
     if(heading&&header&&heading.getBoundingClientRect().bottom>header.getBoundingClientRect().bottom+eps)problems.push({kind:'title-header-overflow'});
     const strip=s.querySelector('.takeaway'),foot=s.querySelector('footer');if(strip&&foot&&strip.getBoundingClientRect().bottom>foot.getBoundingClientRect().top+eps)problems.push({kind:'takeaway-footer-overlap'});
     const toolbar=document.querySelector('.deck-controls');
     if(toolbar&&getComputedStyle(toolbar).display!=='none'){
      const t=toolbar.getBoundingClientRect();
      if(t.left<0||t.right>innerWidth+eps||t.top<0||t.bottom>innerHeight+eps)problems.push({kind:'controls-outside-viewport'});
      if(t.left<root.right&&t.right>root.left&&t.top<root.bottom&&t.bottom>root.top)problems.push({kind:'controls-cover-stage'});
     }
     return{ratio:root.width/root.height,charts:chartMetrics,problems};
    });
    await page.screenshot({path:path.join(out,`${width}-slide-${String(i+1).padStart(2,'0')}.png`)});
    slides.push({page:i+1,...metrics});
   }
   result.viewports.push({width,height,slides,script_errors:errors});await page.close();
  }
  const pdf=option('--pdf');if(pdf){
   if(fs.existsSync(pdf))throw Error('Refusing to overwrite existing PDF');
   const page=await browser.newPage({viewport:{width:1920,height:1080}});await page.goto(pathToFileURL(path.resolve(input)).href);await page.evaluate(()=>document.fonts.ready);await page.emulateMedia({media:'print',reducedMotion:'reduce'});await page.pdf({path:pdf,printBackground:true,preferCSSPageSize:true});result.pdf=path.resolve(pdf);await page.close();
  }
  result.ok=result.viewports.every(v=>!v.script_errors.length&&v.slides.every(s=>!s.problems.length&&Math.abs(s.ratio-16/9)<0.001));
  fs.writeFileSync(path.join(out,'visual-qa.json'),JSON.stringify(result,null,2));console.log(JSON.stringify({ok:result.ok,report:path.resolve(out),pages:result.viewports[0].slides.length}));if(!result.ok)process.exitCode=1;
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
