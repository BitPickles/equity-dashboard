/**
 * Homepage Dynamic Data Loader
 * Fetches real data from JSON files and updates hardcoded placeholders
 */
(function(){
  function fmt(n,d){return n?n.toFixed(d||2):'--'}
  function fmtUSD(n){
    if(!n)return'--';
    if(n>=1e12)return'$'+(n/1e12).toFixed(2)+'T';
    if(n>=1e9)return'$'+(n/1e9).toFixed(1)+'B';
    if(n>=1e6)return'$'+(n/1e6).toFixed(1)+'M';
    return'$'+n.toLocaleString();
  }
  function pctChange(arr,key,days){
    if(!arr||arr.length<days+1)return null;
    var cur=arr[arr.length-1][key],prev=arr[arr.length-1-days][key];
    if(!prev)return null;
    return((cur-prev)/prev*100);
  }
  function setText(sel,val){
    var el=document.querySelector(sel);
    if(el)el.textContent=val;
  }
  function getLangCode(){return (window.CryptoLang&&CryptoLang.get())||localStorage.getItem('lang')||'zh';}
  // 写入 data-zh/data-en 并按当前语言设值（保证语言切换时同步）
  function setI18n(el,zh,en){
    if(!el)return;
    el.setAttribute('data-zh',zh);el.setAttribute('data-en',en);
    el.textContent=getLangCode()==='en'?en:zh;
  }

  // Load global market data from CoinGecko
  fetch('https://api.coingecko.com/api/v3/global').then(function(r){return r.json()}).then(function(d){
    var data=d.data||{};
    var mc=data.total_market_cap&&data.total_market_cap.usd;
    var vol=data.total_volume&&data.total_volume.usd;
    var btcD=data.market_cap_percentage&&data.market_cap_percentage.btc;
    // Update hero meta values by index
    var metaVals=document.querySelectorAll('.hero-meta-item .hero-meta-val');
    if(mc&&metaVals[0])metaVals[0].textContent=fmtUSD(mc);
    if(vol&&metaVals[1])metaVals[1].textContent=fmtUSD(vol);
    if(btcD&&metaVals[2])metaVals[2].textContent=fmt(btcD,1)+'%';
  }).catch(function(){});

  // Load BTC price from CoinGecko simple/price
  fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true').then(function(r){return r.json()}).then(function(d){
    var btc=d.bitcoin||{};
    if(btc.usd){
      setText('.hero-price','$'+Math.round(btc.usd).toLocaleString());
      var hp=document.querySelector('.hero-price');if(hp)hp.classList.add('cg-loaded'); // 阻止 ahr999 旧价回冲
      window.__heroLive={price:btc.usd};   // 追加为 Hero 图表末点，与显示价一致
      if(window.renderHero)renderHero();
    }
    var chg=btc.usd_24h_change;
    var heroChg=document.querySelector('.hero-change');
    if(heroChg&&chg!==undefined&&chg!==null){
      heroChg.textContent=(chg>=0?'+':'')+fmt(chg,1)+'%';
      heroChg.className='hero-change '+(chg>=0?'up':'down');
    }
  }).catch(function(){});

  // Load AHR999
  fetch('./indicators/data/ahr999.json').then(function(r){return r.json()}).then(function(d){
    var cur=d.current||{};
    var hist=d.history||[];
    var val=cur.ahr999||hist[hist.length-1]?.ahr999;
    var price=cur.btc_price||hist[hist.length-1]?.btc_price;
    // Update indicator card
    var indEl=document.querySelector('a[href="./ahr999/"] .ind-val');
    if(indEl&&val)indEl.textContent=fmt(val,2);
    // Update zone
    var zoneEl=document.querySelector('a[href="./ahr999/"] .ind-zone');
    if(zoneEl&&val){
      if(val<0.45){setI18n(zoneEl,'抄底区','Buy Zone');zoneEl.className='ind-zone g';}
      else if(val<1.2){setI18n(zoneEl,'定投区','DCA Zone');zoneEl.className='ind-zone y';}
      else{setI18n(zoneEl,'过热区','Overheated');zoneEl.className='ind-zone r';}
    }
    // Update sparkline data
    if(hist.length>7){
      var last7=hist.slice(-7).map(function(x){return x.ahr999});
      if(window.sp)sp('sp-a',last7,'#60a5fa');
    }
    // Update 7d change
    var chg=pctChange(hist,'ahr999',7);
    var chgEl=document.querySelector('a[href="./ahr999/"] .ind-chg');
    if(chgEl&&chg!==null){
      chgEl.textContent=(chg>=0?'+':'')+fmt(chg,1)+'%';
      chgEl.className='ind-chg '+(chg>=0?'up':'down')+' mono';
    }
    // Hero chart series — 真实 BTC 日线收盘价（近 180 天），复用本文件已拉取的 ahr999.json
    if(hist.length>2){
      var series=hist.slice(-180).filter(function(x){return x.close}).map(function(x){return {date:x.date,price:x.close}});
      if(series.length>2){window.__heroSeries=series;if(window.renderHero)renderHero();}
    }
    // Hero price fallback (if CoinGecko fails)
    if(price&&!document.querySelector('.hero-price.cg-loaded')){
      setText('.hero-price','$'+Math.round(price).toLocaleString());
    }
  }).catch(function(){});

  // Load MVRV
  fetch('./indicators/data/mvrv.json').then(function(r){return r.json()}).then(function(d){
    var cur=d.current||{};
    var hist=d.history||[];
    var val=cur.mvrv||hist[hist.length-1]?.mvrv;
    var indEl=document.querySelector('a[href="./mvrv/"] .ind-val');
    if(indEl&&val)indEl.textContent=fmt(val,2);
    var zoneEl=document.querySelector('a[href="./mvrv/"] .ind-zone');
    if(zoneEl&&val){
      if(val<1){setI18n(zoneEl,'低估区','Undervalued');zoneEl.className='ind-zone g';}
      else if(val<2.5){setI18n(zoneEl,'合理区','Fair Zone');zoneEl.className='ind-zone y';}
      else{setI18n(zoneEl,'过热区','Overheated');zoneEl.className='ind-zone r';}
    }
    if(hist.length>7){
      var last7=hist.slice(-7).map(function(x){return x.mvrv});
      if(window.sp)sp('sp-m',last7,'#a78bfa');
    }
    var chg=pctChange(hist,'mvrv',7);
    var chgEl=document.querySelector('a[href="./mvrv/"] .ind-chg');
    if(chgEl&&chg!==null){
      chgEl.textContent=(chg>=0?'+':'')+fmt(chg,1)+'%';
      chgEl.className='ind-chg '+(chg>=0?'up':'down')+' mono';
    }
  }).catch(function(){});

  // Load BTC.D
  fetch('./indicators/data/btc-dominance.json').then(function(r){return r.json()}).then(function(d){
    var cur=d.current||{};
    var hist=d.history||[];
    var val=cur.dominance||cur.value||hist[hist.length-1]?.dominance||hist[hist.length-1]?.value;
    var indEl=document.querySelector('a[href="./btc-dominance/"] .ind-val');
    if(indEl&&val)indEl.textContent=fmt(val,1)+'%';
    // Hero BTC占比
    setText('.hero-meta-item:nth-child(3) .hero-meta-val',fmt(val,1)+'%');
    var zoneEl=document.querySelector('a[href="./btc-dominance/"] .ind-zone');
    if(zoneEl&&val){
      if(val>65){setI18n(zoneEl,'BTC主导','BTC-Led');zoneEl.className='ind-zone y';}
      else if(val>50){setI18n(zoneEl,'平衡','Balanced');zoneEl.className='ind-zone b';}
      else{setI18n(zoneEl,'山寨季','Altcoin Season');zoneEl.className='ind-zone g';}
    }
    if(hist.length>7){
      var last7=hist.slice(-7).map(function(x){return x.dominance||x.value});
      if(window.sp)sp('sp-d',last7,'#38bdf8');
    }
    var chg=pctChange(hist,hist[0]?.dominance!==undefined?'dominance':'value',7);
    var chgEl=document.querySelector('a[href="./btc-dominance/"] .ind-chg');
    if(chgEl&&chg!==null){
      chgEl.textContent=(chg>=0?'+':'')+fmt(chg,1)+'%';
      chgEl.className='ind-chg '+(chg>=0?'up':'down')+' mono';
    }
  }).catch(function(){});

  // Update TEV KPI stats from all-protocols.json
  fetch('./data/all-protocols.json').then(function(r){return r.json()}).then(function(d){
    var protos=d.protocols,list=[];
    var totalProtos=Object.keys(protos).length;
    for(var k in protos){var p=protos[k];var y=p.shareholder_yield_percent||0;if(y>0)list.push(y)}
    var el1=document.getElementById('kpi-total');if(el1)el1.textContent=totalProtos;
    var el1b=document.getElementById('stat-total');if(el1b)el1b.textContent=totalProtos;
    var el2=document.getElementById('kpi-active');if(el2)el2.textContent=list.length;
    // 中位 P/E（仅统计有正 PE 的协议）
    var pes=[];
    for(var kk in protos){var fs=protos[kk].financial_snapshot||{};var pe=fs.pe;if(typeof pe==='number'&&pe>0)pes.push(pe)}
    if(pes.length){
      pes.sort(function(a,b){return a-b});
      var mid=(pes.length%2)?pes[(pes.length-1)/2]:(pes[pes.length/2-1]+pes[pes.length/2])/2;
      var el3=document.getElementById('kpi-pe');if(el3)el3.textContent=mid.toFixed(1);
    }
    // governance count updated from governance.json below
  }).catch(function(){});

  // Load governance data for governance cards
  fetch('./data/governance.json').then(function(r){return r.json()}).then(function(d){
    var proposals=d.proposals||[];
    // Update governance protocol count
    var govProtos=new Set();
    proposals.forEach(function(p){if(p.protocol)govProtos.add(p.protocol)});
    var gEl2=document.getElementById('stat-governance');if(gEl2)gEl2.textContent=govProtos.size;
    if(!proposals.length)return;
    function ts(p){var c=p.created;if(typeof c==='number')return c;var d=new Date(c);return isNaN(d)?0:d.getTime()/1000;}
    function fmtMD(v){
      if(v===undefined||v===null||v==='')return'';
      var d=(typeof v==='number')?new Date(v*1000):new Date(v);
      if(isNaN(d.getTime()))return'';
      return(d.getMonth()+1)+'月'+d.getDate()+'日';
    }
    // 剥离「协议：/标题：/摘要：」等抓取前缀，尽量取「标题」行
    function cleanTitle(p,isEn){
      if(isEn)return String(p.title||p.summary_en||'').replace(/\s+/g,' ').trim();
      var s=String(p.summary_zh||'').replace(/\s+/g,' ').trim();
      var m=s.match(/标题[:：]\s*(.+?)(?:\s*摘要[:：]|$)/);
      if(m&&m[1])s=m[1].trim();else s=s.replace(/^(协议|标题|摘要)[:：]\s*/,'').trim();
      return s||String(p.title||'').trim();
    }
    // 最近 3 条「进行中 或 股东回报相关」提案
    var active=proposals.filter(function(p){return p.status==='active'||p.tev_related});
    if(!active.length)active=proposals;
    active=active.slice().sort(function(a,b){return ts(b)-ts(a)});
    function renderGovCards(lang){
      var cards=document.querySelectorAll('.gov-card');
      var isEn=lang==='en';
      for(var i=0;i<Math.min(cards.length,active.length);i++){
        var p=active[i],c=cards[i];
        var titleEl=c.querySelector('.gov-card-title');
        var protoEl=c.querySelector('.gov-card-proto');
        var statusEl=c.querySelector('.gov-card-status');
        if(titleEl){
          var t=cleanTitle(p,isEn);
          titleEl.textContent=t.length>46?t.slice(0,46)+'…':t;
        }
        var statusActive=isEn?'Voting':'投票中';
        var statusEnded=isEn?'Ended':'已结束';
        if(protoEl)protoEl.textContent=(p.protocol||'')+' · '+(p.status==='active'?statusActive:statusEnded);
        if(statusEl){
          if(p.tev_related){statusEl.textContent=isEn?'Capital Return':'股东回报相关';statusEl.className='gov-card-status tev';}
          else if(p.status==='active'){statusEl.innerHTML='<div class="pulse-dot"></div>'+(isEn?'Voting':'投票中');statusEl.className='gov-card-status active';}
          else{statusEl.textContent=statusEnded;statusEl.className='gov-card-status passed';}
        }
        // 底部日期按提案真实 created/end 动态生成（原为陈旧硬编码）
        var metaEl=c.querySelector('.gov-card-meta');
        if(metaEl){
          var createdD=fmtMD(p.created),endD=fmtMD(p.end),mhtml='';
          if(createdD)mhtml+='<dl><dt>'+(isEn?'Submitted':'提交')+'</dt><dd class="mono">'+createdD+'</dd></dl>';
          if(endD)mhtml+='<dl><dt>'+((p.status==='active')?(isEn?'Vote Ends':'投票截止'):(isEn?'Closed':'结束'))+'</dt><dd class="mono">'+endD+'</dd></dl>';
          metaEl.innerHTML=mhtml;
        }
        c.href='./governance/';
      }
    }
    var curLang=window.CryptoLang?CryptoLang.get():(localStorage.getItem('lang')||'zh');
    renderGovCards(curLang);
    window.addEventListener('langchange',function(e){renderGovCards(e.detail.lang);});
  }).catch(function(){});

})();
