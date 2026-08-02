"""
ai/interactions/library.py — Phase 6: JavaScript Interaction Library

Pre-built, safe, vanilla JS modules for common website behaviors.

Instead of AI generating JavaScript randomly, we provide
deterministic, tested, minified interaction scripts that get
injected per-component.

Each script is:
  - Self-contained (IIFE, no globals leaked)
  - Zero external dependencies
  - Safe (no eval, no external scripts, no DOM manipulation of parent)
  - Minified for production

Available scripts:
  navbar    — Sticky header, blur on scroll, mobile menu toggle
  faq       — Accordion open/close with smooth height animation
  pricing   — Monthly/Yearly toggle with price swap
  gallery   — Simple lightbox overlay
  counter   — Animated number counting on scroll
  carousel  — Testimonial/content carousel with dots
  scroll    — Smooth scroll for anchor links + scroll-to-top
  reveal    — Fade-in-up on scroll (IntersectionObserver)
  newsletter — Form validation + success message
  typing    — Typewriter effect for hero headings

Usage:
    from ai.interactions.library import InteractionLibrary
    script = InteractionLibrary.get("faq")
    all_scripts = InteractionLibrary.get_bundle(["faq", "navbar", "scroll"])
"""
from __future__ import annotations


class InteractionLibrary:
    """Pre-built vanilla JS interaction modules."""

    _SCRIPTS: dict[str, str] = {
        # ── Navbar ────────────────────────────────────────────────
        "navbar": """(function(){
const nav=document.querySelector('nav');
if(!nav)return;
const cls=nav.classList;
let lastY=0;
window.addEventListener('scroll',()=>{
const y=window.scrollY;
if(y>60){cls.add('backdrop-blur-xl','bg-opacity-90','shadow-lg');cls.remove('bg-transparent')}
else{cls.remove('backdrop-blur-xl','bg-opacity-90','shadow-lg');cls.add('bg-transparent')}
lastY=y},{passive:true});
const btn=document.querySelector('[data-mobile-menu]');
const menu=document.querySelector('[data-mobile-nav]');
if(btn&&menu){btn.addEventListener('click',()=>{menu.classList.toggle('hidden');
btn.setAttribute('aria-expanded',menu.classList.contains('hidden')?'false':'true')})}
const links=document.querySelectorAll('nav a[href^="#"]');
links.forEach(a=>{a.addEventListener('click',e=>{const t=document.querySelector(a.getAttribute('href'));
if(t){e.preventDefault();t.scrollIntoView({behavior:'smooth',block:'start'})}})});
const sections=document.querySelectorAll('section[id]');
if(sections.length){const obs=new IntersectionObserver(entries=>{entries.forEach(e=>{
if(e.isIntersecting){links.forEach(l=>{l.classList.remove('text-white','font-bold');
if(l.getAttribute('href')==='#'+e.target.id){l.classList.add('text-white','font-bold')}})}})},
{threshold:0.3,rootMargin:'-80px 0px 0px 0px'});sections.forEach(s=>obs.observe(s))}})();""",

        # ── FAQ Accordion ─────────────────────────────────────────
        "faq": """(function(){
document.querySelectorAll('[data-faq]').forEach(item=>{
const btn=item.querySelector('[data-faq-q]');
const ans=item.querySelector('[data-faq-a]');
const icon=item.querySelector('[data-faq-icon]');
if(!btn||!ans)return;
ans.style.maxHeight='0';ans.style.overflow='hidden';ans.style.transition='max-height 0.3s ease';
btn.addEventListener('click',()=>{const open=ans.style.maxHeight!=='0px'&&ans.style.maxHeight!=='0';
if(open){ans.style.maxHeight='0';if(icon)icon.style.transform='rotate(0deg)'}
else{ans.style.maxHeight=ans.scrollHeight+'px';if(icon)icon.style.transform='rotate(180deg)'}
btn.setAttribute('aria-expanded',!open)})})})();""",

        # ── Pricing Toggle ────────────────────────────────────────
        "pricing": """(function(){
const toggle=document.querySelector('[data-pricing-toggle]');
if(!toggle)return;
const monthly=document.querySelectorAll('[data-price-monthly]');
const yearly=document.querySelectorAll('[data-price-yearly]');
const labels=document.querySelectorAll('[data-pricing-label]');
let isYearly=false;
toggle.addEventListener('click',()=>{isYearly=!isYearly;
toggle.setAttribute('aria-checked',isYearly);
const dot=toggle.querySelector('[data-toggle-dot]');
if(dot)dot.style.transform=isYearly?'translateX(24px)':'translateX(0)';
monthly.forEach(el=>el.style.display=isYearly?'none':'');
yearly.forEach(el=>el.style.display=isYearly?'':'none');
labels.forEach(l=>{if(l.dataset.pricingLabel==='monthly')l.style.opacity=isYearly?'0.5':'1';
if(l.dataset.pricingLabel==='yearly')l.style.opacity=isYearly?'1':'0.5'})})})();""",

        # ── Gallery Lightbox ──────────────────────────────────────
        "gallery": """(function(){
const imgs=document.querySelectorAll('[data-gallery-img]');
if(!imgs.length)return;
const overlay=document.createElement('div');
overlay.style.cssText='position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,0.9);display:none;align-items:center;justify-content:center;cursor:pointer;backdrop-filter:blur(8px)';
const display=document.createElement('img');
display.style.cssText='max-width:90vw;max-height:90vh;object-fit:contain;border-radius:8px';
overlay.appendChild(display);document.body.appendChild(overlay);
imgs.forEach(img=>{img.style.cursor='pointer';
img.addEventListener('click',()=>{display.src=img.src;display.alt=img.alt;overlay.style.display='flex'})});
overlay.addEventListener('click',()=>{overlay.style.display='none'});
document.addEventListener('keydown',e=>{if(e.key==='Escape')overlay.style.display='none'})})();""",

        # ── Counter Animation ─────────────────────────────────────
        "counter": """(function(){
const counters=document.querySelectorAll('[data-counter]');
if(!counters.length)return;
const animate=(el)=>{const target=parseInt(el.dataset.counter)||0;
const dur=1500;const start=performance.now();const fmt=el.dataset.counterPrefix||'';
const suffix=el.dataset.counterSuffix||'';
const step=(now)=>{const p=Math.min((now-start)/dur,1);
const ease=1-Math.pow(1-p,3);
el.textContent=fmt+Math.floor(ease*target)+suffix;
if(p<1)requestAnimationFrame(step)};requestAnimationFrame(step)};
const obs=new IntersectionObserver(entries=>{entries.forEach(e=>{
if(e.isIntersecting){animate(e.target);obs.unobserve(e.target)}})},{threshold:0.3});
counters.forEach(c=>obs.observe(c))})();""",

        # ── Testimonial Carousel ──────────────────────────────────
        "carousel": """(function(){
const track=document.querySelector('[data-carousel]');
if(!track)return;
const slides=track.querySelectorAll('[data-slide]');
const dots=document.querySelectorAll('[data-carousel-dot]');
let current=0;const total=slides.length;if(!total)return;
const show=(i)=>{slides.forEach((s,idx)=>{s.style.display=idx===i?'':'none';
s.style.opacity=idx===i?'1':'0';s.style.transition='opacity 0.3s ease'});
dots.forEach((d,idx)=>{d.style.opacity=idx===i?'1':'0.4'});current=i};
show(0);dots.forEach((d,i)=>d.addEventListener('click',()=>show(i)));
const prev=document.querySelector('[data-carousel-prev]');
const next=document.querySelector('[data-carousel-next]');
if(prev)prev.addEventListener('click',()=>show((current-1+total)%total));
if(next)next.addEventListener('click',()=>show((current+1)%total));
setInterval(()=>show((current+1)%total),5000)})();""",

        # ── Smooth Scroll + Scroll-to-Top ─────────────────────────
        "scroll": """(function(){
document.querySelectorAll('a[href^="#"]').forEach(a=>{a.addEventListener('click',e=>{
const t=document.querySelector(a.getAttribute('href'));
if(t){e.preventDefault();t.scrollIntoView({behavior:'smooth',block:'start'})}})});
const btn=document.createElement('button');
btn.innerHTML='&#8593;';btn.setAttribute('aria-label','Scroll to top');
btn.style.cssText='position:fixed;bottom:24px;right:24px;z-index:9998;width:44px;height:44px;border-radius:50%;background:rgba(99,102,241,0.9);color:white;border:none;font-size:18px;cursor:pointer;opacity:0;transition:opacity 0.3s;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px)';
document.body.appendChild(btn);
btn.addEventListener('click',()=>window.scrollTo({top:0,behavior:'smooth'}));
window.addEventListener('scroll',()=>{btn.style.opacity=window.scrollY>400?'1':'0';
btn.style.pointerEvents=window.scrollY>400?'auto':'none'},{passive:true})})();""",

        # ── Reveal on Scroll ──────────────────────────────────────
        "reveal": """(function(){
const els=document.querySelectorAll('[data-reveal]');
if(!els.length)return;
els.forEach(el=>{el.style.opacity='0';el.style.transform='translateY(20px)';
el.style.transition='opacity 0.6s ease, transform 0.6s ease'});
const obs=new IntersectionObserver(entries=>{entries.forEach(e=>{
if(e.isIntersecting){const d=parseInt(e.target.dataset.reveal)||0;
setTimeout(()=>{e.target.style.opacity='1';e.target.style.transform='translateY(0)'},d);
obs.unobserve(e.target)}})},{threshold:0.1,rootMargin:'0px 0px -50px 0px'});
els.forEach(el=>obs.observe(el))})();""",

        # ── Newsletter Form ───────────────────────────────────────
        "newsletter": """(function(){
const forms=document.querySelectorAll('[data-newsletter]');
forms.forEach(form=>{form.addEventListener('submit',e=>{e.preventDefault();
const input=form.querySelector('input[type="email"]');
if(!input||!input.value||!input.value.includes('@')){
if(input){input.style.borderColor='#ef4444';setTimeout(()=>input.style.borderColor='',2000)}return}
const btn=form.querySelector('button[type="submit"]');
if(btn){const orig=btn.innerHTML;btn.innerHTML='✓ Subscribed!';btn.disabled=true;
btn.style.background='#10b981';
setTimeout(()=>{btn.innerHTML=orig;btn.disabled=false;btn.style.background='';input.value=''},3000)}})})})();""",

        # ── Typing Animation ──────────────────────────────────────
        "typing": """(function(){
const els=document.querySelectorAll('[data-typing]');
els.forEach(el=>{const words=(el.dataset.typing||el.textContent).split('|');
if(!words.length)return;let wi=0,ci=0,deleting=false;el.textContent='';
el.style.borderRight='2px solid currentColor';
const type=()=>{const word=words[wi];
if(!deleting){el.textContent=word.substring(0,ci+1);ci++;
if(ci===word.length){deleting=true;setTimeout(type,2000);return}}
else{el.textContent=word.substring(0,ci-1);ci--;
if(ci===0){deleting=false;wi=(wi+1)%words.length}}
setTimeout(type,deleting?50:100)};setTimeout(type,500)})})();""",
    }

    @classmethod
    def get(cls, name: str) -> str | None:
        """Get a single interaction script by name."""
        return cls._SCRIPTS.get(name)

    @classmethod
    def get_bundle(cls, names: list[str]) -> str:
        """Bundle multiple scripts into a single string."""
        scripts = []
        for name in names:
            script = cls._SCRIPTS.get(name)
            if script:
                scripts.append(f"/* {name} */\n{script}")
        return "\n".join(scripts)

    @classmethod
    def list_available(cls) -> list[str]:
        """List all available interaction names."""
        return sorted(cls._SCRIPTS.keys())

    @classmethod
    def get_all(cls) -> str:
        """Get all scripts bundled together."""
        return cls.get_bundle(sorted(cls._SCRIPTS.keys()))
