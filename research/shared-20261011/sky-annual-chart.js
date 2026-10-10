/* Source-backed React/Recharts chart using the pinned, local Data visualization runtime. */
(function () {
 const figure=document.getElementById('sky-annual-income');
 if(!figure||figure.dataset.mounted==='true')return;
 const runtime=window.CodexDataAppRuntime;
 if(!runtime)return;
 const React=runtime.modules.react;
 const {createRoot}=runtime.modules['react-dom/client'];
 const {ResponsiveContainer,BarChart,Bar,CartesianGrid,XAxis,YAxis,Tooltip,Cell}=runtime.modules.recharts;
 const h=React.createElement;
 const query=JSON.parse(figure.dataset.reviewedRows);
 const colors={gross:'var(--accent)',net:'var(--pink)'};
 const number=new Intl.NumberFormat('zh-CN',{maximumFractionDigits:2,minimumFractionDigits:2});
 function IncomeTooltip({active,payload}){
  if(!active||!payload?.length)return null;
  const row=payload[0].payload;
  return h('div',{className:'sky-annual-tooltip',role:'status'},
   h('strong',null,row.complete?`${row.year}全年`:`${row.year}年1月1日—10月9日（累计）`),
   h('div',null,h('span',null,'业务毛收入'),h('b',null,number.format(row.grossMillion)+' 百万美元')),
   h('div',null,h('span',null,'扣储蓄成本后收入'),h('b',null,number.format(row.afterSavingsMillion)+' 百万美元')),
  );
 }
 function Chart(){
  return h(ResponsiveContainer,{width:'100%',height:'100%',minWidth:0},
   h(BarChart,{data:query.rows,margin:{top:18,right:4,bottom:4,left:0},barGap:3,barCategoryGap:'22%',accessibilityLayer:true},
    h('defs',null,...[['gross',colors.gross],['net',colors.net]].map(([name,color])=>
     h('pattern',{key:name,id:'sky-ytd-'+name,width:6,height:6,patternUnits:'userSpaceOnUse'},
      h('rect',{width:6,height:6,fill:color,fillOpacity:0.18}),
      h('path',{d:'M-1,1 L1,-1 M0,6 L6,0 M5,7 L7,5',stroke:color,strokeWidth:1.8})
     )
    )),
    h(CartesianGrid,{vertical:false,stroke:'var(--line)',strokeDasharray:'3 4'}),
    h(XAxis,{dataKey:'label',interval:0,tickLine:false,axisLine:{stroke:'var(--line)'},height:32,tickMargin:10,tick:{fill:'var(--muted)',fontSize:12}}),
    h(YAxis,{domain:[0,450],ticks:[0,100,200,300,400],width:38,tickLine:false,axisLine:false,tick:{fill:'var(--muted)',fontSize:12}}),
    h(Tooltip,{content:h(IncomeTooltip),cursor:{fill:'var(--ink)',fillOpacity:0.04},isAnimationActive:false,allowEscapeViewBox:{x:false,y:false}}),
    h(Bar,{dataKey:'grossMillion',name:'业务毛收入',fill:colors.gross,maxBarSize:28,isAnimationActive:false},
     ...query.rows.map(row=>h(Cell,{key:row.year,fill:row.complete?colors.gross:'url(#sky-ytd-gross)',stroke:row.complete?'none':colors.gross,strokeWidth:1}))),
    h(Bar,{dataKey:'afterSavingsMillion',name:'扣储蓄成本后收入',fill:colors.net,maxBarSize:28,isAnimationActive:false},
     ...query.rows.map(row=>h(Cell,{key:row.year,fill:row.complete?colors.net:'url(#sky-ytd-net)',stroke:row.complete?'none':colors.net,strokeWidth:1}))),
   )
  );
 }
 createRoot(figure.querySelector('[data-sky-annual-mount]')).render(h(Chart));
 figure.dataset.mounted='true';
})();
