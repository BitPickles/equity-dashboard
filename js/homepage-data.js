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
    if(btc.usd)setText('.hero-price','$'+Math.round(btc.usd).toLocaleString());
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
      if(val<0.45){zoneEl.textContent='抄底区';zoneEl.className='ind-zone g';}
      else if(val<1.2){zoneEl.textContent='定投区';zoneEl.className='ind-zone y';}
      else{zoneEl.textContent='过热区';zoneEl.className='ind-zone r';}
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
      if(val<1){zoneEl.textContent='低估区';zoneEl.className='ind-zone g';}
      else if(val<2.5){zoneEl.textContent='合理区';zoneEl.className='ind-zone y';}
      else{zoneEl.textContent='过热区';zoneEl.className='ind-zone r';}
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
      if(val>65){zoneEl.textContent='BTC主导';zoneEl.className='ind-zone y';}
      else if(val>50){zoneEl.textContent='平衡';zoneEl.className='ind-zone b';}
      else{zoneEl.textContent='山寨季';zoneEl.className='ind-zone g';}
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
    // governance count updated from governance.json below
  }).catch(function(){});

  // Load governance data for governance cards
  fetch('./data/governance.json').then(function(r){return r.json()}).then(function(d){
    var proposals=d.proposals||[];
    // Update governance protocol count
    var govProtos=new Set();
    proposals.forEach(function(p){if(p.protocol)govProtos.add(p.protocol)});
    var gEl=document.getElementById('kpi-governance');if(gEl)gEl.textContent=govProtos.size;
    var gEl2=document.getElementById('stat-governance');if(gEl2)gEl2.textContent=govProtos.size;
    if(!proposals.length)return;
    // Get 2 most recent TEV-related or active proposals
    var active=proposals.filter(function(p){return p.status==='active'||p.tev_related});
    if(!active.length)active=proposals;
    active.sort(function(a,b){return(b.created||0)-(a.created||0)});
    function renderGovCards(lang){
      var cards=document.querySelectorAll('.gov-card');
      var isEn=lang==='en';
      for(var i=0;i<Math.min(cards.length,active.length);i++){
        var p=active[i],c=cards[i];
        var titleEl=c.querySelector('.gov-card-title');
        var protoEl=c.querySelector('.gov-card-proto');
        var statusEl=c.querySelector('.gov-card-status');
        if(titleEl){
          var title=isEn?(p.summary_en||p.title||''):(p.summary_zh||p.title||'');
          title=title.replace(/[>#*\-\n\r]+/g,' ').replace(/\s+/g,' ').trim();
          titleEl.textContent=title.substring(0,40);
        }
        var statusActive=isEn?'Voting':'投票中';
        var statusEnded=isEn?'Ended':'已结束';
        if(protoEl)protoEl.textContent=p.protocol+' · '+(p.status==='active'?statusActive:statusEnded);
        if(statusEl){
          if(p.tev_related){statusEl.textContent=isEn?'TEV Related':'TEV 相关';statusEl.className='gov-card-status tev';}
          else if(p.status==='active'){statusEl.textContent=statusActive;statusEl.className='gov-card-status active';}
          else{statusEl.textContent=statusEnded;statusEl.className='gov-card-status passed';}
        }
        c.href='./governance/';
      }
    }
    var curLang=window.CryptoLang?CryptoLang.get():(localStorage.getItem('lang')||'zh');
    renderGovCards(curLang);
    window.addEventListener('langchange',function(e){renderGovCards(e.detail.lang);});
  }).catch(function(){});

})();
