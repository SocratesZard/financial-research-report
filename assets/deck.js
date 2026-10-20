/* === FIXED STAGE, NAVIGATION, LOCAL EDITING === */
class SlidePresentation {
  constructor(){
    this.slides=[...document.querySelectorAll('.slide')];this.index=0;this.editing=false;
    this.stage=document.getElementById('deckStage');
    const scale=()=>{const {width,height}=this.stage.parentElement.getBoundingClientRect();const k=Math.min(width/1920,height/1080);this.stage.style.transform=`translate(${(width-1920*k)/2}px,${(height-1080*k)/2}px) scale(${k})`;};
    addEventListener('resize',scale);scale();
    this.storageKey='financial-report:'+document.title+':'+location.pathname;
    try{const saved=JSON.parse(localStorage.getItem(this.storageKey)||'null');if(saved)this.slides.forEach((s,i)=>{if(saved[i])s.innerHTML=saved[i];});}catch{}
    this.showSlide(Number(location.hash.slice(1)||1)-1);
    addEventListener('keydown',e=>{
      if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'){e.preventDefault();this.save();return;}
      if(e.target.isContentEditable)return;
      if(e.target.closest('button,a,summary')&&[' ','Enter'].includes(e.key))return;
      if(e.key.toLowerCase()==='e'){this.toggleEdit();return;}
      if(['ArrowRight','ArrowDown',' ','PageDown'].includes(e.key)){e.preventDefault();this.showSlide(this.index+1);}
      if(['ArrowLeft','ArrowUp','PageUp'].includes(e.key)){e.preventDefault();this.showSlide(this.index-1);}
      if(e.key==='Home')this.showSlide(0);if(e.key==='End')this.showSlide(this.slides.length-1);
    });
    let touchX=0;addEventListener('touchstart',e=>{touchX=e.changedTouches[0].clientX;},{passive:true});
    addEventListener('touchend',e=>{if(this.editing)return;const dx=e.changedTouches[0].clientX-touchX;if(Math.abs(dx)>45)this.showSlide(this.index+(dx<0?1:-1));},{passive:true});
    let lastWheel=0;addEventListener('wheel',e=>{if(this.editing)return;if(Date.now()-lastWheel>500&&Math.abs(e.deltaY)>15){lastWheel=Date.now();this.showSlide(this.index+(e.deltaY>0?1:-1));}},{passive:true});
    document.getElementById('prev').onclick=()=>this.showSlide(this.index-1);
    document.getElementById('next').onclick=()=>this.showSlide(this.index+1);
    document.getElementById('edit').onclick=()=>this.toggleEdit();document.getElementById('save').onclick=()=>this.save();
    document.getElementById('exportPdf').onclick=()=>this.exportPDF();
    document.addEventListener('input',()=>{try{localStorage.setItem(this.storageKey,JSON.stringify(this.slides.map(s=>s.innerHTML)));}catch{}});
  }
  showSlide(n){this.index=Math.max(0,Math.min(this.slides.length-1,Number.isFinite(n)?n:0));this.slides.forEach((s,i)=>{s.classList.toggle('active',i===this.index);s.classList.toggle('visible',i===this.index);});document.getElementById('counter').textContent=`${this.index+1} / ${this.slides.length}`;history.replaceState(null,'',`#${this.index+1}`);}
  toggleEdit(){this.editing=!this.editing;document.body.classList.toggle('editing',this.editing);document.querySelectorAll('h1,h2,h3,p,td,th,.toc-row strong,.toc-row span').forEach(e=>e.contentEditable=String(this.editing));document.getElementById('edit').textContent=this.editing?'完成编辑':'编辑';}
  exportPDF(){document.activeElement?.blur();window.print();}
  save(){const clone=document.documentElement.cloneNode(true);clone.querySelectorAll('[contenteditable]').forEach(e=>e.removeAttribute('contenteditable'));clone.querySelector('body').classList.remove('editing');clone.querySelector('#edit').textContent='编辑';const blob=new Blob(['<!doctype html>\n'+clone.outerHTML],{type:'text/html;charset=utf-8'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='report-edited.html';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
}
window.deck=new SlidePresentation();
