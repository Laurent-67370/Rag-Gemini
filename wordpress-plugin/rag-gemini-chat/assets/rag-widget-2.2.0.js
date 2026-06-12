/**
 * rag-widget.js — RAG Gemini Chat v2.2.0
 * v2.2 : export PDF de la conversation complète (bouton 📄 dans les onglets)
 * v2.1 : export PDF des réponses (impression native, zéro dépendance)
 * Design inspiré de lhusser.fr/assistant-ia/
 * v2.0 : effet machine à écrire, feedback 👍👎 + copier, historique localStorage,
 *        plein écran mobile, chips scrollables, fallback stats, accessibilité
 */
(function () {
    'use strict';

    var C        = window.ragGeminiConfig || {};
    var RAG_URL  = C.rag_url         || 'https://rag.lhusser.cloud/api/public-query';
    var TITLE    = C.widget_title    || 'Assistant lhusser.fr';
    var ACCENT   = C.accent_color    || '#f97316';
    var POSITION = C.position        || 'bottom-right';
    var MOBILE   = C.show_on_mobile  !== '0';
    var SUGS = Array.isArray(C.suggestions) ? C.suggestions : [
        "🤖 Qu'est-ce que Claude Code ?",
        "⚡ Articles sur n8n",
        "🌿 Ho'oponopono expliqué",
        "🌍 C'est quoi la géobiologie ?",
        "🍎 Meilleurs articles Mac",
        "🚀 Créer un agent IA",
    ];

    if (!MOBILE && window.innerWidth < 768) return;
    var isLeft = POSITION === 'bottom-left';
    var hPos   = isLeft ? 'left:20px' : 'right:20px';

    // Fonts
    if (!document.getElementById('rw-fonts')) {
        var lk=document.createElement('link'); lk.id='rw-fonts'; lk.rel='stylesheet';
        lk.href='https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap';
        document.head.appendChild(lk);
    }

    // Markdown
    function md(t) {
        if(!t)return'';
        return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
            .replace(/\*\*(.*?)\*\*/g,'<strong style="color:#f1f5f9">$1</strong>')
            .replace(/\*(.*?)\*/g,'<em>$1</em>')
            .replace(new RegExp('`([^`]+)`','g'),'<code style="background:rgba(249,115,22,.15);color:#fb923c;padding:1px 5px;border-radius:4px;font-family:Space Mono,monospace;font-size:11px">$1</code>')
            .replace(/^\*\s(.+)$/gm,'<li style="margin:2px 0">$1</li>')
            .replace(/^-\s(.+)$/gm,'<li style="margin:2px 0">$1</li>')
            .replace(/(<li[\s\S]*?<\/li>\n?)+/g,function(m){return'<ul style="margin:6px 0;padding-left:18px;list-style:disc">'+m+'</ul>';})
            .replace(/\[(.+?)\]\((.+?)\)/g,'<a href="$2" target="_blank" rel="noopener" style="color:#f97316;text-decoration:underline">$1</a>')
            .replace(/\n\n/g,'</p><p style="margin-top:8px">').replace(/\n/g,'<br>');
    }
    // Retire la liste "Sources :" en fin de réponse (déjà affichée en cartes)
    function stripSources(t){
        if(!t)return t;
        return t.replace(/(\n\s*[-–—]{2,}\s*)?\n\s*\*{0,2}Sources?\s*:?\s*\*{0,2}\s*\n(?:\s*[*•-]\s+.*(?:\n|$))+\s*$/i,'').trim();
    }
    function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
    function now(){return new Date().toLocaleTimeString('fr',{hour:'2-digit',minute:'2-digit'});}

    // CSS
    var css = `
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap');

    #rw-fab {
        position:fixed; ${hPos}; bottom:24px;
        width:54px; height:54px; border-radius:16px;
        background:${ACCENT}; border:none; cursor:pointer; z-index:9999;
        box-shadow:0 0 24px rgba(249,115,22,.5), 0 4px 16px rgba(0,0,0,.4);
        display:flex; align-items:center; justify-content:center; font-size:24px;
        transition:all .3s cubic-bezier(.34,1.56,.64,1);
        animation:rw-glow 3s ease-in-out infinite;
        font-family:'Syne',sans-serif;
    }
    #rw-fab:hover { transform:scale(1.1) translateY(-2px); }
    @keyframes rw-glow {
        0%,100%{ box-shadow:0 0 24px rgba(249,115,22,.5),0 4px 16px rgba(0,0,0,.4); }
        50%    { box-shadow:0 0 36px rgba(249,115,22,.8),0 4px 16px rgba(0,0,0,.4); }
    }

    #rw-panel {
        position:fixed; ${hPos}; bottom:90px;
        width:min(440px, calc(100vw - 20px));
        height:min(780px, calc(100vh - 80px));
        background:#0d1424; border:1px solid #1e2d45;
        border-radius:22px; overflow:hidden; z-index:9998;
        display:flex; flex-direction:column;
        box-shadow:0 0 80px rgba(249,115,22,.06), 0 32px 80px rgba(0,0,0,.6);
        transform:scale(.9) translateY(20px); opacity:0; pointer-events:none;
        transform-origin:${isLeft?'bottom left':'bottom right'};
        transition:transform .35s cubic-bezier(.34,1.56,.64,1), opacity .25s ease;
        font-family:'Syne',sans-serif;
    }
    #rw-panel.ropen { transform:scale(1) translateY(0); opacity:1; pointer-events:all; }

    /* ── HERO ── */
    #rw-hero {
        background:linear-gradient(180deg, #111827 0%, #0d1424 100%);
        padding:20px 20px 16px; flex-shrink:0;
        border-bottom:1px solid #1e2d45;
    }
    #rw-hero-top {
        display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:14px;
    }
    #rw-close-btn {
        background:rgba(255,255,255,.06); border:1px solid #1e2d45;
        border-radius:8px; color:#64748b; cursor:pointer; padding:5px 9px;
        font-size:13px; transition:all .2s; flex-shrink:0; margin-top:2px;
    }
    #rw-close-btn:hover { background:rgba(239,68,68,.12); color:#fca5a5; border-color:rgba(239,68,68,.3); }

    #rw-hero-texts {}
    #rw-hero-badge {
        display:inline-flex; align-items:center; gap:6px;
        background:rgba(249,115,22,.12); border:1px solid rgba(249,115,22,.3);
        border-radius:20px; padding:4px 12px; margin-bottom:10px;
        font-family:'Space Mono',monospace; font-size:10px; color:${ACCENT};
        letter-spacing:.08em; font-weight:700; text-transform:uppercase;
    }
    #rw-hero-badge::before { content:'●'; font-size:8px; }
    #rw-hero-title {
        color:#f1f5f9; font-size:18px; font-weight:800; line-height:1.25;
        letter-spacing:-.01em; margin-bottom:6px;
    }
    #rw-hero-title span { color:${ACCENT}; }
    #rw-hero-desc { color:#64748b; font-size:12px; line-height:1.6; margin-bottom:12px; }

    #rw-hero-stats {
        display:flex; align-items:center; gap:14px;
        font-family:'Space Mono',monospace; font-size:11px;
    }
    .rw-stat-cnt { color:#f1f5f9; }
    .rw-stat-cnt strong { color:${ACCENT}; font-size:13px; font-weight:700; }
    .rw-stat-online { display:flex; align-items:center; gap:5px; color:#94a3b8; }
    .rw-stat-online::before { content:'●'; color:#6b7280; font-size:9px; animation:rw-blink 2s infinite; }
    .rw-stat-online.live::before { color:#22c55e; }
    @keyframes rw-blink { 0%,100%{opacity:1}50%{opacity:.3} }

    /* ── QUESTIONS POPULAIRES ── */
    #rw-pops { padding:14px 18px 0; flex-shrink:0; }
    #rw-pops-label {
        font-family:'Space Mono',monospace; font-size:9px; font-weight:700;
        color:#334155; letter-spacing:.12em; text-transform:uppercase;
        display:flex; align-items:center; gap:6px; margin-bottom:10px;
    }
    #rw-pops-label::before { content:'✦'; color:${ACCENT}; }
    #rw-pops-grid {
        display:grid; grid-template-columns:1fr 1fr; gap:7px;
    }
    .rw-pop {
        padding:9px 13px; background:#131f33; border:1px solid #1e2d45;
        border-radius:12px; color:#94a3b8; font-size:12px; font-weight:600;
        cursor:pointer; transition:all .2s; text-align:left; font-family:'Syne',sans-serif;
        white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
    }
    .rw-pop:hover { border-color:${ACCENT}; color:#f1f5f9; background:#1a2d47; transform:translateY(-1px); }

    /* ── TABS ── */
    #rw-tabs {
        display:flex; gap:0; padding:10px 18px 0;
        flex-shrink:0; border-bottom:1px solid #1e2d45;
    }
    .rw-tab {
        padding:8px 16px; border-radius:10px 10px 0 0; border:none;
        background:transparent; color:#475569; font-family:'Syne',sans-serif;
        font-size:12px; font-weight:700; cursor:pointer; transition:all .2s;
        border-bottom:2px solid transparent; margin-bottom:-1px;
    }
    .rw-tab.active { color:${ACCENT}; border-bottom-color:${ACCENT}; background:rgba(249,115,22,.06); }
    .rw-tab:hover:not(.active) { color:#94a3b8; }
    .rw-tab-clear { margin-left:auto; color:#334155; }
    .rw-tab-clear:hover { color:#f87171; }
    .rw-tab-close { display:none; color:#64748b; }
    .rw-tab-close:hover { color:#fca5a5; }

    /* ── MESSAGES ── */
    #rw-msgs {
        flex:1; overflow-y:auto; padding:14px 16px;
        display:flex; flex-direction:column; gap:14px;
        min-height:0;
    }
    #rw-msgs::-webkit-scrollbar { width:3px; }
    #rw-msgs::-webkit-scrollbar-thumb { background:#1e2d45; border-radius:2px; }
    #rw-msgs::-webkit-scrollbar-thumb:hover { background:${ACCENT}; }

    .rw-msg { display:flex; gap:10px; animation:rw-up .3s ease; }
    .rw-msg.u { flex-direction:row-reverse; }
    @keyframes rw-up { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }

    .rw-av { width:32px; height:32px; border-radius:10px; flex-shrink:0;
        display:flex; align-items:center; justify-content:center; font-size:15px; margin-top:2px; }
    .rw-msg.b .rw-av { background:#131f33; border:1px solid #1e2d45; }
    .rw-msg.u .rw-av { background:${ACCENT}; box-shadow:0 0 12px rgba(249,115,22,.3); }

    .rw-body { max-width:calc(100% - 46px); }
    .rw-bub { padding:11px 14px; border-radius:14px; font-size:13px; line-height:1.65; word-break:break-word; }
    .rw-msg.b .rw-bub { background:#131f33; border:1px solid #1e2d45; color:#cbd5e1; border-top-left-radius:4px; }
    .rw-msg.u .rw-bub { background:linear-gradient(135deg,${ACCENT},#ea580c); border:none; color:#fff; border-top-right-radius:4px; box-shadow:0 4px 14px rgba(249,115,22,.25); }
    .rw-time { font-family:'Space Mono',monospace; font-size:10px; color:#475569; margin-top:3px; padding:0 4px; }
    .rw-msg.u .rw-time { text-align:right; }

    /* Actions sous les réponses */
    .rw-acts { display:flex; gap:6px; margin-top:6px; }
    .rw-act { background:#131f33; border:1px solid #1e2d45; border-radius:8px;
        color:#64748b; cursor:pointer; font-size:12px; padding:3px 9px;
        font-family:'Syne',sans-serif; transition:all .2s; }
    .rw-act:hover { border-color:${ACCENT}; color:${ACCENT}; transform:translateY(-1px); }
    .rw-act.sel { background:rgba(249,115,22,.15); border-color:${ACCENT}; color:${ACCENT}; }

    /* Sources */
    .rw-srcs { margin-top:10px; display:flex; flex-direction:column; gap:5px; }
    .rw-srcs-lbl { font-family:'Space Mono',monospace; font-size:10px; color:#334155;
        text-transform:uppercase; letter-spacing:.1em; margin-bottom:2px; }
    .rw-src { display:flex; align-items:center; gap:8px; padding:6px 10px;
        background:#1a2940; border:1px solid #1e2d45; border-radius:8px;
        text-decoration:none; transition:all .2s; color:#94a3b8; font-size:12px; }
    .rw-src:hover { border-color:${ACCENT}; color:${ACCENT}; transform:translateX(3px); }
    .rw-src .txt { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; flex:1; }
    .rw-src .arr { margin-left:auto; flex-shrink:0; color:#334155; font-size:10px; }

    /* Typing */
    .rw-typing { display:flex; gap:5px; align-items:center; padding:3px 0; }
    .rw-td { width:6px; height:6px; border-radius:50%; background:${ACCENT};
        animation:rw-td .9s ease-in-out infinite; }
    .rw-td:nth-child(2){animation-delay:.2s} .rw-td:nth-child(3){animation-delay:.4s}
    @keyframes rw-td { 0%,100%{transform:translateY(0);opacity:.4}50%{transform:translateY(-5px);opacity:1} }

    /* Welcome inline */
    .rw-welcome { text-align:center; padding:30px 14px;
        display:flex; flex-direction:column; align-items:center; gap:10px; }
    .rw-wicon { font-size:30px; animation:rw-float 4s ease-in-out infinite; }
    @keyframes rw-float { 0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)} }
    .rw-welcome h4 { color:#f1f5f9; font-size:18px; font-weight:800; }
    .rw-welcome p  { color:#475569; font-size:12px; line-height:1.6; max-width:280px; }

    /* Article cards (mode recherche) */
    .rw-art-card {
        display:block; padding:10px 12px; margin:5px 0;
        background:#1a2940; border:1px solid #1e2d45; border-radius:10px;
        text-decoration:none; transition:all .2s;
    }
    .rw-art-card:hover { border-color:#f97316; transform:translateY(-2px); box-shadow:0 4px 16px rgba(249,115,22,.1); }
    .rw-art-title { color:#f1f5f9; font-size:13px; font-weight:700; margin-bottom:4px; line-height:1.4; }
    .rw-art-cat { color:#475569; font-family:'Space Mono',monospace; font-size:10px;
        display:flex; justify-content:space-between; align-items:center; }
    .rw-art-arr { color:#f97316; font-weight:700; }

    /* Error */
    .rw-err { background:rgba(239,68,68,.08); border:1px solid rgba(239,68,68,.2);
        border-radius:10px; padding:10px 14px; font-size:12px; color:#fca5a5; }

    /* ── INPUT ── */
    #rw-iz { padding:12px 16px 10px; background:#0a1020; border-top:1px solid #1e2d45; flex-shrink:0; }
    #rw-irow { display:flex; gap:10px; align-items:flex-end; }
    #rw-iwrap { flex:1; background:#131f33; border:1px solid #1e2d45; border-radius:16px;
        padding:11px 14px; display:flex; align-items:flex-end; gap:8px;
        transition:border-color .2s, box-shadow .2s; }
    #rw-iwrap:focus-within { border-color:${ACCENT}; box-shadow:0 0 0 3px rgba(249,115,22,.08); }
    #rw-ta { flex:1; background:transparent; border:none; outline:none;
        color:#f1f5f9; font-family:'Syne',sans-serif; font-size:13px;
        resize:none; min-height:20px; max-height:100px; line-height:1.5; }
    #rw-ta::placeholder { color:#2d3f55; }
    #rw-ta:focus { outline:none !important; box-shadow:none !important; border:none !important; }
    #rw-iwrap textarea { border:none !important; box-shadow:none !important; outline:none !important; }
    #rw-iwrap textarea:focus { border:none !important; box-shadow:none !important; outline:none !important; }
    #rw-cc { font-family:'Space Mono',monospace; font-size:10px; color:#1e2d45;
        flex-shrink:0; align-self:flex-end; }
    #rw-send { width:46px; height:46px; border-radius:14px; flex-shrink:0;
        background:${ACCENT}; border:none; cursor:pointer; color:#fff; font-size:18px;
        display:flex; align-items:center; justify-content:center;
        box-shadow:0 0 20px rgba(249,115,22,.3); transition:all .2s ease; }
    #rw-send:hover { transform:translateY(-2px); box-shadow:0 0 28px rgba(249,115,22,.5); }
    #rw-send:active { transform:scale(.95); }
    #rw-send:disabled { opacity:.4; cursor:not-allowed; transform:none; box-shadow:none; }

    #rw-footer { padding:6px 16px 10px; display:flex; justify-content:center;
        font-family:'Space Mono',monospace; font-size:10px; color:#1e2d45; }
    #rw-footer kbd { background:#131f33; border:1px solid #1e2d45; border-radius:4px;
        padding:1px 5px; font-family:'Space Mono',monospace; font-size:9px; color:#2d3f55; }

    @media(hover:none){ #rw-footer .rw-kbd{ display:none; } }
    @media(prefers-reduced-motion:reduce){
        #rw-fab,#rw-panel,.rw-msg,.rw-wicon,.rw-td{ animation:none !important; transition:none !important; }
    }
    @media(max-width:480px){
        #rw-panel{ width:100vw; left:0; right:0; top:0; bottom:0;
            height:100vh; height:100dvh; border-radius:0; border:none; }
        #rw-fab{ ${isLeft?'left:14px':'right:14px'}; bottom:14px; }
        #rw-hero{ padding:14px 16px 12px; }
        #rw-hero-desc{ display:none; }
        #rw-pops-grid{ display:flex; overflow-x:auto; gap:8px; padding-bottom:6px;
            scrollbar-width:none; -webkit-overflow-scrolling:touch; }
        #rw-pops-grid::-webkit-scrollbar{ display:none; }
        .rw-pop{ flex:0 0 auto; max-width:240px; }
        #rw-footer .rw-kbd{ display:none; }
        .rw-tab-close{ display:block; }
    }`;

    var st=document.createElement('style'); st.textContent=css; document.head.appendChild(st);

    // ── FAB ──────────────────────────────────────────────────────────
    var fab=document.createElement('button'); fab.id='rw-fab'; fab.innerHTML='🧠'; fab.title=TITLE;
    fab.setAttribute('aria-label',TITLE); fab.setAttribute('aria-expanded','false');
    fab.addEventListener('click',toggle); document.body.appendChild(fab);

    // ── PANEL ─────────────────────────────────────────────────────────
    var panel=document.createElement('div'); panel.id='rw-panel';
    panel.innerHTML=
        // Hero
        '<div id="rw-hero">'+
            '<div id="rw-hero-top">'+
                '<div>'+
                    '<div id="rw-hero-badge">ASSISTANT IA · BLOG</div>'+
                    '<div id="rw-hero-title">Explore <span id="rw-cnt">350+</span> articles<br>avec l\'IA</div>'+
                    '<div id="rw-hero-desc">Pose une question, obtiens une réponse précise tirée des articles de Laurent Husser — IA, n8n, géobiologie, développement personnel.</div>'+
                    '<div id="rw-hero-stats">'+
                        '<div class="rw-stat-cnt">🧠 <strong id="rw-vcnt">...</strong> articles indexés</div>'+
                        '<div class="rw-stat-online" id="rw-online">en ligne</div>'+
                    '</div>'+
                '</div>'+
                '<button id="rw-close-btn">✕</button>'+
            '</div>'+
        '</div>'+
        // Questions populaires
        '<div id="rw-pops">'+
            '<div id="rw-pops-label">QUESTIONS POPULAIRES</div>'+
            '<div id="rw-pops-grid">'+
                SUGS.map(function(s){return '<button class="rw-pop" onclick="rwAsk(\''+s.replace(/'/g,"\\'")+'\')">'+esc(s)+'</button>';}).join('')+
            '</div>'+
        '</div>'+
        // Tabs
        '<div id="rw-tabs">'+
            '<button class="rw-tab active" id="rw-tchat"   onclick="rwMode(\'chat\')">💬 Chat IA</button>'+
            '<button class="rw-tab"        id="rw-tsearch" onclick="rwMode(\'search\')">🔍 Recherche</button>'+
            '<button class="rw-tab rw-tab-clear" onclick="rwClear()">🗑 Effacer</button>'+
            '<button class="rw-tab" onclick="rwExportAll()" aria-label="Exporter la conversation en PDF" title="Exporter la conversation en PDF">📄</button>'+
            '<button class="rw-tab rw-tab-close" onclick="rwClose()" aria-label="Fermer le chat">✕</button>'+
        '</div>'+
        // Messages
        '<div id="rw-msgs" role="log" aria-live="polite"><div class="rw-welcome" id="rw-welcome">'+
            '<div class="rw-wicon">✨</div>'+
            '<h4>Bonjour !</h4>'+
            '<p>Je suis l\'assistant du blog lhusser.fr. Pose-moi une question ou clique sur une suggestion.</p>'+
        '</div></div>'+
        // Input
        '<div id="rw-iz">'+
            '<div id="rw-irow">'+
                '<div id="rw-iwrap"><textarea id="rw-ta" placeholder="Pose ta question ici…" rows="1" maxlength="500"></textarea>'+
                '<span id="rw-cc">0 / 500</span></div>'+
                '<button id="rw-send" onclick="rwSend()" title="Envoyer">➤</button>'+
            '</div>'+
        '</div>'+
        '<div id="rw-footer"><span class="rw-kbd"><kbd>Enter</kbd>&nbsp;envoyer · <kbd>Shift+Enter</kbd>&nbsp;ligne&nbsp;·&nbsp;</span>🔒 Serveur privé · Propulsé par Claude + Gemini</div>';
    document.body.appendChild(panel);

    document.getElementById('rw-close-btn').setAttribute('aria-label','Fermer');
    document.getElementById('rw-send').setAttribute('aria-label','Envoyer');
    document.getElementById('rw-close-btn').addEventListener('click',closePanel);
    document.addEventListener('keydown',function(e){
        if(e.key==='Escape'&&panel.classList.contains('ropen'))closePanel();
    });
    document.addEventListener('click',function(e){
        if(panel.classList.contains('ropen')&&!panel.contains(e.target)&&!fab.contains(e.target))closePanel();
    });

    var ta=document.getElementById('rw-ta');
    ta.addEventListener('input',function(){
        this.style.height='auto'; this.style.height=Math.min(this.scrollHeight,100)+'px';
        document.getElementById('rw-cc').textContent=this.value.length+' / 500';
    });
    ta.addEventListener('keydown',function(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();rwSend();}});

    // Stats + Articles
    var allArticles = [];
    fetchStats();
    restoreHist();
    async function fetchStats(){
        var base = RAG_URL.replace('/api/public-query','');
        // Fallback : si l'API ne répond pas en 3 s, on affiche une valeur sûre
        setTimeout(function(){
            var v=document.getElementById('rw-vcnt');
            if(v&&v.textContent==='...'){
                v.textContent='350+';
                document.getElementById('rw-cnt').textContent='350+';
            }
        },3000);
        // Stats vecteurs
        try{
            var r=await fetch(base+'/api/stats',{credentials:'include'});
            if(r.ok){
                var d=await r.json();
                document.getElementById('rw-cnt').textContent=(d.total_vectors?Math.floor(d.total_vectors/10)*10+'+':'350+');
                document.getElementById('rw-vcnt').textContent=(d.total_vectors||'...');
                document.getElementById('rw-online').classList.add('live');
            }
        }catch(e){}
        // Articles
        try{
            var r2=await fetch(base+'/api/public-articles');
            if(r2.ok){
                var d2=await r2.json();
                allArticles=d2.articles||[];
                document.getElementById('rw-cnt').textContent=allArticles.length+'+';
                document.getElementById('rw-vcnt').textContent=allArticles.length;
                // Mettre à jour les suggestions avec de vrais articles récents
                updateSuggestions(allArticles);
            }
        }catch(e){}
    }

    function updateSuggestions(articles){
        var grid=document.getElementById('rw-pops-grid');
        if(!grid||!articles.length) return;
        var recent=articles.slice(0,6);
        grid.innerHTML=recent.map(function(a){
            var emoji=getCatEmoji(a.category);
            var title=a.title.length>35?a.title.slice(0,33)+'...':a.title;
            var encoded=encodeURIComponent(a.title);
            return '<button class="rw-pop" onclick="rwAsk(decodeURIComponent(\'' +encoded+ '\'))" title="'+esc(a.title)+'">'+
                emoji+' '+esc(title)+'</button>';
        }).join('');
    }

    function getCatEmoji(cat){
        if(!cat) return '📝';
        if(cat.includes('Intelligence') || cat.includes('IA')) return '🤖';
        if(cat.includes('Surnaturel') || cat.includes('Spirituel')) return '🔮';
        if(cat.includes('Mac') || cat.includes('Apple')) return '🍎';
        if(cat.includes('Personnel') || cat.includes('Développement')) return '🌱';
        if(cat.includes('Géobio')) return '🌍';
        if(cat.includes('Musique')) return '🎵';
        if(cat.includes('Santé')) return '💚';
        return '📝';
    }

    // Toggle
    var mode='chat';
    function toggle(){panel.classList.contains('ropen')?closePanel():openPanel();}
    function openPanel(){
        panel.classList.add('ropen');fab.innerHTML='✕';fab.setAttribute('aria-expanded','true');
        if(window.innerWidth<=480){document.body.style.overflow='hidden';fab.style.display='none';}
        setTimeout(function(){ta.focus();},350);
    }
    function closePanel(){
        panel.classList.remove('ropen');fab.innerHTML='🧠';fab.setAttribute('aria-expanded','false');
        document.body.style.overflow='';fab.style.display='';
    }
    window.rwClose=closePanel;

    window.rwMode=function(m){
        mode=m;
        document.getElementById('rw-tchat').classList.toggle('active',m==='chat');
        document.getElementById('rw-tsearch').classList.toggle('active',m==='search');
        ta.placeholder=m==='chat'?'Pose ta question ici…':'Recherche un article par sujet…';
    };

    window.rwClear=function(){
        clearHist();
        var hero=document.getElementById('rw-hero'),pops=document.getElementById('rw-pops');
        if(hero)hero.style.display='';if(pops)pops.style.display='';
        document.getElementById('rw-msgs').innerHTML='<div class="rw-welcome" id="rw-welcome"><div class="rw-wicon">✨</div><h4>Bonjour !</h4><p>Je suis l\'assistant du blog lhusser.fr. Pose-moi une question ou clique sur une suggestion.</p></div>';
    };

    function removeWelcome(){var w=document.getElementById('rw-welcome');if(w)w.remove();}
    function hideHero(){
        var hero=document.getElementById('rw-hero');
        var pops=document.getElementById('rw-pops');
        if(hero) hero.style.display='none';
        if(pops) pops.style.display='none';
    }

    function addUser(text,opts){
        opts=opts||{};
        removeWelcome();
        var c=document.getElementById('rw-msgs'),d=document.createElement('div');
        d.className='rw-msg u';
        d.innerHTML='<div class="rw-av">👤</div><div class="rw-body"><div class="rw-bub">'+esc(text)+'</div><div class="rw-time">'+(opts.time||now())+'</div></div>';
        c.appendChild(d);c.scrollTop=c.scrollHeight;
        if(!opts.noSave)saveMsg({r:'u',t:text,time:now()});
    }

    function addBot(html,sources,q,opts){
        opts=opts||{};
        var c=document.getElementById('rw-msgs'),d=document.createElement('div');
        d.className='rw-msg b';
        var srcHtml='';
        if(sources&&sources.length){
            srcHtml='<div class="rw-srcs"><div class="rw-srcs-lbl">📎 Sources consultées</div>'+
                sources.slice(0,4).map(function(s){
                    var srcName=s.source||s.title||'Source';
                    // 1) URL fournie directement par l'API (métadonnées WXR)
                    var url=(s.url&&s.url.indexOf('http')===0)?s.url:'#';
                    // 2) Fallback : matching dans articles.json
                    if(url==='#'&&allArticles.length){
                        var found=allArticles.find(function(a){
                            return a.title&&srcName&&(
                                a.title.toLowerCase().includes(srcName.toLowerCase().slice(0,20))||
                                srcName.toLowerCase().includes(a.title.toLowerCase().slice(0,20))
                            );
                        });
                        if(found&&found.link) url=found.link;
                    }
                    var isLink=url!=='#';
                    return '<'+(isLink?'a href="'+esc(url)+'" target="_blank" rel="noopener"':'span')+' class="rw-src">'+
                        '<span class="txt">📄 '+esc(srcName)+'</span>'+
                        (isLink?'<span class="arr">↗ Lire l’article</span>':'<span class="arr">'+s.score+'</span>')+
                        '</'+(isLink?'a':'span')+'>';
                }).join('')+'</div>';
        }
        var acts='<div class="rw-acts">'+
            '<button class="rw-act" data-fb="up" aria-label="Réponse utile">👍</button>'+
            '<button class="rw-act" data-fb="down" aria-label="Réponse peu utile">👎</button>'+
            '<button class="rw-act rw-copy" aria-label="Copier la réponse">📋 Copier</button>'+
            '<button class="rw-act rw-pdf" aria-label="Exporter en PDF">📄 PDF</button></div>';
        d.innerHTML='<div class="rw-av">✨</div><div class="rw-body"><div class="rw-bub"><p style="margin:0" class="rw-txt"></p>'+srcHtml+'</div>'+acts+'<div class="rw-time">'+(opts.time||now())+'</div></div>';
        c.appendChild(d);
        var txtEl=d.querySelector('.rw-txt');
        if(opts.instant||prefersReduced()){txtEl.innerHTML=html;}
        else typewrite(txtEl,html,c);
        bindActions(d,q,html,sources);
        c.scrollTop=c.scrollHeight;
        if(!opts.noSave)saveMsg({r:'b',h:html,s:sources||[],q:q||'',time:opts.time||now()});
    }

    function prefersReduced(){
        return window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }

    // Effet machine à écrire : texte brut progressif, puis bascule en HTML formaté
    function typewrite(el,html,scroller){
        var tmp=document.createElement('div');tmp.innerHTML=html;
        var txt=tmp.textContent||'';
        if(txt.length>800){el.innerHTML=html;return;}
        var i=0,step=Math.max(2,Math.round(txt.length/120));
        var iv=setInterval(function(){
            i+=step;el.textContent=txt.slice(0,i);
            scroller.scrollTop=scroller.scrollHeight;
            if(i>=txt.length){clearInterval(iv);el.innerHTML=html;scroller.scrollTop=scroller.scrollHeight;}
        },16);
    }

    function bindActions(d,q,html,sources){
        var tmp=document.createElement('div');tmp.innerHTML=html;
        var plain=tmp.textContent||'';
        var cp=d.querySelector('.rw-copy');
        if(cp)cp.addEventListener('click',function(){
            if(!navigator.clipboard)return;
            navigator.clipboard.writeText(plain).then(function(){
                cp.textContent='✓ Copié';
                setTimeout(function(){cp.textContent='📋 Copier';},1500);
            }).catch(function(){});
        });
        var pdfBtn=d.querySelector('.rw-pdf');
        if(pdfBtn)pdfBtn.addEventListener('click',function(){exportPdf(q,html,sources);});
        d.querySelectorAll('[data-fb]').forEach(function(b){
            b.addEventListener('click',function(){
                d.querySelectorAll('[data-fb]').forEach(function(x){x.classList.remove('sel');});
                b.classList.add('sel');
                // Endpoint optionnel — échoue en silence s'il n'existe pas encore côté VPS
                try{
                    fetch(RAG_URL.replace('/api/public-query','')+'/api/feedback',{
                        method:'POST',headers:{'Content-Type':'application/json'},
                        body:JSON.stringify({question:q||'',answer:plain.slice(0,500),vote:b.dataset.fb})
                    }).catch(function(){});
                }catch(e){}
            });
        });
    }

    // ── Export PDF (impression native, charte lhusser.fr) ──
    function _pdfShell(title, inner){
        var w=window.open('','_blank');
        if(!w){alert('Autorise les pop-ups pour exporter en PDF.');return;}
        w.document.write('<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">'+
        '<title>'+esc(title)+'</title>'+
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap">'+
        '<style>'+
        '*{-webkit-print-color-adjust:exact;print-color-adjust:exact}'+
        'body{font-family:Syne,Arial,sans-serif;max-width:720px;margin:0 auto;padding:0 24px 24px;color:#1e293b;line-height:1.75;font-size:14px}'+
        '.band{background:#0f172a;margin:0 -24px;padding:26px 28px 22px;border-bottom:4px solid #f97316;border-radius:0 0 18px 18px}'+
        '.badge{display:inline-block;font-family:\'Space Mono\',monospace;font-size:10px;letter-spacing:.1em;color:#f97316;border:1px solid rgba(249,115,22,.45);border-radius:20px;padding:4px 12px;margin-bottom:12px;font-weight:700}'+
        '.band h1{color:#fff;font-size:22px;font-weight:800;margin:0;letter-spacing:-.01em}'+
        '.band h1 span{color:#f97316}'+
        '.meta{font-family:\'Space Mono\',monospace;color:#94a3b8;font-size:10px;margin-top:8px}'+
        '.q{background:#fff7ed;border-left:4px solid #f97316;border-radius:0 10px 10px 0;padding:13px 16px;margin:22px 0;font-style:italic;color:#7c2d12;page-break-inside:avoid}'+
        '.answer *{color:#1e293b !important;background:transparent !important;font-family:Syne,Arial,sans-serif !important}'+
        '.answer strong{color:#0f172a !important}'+
        '.answer a{color:#ea580c !important;text-decoration:underline}'+
        '.answer code{font-family:\'Space Mono\',monospace !important;background:#fff7ed !important;color:#c2410c !important;padding:1px 5px;border-radius:4px;font-size:12px}'+
        '.answer ul{padding-left:20px}'+
        'h2{font-family:\'Space Mono\',monospace;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#f97316;margin-top:28px}'+
        '.src{border:1px solid #e2e8f0;border-left:3px solid #f97316;border-radius:10px;padding:10px 14px;margin-bottom:8px;page-break-inside:avoid}'+
        '.st{font-weight:700;color:#0f172a;font-size:13px}'+
        '.su{font-family:\'Space Mono\',monospace;color:#94a3b8;font-size:10px;word-break:break-all;margin-top:2px}'+
        '.sep{border:none;border-top:1px dashed #cbd5e1;margin:30px 0}'+
        '.foot{margin-top:36px;border-top:1px solid #e2e8f0;padding-top:10px;color:#94a3b8;font-family:\'Space Mono\',monospace;font-size:10px}'+
        '@media print{body{margin:0 auto}}'+
        '</style></head><body>'+
        '<div class="band"><div class="badge">● ASSISTANT IA · BLOG</div>'+
        '<h1>Assistant <span>lhusser.fr</span></h1>'+
        '<div class="meta">Généré le '+new Date().toLocaleString('fr')+'</div></div>'+
        inner+
        '<p class="foot">🧠 Réponse générée par l\'assistant IA du blog — articles complets sur https://lhusser.fr</p>'+
        '</body></html>');
        w.document.close();
        var go=function(){setTimeout(function(){w.focus();w.print();},250);};
        if(w.document.fonts&&w.document.fonts.ready){w.document.fonts.ready.then(go);}else{setTimeout(go,800);}
    }

    function _srcCards(sources){
        return (sources||[]).filter(function(s){return s&&s.url;}).map(function(s){
            return '<div class="src"><div class="st">📄 '+esc(s.title||s.source||s.url)+'</div>'+
                   '<div class="su">'+esc(s.url)+'</div></div>';
        }).join('');
    }

    function exportPdf(q,html,sources){
        var srcs=_srcCards(sources);
        _pdfShell('Assistant lhusser.fr — '+(q||'réponse').slice(0,60),
            (q?'<div class="q"><strong>Question :</strong> '+esc(q)+'</div>':'')+
            '<div class="answer">'+html+'</div>'+
            (srcs?'<h2>✦ Sources consultées</h2>'+srcs:''));
    }

    // Export de la conversation complète (depuis l'historique persistant)
    function exportAllPdf(){
        var h=loadHist();
        if(!h.length){alert('Aucune conversation à exporter pour le moment.');return;}
        var body='',n=0;
        h.forEach(function(m){
            if(m.r==='u'){
                n++;
                body+='<div class="q"><strong>Question '+n+' :</strong> '+esc(m.t)+'</div>';
            }else{
                body+='<div class="answer">'+m.h+'</div>';
                var srcs=_srcCards(m.s);
                if(srcs)body+='<h2>✦ Sources</h2>'+srcs;
                body+='<hr class="sep">';
            }
        });
        _pdfShell('Conversation — Assistant lhusser.fr', body);
    }
    window.rwExportAll=exportAllPdf;

    // ── Historique persistant (localStorage, 30 derniers messages) ──
    var HKEY='rwHistoryV1';
    function loadHist(){try{return JSON.parse(localStorage.getItem(HKEY)||'[]');}catch(e){return[];}}
    function saveMsg(m){try{var h=loadHist();h.push(m);if(h.length>30)h=h.slice(-30);localStorage.setItem(HKEY,JSON.stringify(h));}catch(e){}}
    function clearHist(){try{localStorage.removeItem(HKEY);}catch(e){}}
    function restoreHist(){
        var h=loadHist();if(!h.length)return;
        removeWelcome();hideHero();
        h.forEach(function(m){
            if(m.r==='u')addUser(m.t,{noSave:true,time:m.time});
            else addBot(m.h,m.s,m.q,{instant:true,noSave:true,time:m.time});
        });
    }

    function addTyping(){
        var c=document.getElementById('rw-msgs'),d=document.createElement('div');
        d.className='rw-msg b';d.id='rw-typ';
        d.innerHTML='<div class="rw-av">✨</div><div class="rw-body"><div class="rw-bub"><div class="rw-typing"><div class="rw-td"></div><div class="rw-td"></div><div class="rw-td"></div></div></div></div>';
        c.appendChild(d);c.scrollTop=c.scrollHeight;return d;
    }

    window.rwSend=async function(){
        var q=ta.value.trim();if(!q)return;
        ta.value='';ta.style.height='auto';document.getElementById('rw-cc').textContent='0 / 500';
        document.getElementById('rw-send').disabled=true;
        hideHero(); addUser(q);

        // Mode Recherche locale dans articles.json
        if(mode==='search' && allArticles.length){
            var ql=q.toLowerCase();
            var results=allArticles.filter(function(a){
                return (a.title&&a.title.toLowerCase().includes(ql))||
                       (a.category&&a.category.toLowerCase().includes(ql))||
                       (a.description&&a.description.toLowerCase().includes(ql));
            }).slice(0,8);
            addSearchResults(results, q);
            document.getElementById('rw-send').disabled=false;
            ta.focus(); return;
        }

        var typ=addTyping();
        try{
            var r=await fetch(RAG_URL,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,mode:mode})});
            var d=await r.json(); typ.remove();
            addBot(md(stripSources(d.answer)||'Désolé, aucune réponse trouvée.'),d.sources,q);
        }catch(e){
            typ.remove();
            var c=document.getElementById('rw-msgs'),div=document.createElement('div');
            div.className='rw-msg b';
            div.innerHTML='<div class="rw-av">⚠️</div><div class="rw-body"><div class="rw-err">Erreur de connexion. Réessaie dans un instant.</div></div>';
            c.appendChild(div); c.scrollTop=c.scrollHeight;
        }finally{ document.getElementById('rw-send').disabled=false; ta.focus(); }
    };

    function addSearchResults(results, q){
        var c=document.getElementById('rw-msgs'), d=document.createElement('div');
        d.className='rw-msg b';
        var html='';
        if(!results.length){
            html='<div class="rw-err">Aucun article trouvé pour "'+esc(q)+'".</div>';
        } else {
            html='<div style="color:#64748b;font-family:Space Mono,monospace;font-size:11px;margin-bottom:10px">'+
                results.length+' article(s) trouvé(s)</div>'+
                results.map(function(a){
                    var emoji=getCatEmoji(a.category);
                    return '<a href="'+esc(a.link)+'" target="_blank" rel="noopener" class="rw-art-card">'+
                        '<div class="rw-art-title">'+emoji+' '+esc(a.title)+'</div>'+
                        '<div class="rw-art-cat">'+esc(a.category||'')+'<span class="rw-art-arr">↗ Lire</span></div>'+
                    '</a>';
                }).join('');
        }
        d.innerHTML='<div class="rw-av">🔍</div><div class="rw-body"><div class="rw-bub">'+html+'</div><div class="rw-time">'+now()+'</div></div>';
        c.appendChild(d); c.scrollTop=c.scrollHeight;
    }

    window.rwAsk=function(t){ta.value=t;rwSend();};
})();
