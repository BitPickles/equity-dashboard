
const themeButton=document.querySelector('#theme-toggle');
themeButton.addEventListener('click',()=>{const t=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=t;try{localStorage.setItem('theme',t)}catch(e){}});
const toc=document.querySelector('.toc');if(matchMedia('(max-width:980px)').matches)toc.open=false;
const viewer=document.querySelector('#image-viewer'),large=document.querySelector('#viewer-image'),caption=document.querySelector('#viewer-caption'),original=document.querySelector('#original-image');
document.querySelectorAll('.zoom-image').forEach(a=>a.addEventListener('click',e=>{if(!viewer.showModal)return;e.preventDefault();const img=a.querySelector('img');large.src=a.href;large.alt=img.alt;caption.textContent=img.alt;original.href=a.href;viewer.showModal()}));
document.querySelector('#close-viewer').addEventListener('click',()=>viewer.close());
viewer.addEventListener('click',e=>{if(e.target===viewer){const r=viewer.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)viewer.close()}});
const links=[...document.querySelectorAll('.toc nav a')];
if('IntersectionObserver' in window){const observer=new IntersectionObserver(entries=>{entries.forEach(entry=>{if(entry.isIntersecting)links.forEach(a=>a.classList.toggle('current',a.hash==='#'+entry.target.id))})},{rootMargin:'-15% 0px -65% 0px'});document.querySelectorAll('h2').forEach(h=>observer.observe(h))}
