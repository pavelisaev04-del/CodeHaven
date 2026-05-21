import { useState, useEffect } from "react";
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, BarChart, Bar, XAxis, Cell } from 'recharts';

const C={bg:'#040917',bgDeep:'#020610',card:'#081030',cardHi:'#0D1A48',border:'#142560',borderHi:'#2440A0',accent:'#4BC8FF',accentBg:'rgba(75,200,255,0.09)',text:'#E8F0FF',muted:'#5570A8',green:'#0FD19A',greenBg:'rgba(15,209,154,0.09)',amber:'#F5A623',amberBg:'rgba(245,166,35,0.09)',red:'#FF4060',redBg:'rgba(255,64,96,0.09)',purple:'#A78BFA',purpleBg:'rgba(167,139,250,0.09)'};
const RP={LOW:{c:C.green,bg:C.greenBg,l:'Низкий'},MEDIUM:{c:C.amber,bg:C.amberBg,l:'Средний'},HIGH:{c:C.red,bg:C.redBg,l:'Высокий'}};
const VP={APPROVED:{c:C.green,bg:C.greenBg,l:'✓ Сделка допустима',i:'✓'},CAUTION:{c:C.amber,bg:C.amberBg,l:'⚠ Требует проверки',i:'⚠'},BLOCKED:{c:C.red,bg:C.redBg,l:'✗ Сделка не рекомендована',i:'✗'}};
const ML={sanctions:'🏛 Санкционный скрининг',exportControl:'📦 Экспортный контроль',ubo:'🔗 UBO / Структура',payment:'💳 Платёжный коридор',route:'🗺 Маршрут / антиобход'};
const COUNTRIES=[{v:'CN',l:'🇨🇳 Китай'},{v:'TR',l:'🇹🇷 Турция'},{v:'AE',l:'🇦🇪 ОАЭ'},{v:'KZ',l:'🇰🇿 Казахстан'},{v:'BY',l:'🇧🇾 Беларусь'},{v:'AM',l:'🇦🇲 Армения'},{v:'GE',l:'🇬🇪 Грузия'},{v:'IN',l:'🇮🇳 Индия'},{v:'DE',l:'🇩🇪 Германия'},{v:'FR',l:'🇫🇷 Франция'},{v:'US',l:'🇺🇸 США'},{v:'GB',l:'🇬🇧 Великобритания'},{v:'IR',l:'🇮🇷 Иран'},{v:'SY',l:'🇸🇾 Сирия'},{v:'OTHER',l:'Другая страна'}];
const CURRENCIES=[{v:'CNY',l:'CNY — Юань'},{v:'TRY',l:'TRY — Лира'},{v:'AED',l:'AED — Дирхам'},{v:'USD',l:'USD — Доллар'},{v:'EUR',l:'EUR — Евро'},{v:'RUB',l:'RUB — Рубль'},{v:'INR',l:'INR — Рупия'}];
const CTYPES=[{v:'ООО',l:'ООО'},{v:'АО',l:'АО'},{v:'LLC',l:'LLC'},{v:'LTD',l:'LTD'},{v:'INC',l:'INC/Corp'},{v:'FZ',l:'Free Zone (UAE)'},{v:'OTHER',l:'Иное'}];

// ── utils ───────────────────────────────────────────────────────────────────
const parseSafe = (raw) => {
  const m = raw.match(/\{[\s\S]*\}/);
  if (!m) throw new Error('JSON не найден в ответе');
  let s = m[0];
  s = s.replace(/,(\s*[}\]])/g,'$1');       // trailing commas
  s = s.replace(/[\u0000-\u001F]/g,' ');    // control chars
  return JSON.parse(s);
};

const printDossier = (res, cr) => {
  const vp = VP[res.verdict]||VP.CAUTION;
  const rows = (arr) => arr.filter(([,v])=>v&&v!=='—').map(([k,v])=>`<tr><td style="color:#888;width:140px">${k}</td><td><b>${v}</b></td></tr>`).join('');
  const win = window.open('','_blank','width=860,height=700');
  if(!win) return;
  win.document.write(`<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><title>Досье — ${cr?.counterparty}</title>
<style>body{font-family:Arial,sans-serif;color:#222;max-width:780px;margin:0 auto;padding:40px;font-size:13px}h2{font-size:16px;margin:0 0 2px}table{width:100%;border-collapse:collapse;margin-bottom:18px}td{padding:5px 8px;border-bottom:1px solid #f0f0f0;vertical-align:top}.sec{font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px;font-weight:700;margin:20px 0 8px;border-bottom:1px solid #eee;padding-bottom:5px}.verdict{display:inline-block;padding:8px 16px;border-radius:6px;font-weight:700;font-size:14px;margin-bottom:10px}.tag{display:inline-block;padding:2px 7px;border-radius:10px;font-size:11px;margin:2px;border:1px solid currentColor}.disc{font-size:10px;color:#888;border-top:1px solid #eee;padding-top:14px;margin-top:20px;line-height:1.6}@media print{body{padding:20px}}</style>
</head><body>
<div style="display:flex;align-items:center;gap:12px;margin-bottom:20px">
<svg width="30" height="36" viewBox="0 0 280 340"><path d="M68,59 L212,59 L228,163 L140,244 L52,163Z" fill="#081030" stroke="#4BC8FF" stroke-width="4"/><line x1="140" y1="78" x2="86" y2="224" stroke="white" stroke-width="20" stroke-linecap="round"/><line x1="140" y1="78" x2="194" y2="224" stroke="white" stroke-width="20" stroke-linecap="round"/><rect x="52" y="141" width="176" height="10" fill="#4BC8FF"/></svg>
<div><h2>AEGIS COMPLY</h2><div style="color:#888;font-size:11px">Комплаенс-досье · evidence trail</div></div>
<div style="margin-left:auto;text-align:right;font-size:10px;color:#888"><div>ID: ${cr?.id}</div><div>${new Date(cr?.date||'').toLocaleString('ru-RU')}</div></div></div>
<div class="sec">Объект проверки</div>
<table>${rows([['Контрагент',cr?.counterparty],['Страна',cr?.country],['Товар',cr?.form?.product],['Код ТН ВЭД',cr?.form?.tnved||'н/у'],['Валюта / сумма',`${cr?.form?.currency||'—'} / ${cr?.form?.val||'—'}`],['Транзит',cr?.form?.transit||'прямая'],['Банк',cr?.form?.bank||'н/у'],['UBO',cr?.form?.ubo||'н/у']])}</table>
<div class="sec">Вердикт</div>
<div class="verdict" style="background:${vp.bg};color:${vp.c}">${vp.i} ${vp.l}</div>
<div style="font-size:12px;color:#555;margin-bottom:6px">${res.summary||''}</div>
<div style="font-size:11px;color:#888">Риск-скор: <b>${res.score||0}</b>/100 · Уровень: <b>${res.overall||'—'}</b></div>
${res.red_flags?.length?`<div class="sec">Риск-факторы</div>${res.red_flags.map(f=>`<div style="padding:3px 0;color:#cc3333">! ${f}</div>`).join('')}`:''}
${res.norms?.length?`<div class="sec">Применимые нормы</div><div>${res.norms.map(n=>`<span class="tag" style="color:#6644cc">§ ${n}</span>`).join('')}</div>`:''}
${res.recs?.length?`<div class="sec">Рекомендации</div>${res.recs.map((r,i)=>`<div style="padding:4px 0">${i+1}. ${r}</div>`).join('')}`:''}
<div class="disc"><b>Disclaimer:</b> Данное досье сформировано AI-агентом Aegis Comply как система поддержки принятия решений. Не является юридическим заключением. Окончательное решение принимается ответственным лицом. Human-in-the-loop. Aegis Comply © 2025.</div>
</body></html>`);
  win.document.close();
  setTimeout(()=>win.print(),600);
};

const copyDossier = (res, cr) => {
  const lines = [
    'AEGIS COMPLY — Комплаенс-досье',`ID: ${cr?.id} · ${new Date(cr?.date||'').toLocaleString('ru-RU')}`,'',
    '─ ОБЪЕКТ ПРОВЕРКИ ─',
    `Контрагент: ${cr?.counterparty}`,`Страна: ${cr?.country}`,`Товар: ${cr?.form?.product}`,
    `Вердикт: ${VP[res.verdict]?.l||res.verdict}`,`Риск-скор: ${res.score}/100`,`Уровень: ${res.overall}`,'',
    '─ РЕЗЮМЕ ─', res.summary||'','',
    ...(res.red_flags?.length?['─ РИСК-ФАКТОРЫ ─',...res.red_flags.map(f=>`! ${f}`),'']:[]),
    ...(res.norms?.length?['─ ПРИМЕНИМЫЕ НОРМЫ ─',...res.norms.map(n=>`§ ${n}`),'']:[]),
    ...(res.recs?.length?['─ РЕКОМЕНДАЦИИ ─',...res.recs.map((r,i)=>`${i+1}. ${r}`),'']:[]),
    'Aegis Comply © 2025 · Система поддержки принятия решений · Human-in-the-loop',
  ];
  navigator.clipboard?.writeText(lines.join('\n'));
};

// ── primitives ──────────────────────────────────────────────────────────────
const Shield=({size=40})=>(
  <svg width={size} height={size*1.2} viewBox="0 0 280 340">
    <defs><linearGradient id="sg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#1E3380"/><stop offset="100%" stopColor="#050B22"/></linearGradient></defs>
    <path d="M68,59 L212,59 L228,163 L140,244 L52,163Z" fill="url(#sg)" stroke={C.accent} strokeWidth="2.5"/>
    <line x1="140" y1="78" x2="86" y2="224" stroke="white" strokeWidth="18" strokeLinecap="round"/>
    <line x1="140" y1="78" x2="194" y2="224" stroke="white" strokeWidth="18" strokeLinecap="round"/>
    <rect x="52" y="141" width="176" height="10" fill={C.accent}/>
    <circle cx="52" cy="146" r="7" fill={C.accent}/><circle cx="228" cy="146" r="7" fill={C.accent}/>
  </svg>
);
const Btn=({children,onClick,v='primary',style={},disabled=false})=>{
  const s={primary:{background:`linear-gradient(135deg,#1660A0,${C.accent})`,color:'#fff',border:'none'},outline:{background:'transparent',color:C.accent,border:`1px solid ${C.accent}`},ghost:{background:'transparent',color:C.muted,border:'none'},success:{background:C.greenBg,color:C.green,border:`1px solid ${C.green}`}};
  return <button onClick={onClick} disabled={disabled} style={{padding:'9px 18px',borderRadius:8,fontWeight:600,fontSize:13,cursor:disabled?'not-allowed':'pointer',opacity:disabled?0.5:1,...(s[v]||s.primary),...style}}>{children}</button>;
};
const Card=({children,style={}})=><div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:12,padding:20,...style}}>{children}</div>;
const Badge=({level})=>{const p=RP[level]||{c:C.muted,bg:C.card,l:level||'—'};return <span style={{background:p.bg,color:p.c,border:`1px solid ${p.c}`,padding:'3px 10px',borderRadius:20,fontSize:11,fontWeight:700}}>{p.l}</span>;};
const Inp=({label,value,onChange,placeholder,type='text',req=false,hint=''})=>(
  <div style={{marginBottom:13}}>
    {label&&<label style={{display:'block',marginBottom:5,color:C.muted,fontSize:12}}>{label}{req&&<span style={{color:C.red}}> *</span>}</label>}
    <input type={type} value={value} onChange={e=>onChange(e.target.value)} placeholder={placeholder} style={{width:'100%',background:C.bgDeep,border:`1px solid ${C.border}`,borderRadius:7,padding:'9px 12px',color:C.text,fontSize:13,outline:'none',boxSizing:'border-box'}}/>
    {hint&&<div style={{fontSize:10,color:C.muted,marginTop:3}}>{hint}</div>}
  </div>
);
const Sel=({label,value,onChange,options,req=false})=>(
  <div style={{marginBottom:13}}>
    {label&&<label style={{display:'block',marginBottom:5,color:C.muted,fontSize:12}}>{label}{req&&<span style={{color:C.red}}> *</span>}</label>}
    <select value={value} onChange={e=>onChange(e.target.value)} style={{width:'100%',background:C.bgDeep,border:`1px solid ${C.border}`,borderRadius:7,padding:'9px 12px',color:value?C.text:C.muted,fontSize:13,outline:'none',boxSizing:'border-box'}}>
      <option value="">Выберите...</option>
      {options.map(o=><option key={o.v} value={o.v}>{o.l}</option>)}
    </select>
  </div>
);
const Bar=({score,color})=>(<div style={{height:5,background:C.border,borderRadius:3,marginBottom:9}}><div style={{height:5,borderRadius:3,width:`${Math.min(score,100)}%`,background:color}}/></div>);

function Toasts({toasts}){
  return(
    <div style={{position:'fixed',bottom:20,right:20,zIndex:9999,display:'flex',flexDirection:'column',gap:8,pointerEvents:'none'}}>
      {toasts.map(t=>(
        <div key={t.id} style={{background:t.t==='error'?C.redBg:t.t==='info'?C.accentBg:C.greenBg,border:`1px solid ${t.t==='error'?C.red:t.t==='info'?C.accent:C.green}`,color:t.t==='error'?C.red:t.t==='info'?C.accent:C.green,padding:'10px 16px',borderRadius:9,fontSize:12,fontWeight:600,maxWidth:300,boxShadow:'0 4px 20px rgba(0,0,0,0.4)'}}>
          {t.t==='error'?'✗':t.t==='info'?'ℹ':'✓'} {t.msg}
        </div>
      ))}
    </div>
  );
}

// ── LANDING ─────────────────────────────────────────────────────────────────
function Landing({nav}){
  const feats=[{i:'🏛',t:'Санкционный скрининг',d:'OFAC SDN/SSI, пакеты ЕС 14+, UK OFSI, UN, BIS Entity List — проверка в реальном времени'},{i:'📦',t:'Экспортный контроль',d:'ТН ВЭД, dual-use, лицензионные риски ФСТЭК, End-User Certificate, EU Reg. 2021/821'},{i:'🔗',t:'UBO / Правило 50%',d:'Анализ бенефициаров, цепочка контроля, косвенная принадлежность подсанкционным лицам'},{i:'💳',t:'Платёжный коридор',d:'Санкционный профиль банков-корреспондентов, риск блокировки, 173-ФЗ'},{i:'🗺',t:'Маршрут / антиобход',d:'Red flags транзитных юрисдикций, Shadow Fleet, Common High Priority Items'},{i:'📄',t:'Комплаенс-досье',d:'Evidence trail с печатью: нормы, источники, red flags, audit log для банка и суда'}];
  const pricing=[{n:'Старт',p:'4 900 ₽',per:'/мес',f:['5 проверок сделок','Базовый санкционный скрининг','Комплаенс-досье PDF','Email поддержка'],hi:false},{n:'Бизнес',p:'14 900 ₽',per:'/мес',f:['30 проверок сделок','Полный 6-модульный анализ','UBO и Правило 50%','Платёжный коридор и антиобход','API доступ'],hi:true},{n:'Корпоратив',p:'По запросу',per:'',f:['Безлимитные проверки','White-label решение','Интеграция с CRM/ERP','Юридическое сопровождение'],hi:false}];
  return(
    <div>
      <header style={{display:'flex',alignItems:'center',justifyContent:'space-between',padding:'14px 40px',borderBottom:`1px solid ${C.border}`,background:C.bgDeep,position:'sticky',top:0,zIndex:100}}>
        <div style={{display:'flex',alignItems:'center',gap:10}}><Shield size={24}/><span style={{fontSize:16,fontWeight:800,letterSpacing:2}}>AEGIS <span style={{color:C.accent}}>COMPLY</span></span></div>
        <div style={{display:'flex',gap:24,alignItems:'center'}}>
          {['Возможности','Тарифы','О проекте'].map(l=><span key={l} style={{color:C.muted,fontSize:13,cursor:'pointer'}}>{l}</span>)}
          <Btn onClick={()=>nav('auth')} v="outline" style={{padding:'6px 14px',fontSize:12}}>Войти</Btn>
          <Btn onClick={()=>nav('auth')} style={{padding:'6px 14px',fontSize:12}}>Попробовать</Btn>
        </div>
      </header>
      <section style={{textAlign:'center',padding:'72px 40px 56px',background:`radial-gradient(ellipse at 50% 0%,rgba(75,200,255,0.07) 0%,transparent 60%)`}}>
        <div style={{display:'inline-flex',alignItems:'center',gap:8,background:C.accentBg,border:`1px solid ${C.borderHi}`,borderRadius:20,padding:'5px 14px',marginBottom:24,fontSize:11,color:C.accent}}>
          🔐 RegTech · Двойной комплаенс · 6 модулей · Powered by AI
        </div>
        <h1 style={{fontSize:50,fontWeight:900,margin:'0 0 18px',lineHeight:1.1,background:`linear-gradient(130deg,${C.text} 50%,${C.accent})`,WebkitBackgroundClip:'text',WebkitTextFillColor:'transparent'}}>Защитите ВЭД<br/>от санкционных рисков</h1>
        <p style={{fontSize:16,color:C.muted,maxWidth:540,margin:'0 auto 36px',lineHeight:1.7}}>Первая российская RegTech-платформа, одновременно покрывающая ФЗ-183 и режимы OFAC/ЕС для МСП. End-to-end проверка с комплаенс-досье для банков.</p>
        <div style={{display:'flex',gap:12,justifyContent:'center',marginBottom:56}}>
          <Btn onClick={()=>nav('auth')} style={{padding:'12px 30px',fontSize:14}}>Проверить сделку →</Btn>
          <Btn v="outline" style={{padding:'12px 30px',fontSize:14}}>Посмотреть демо</Btn>
        </div>
        <div style={{display:'flex',justifyContent:'center',gap:44,flexWrap:'wrap',borderTop:`1px solid ${C.border}`,paddingTop:36}}>
          {[{v:'45K+',l:'МСП в ВЭД РФ'},{v:'2 000+',l:'Санкц. объектов'},{v:'6 модулей',l:'Анализ сделки'},{v:'≤10 мин',l:'На проверку'},{v:'PDF',l:'Досье для банка'}].map(s=>(
            <div key={s.l} style={{textAlign:'center'}}><div style={{fontSize:22,fontWeight:900,color:C.accent}}>{s.v}</div><div style={{fontSize:11,color:C.muted,marginTop:3}}>{s.l}</div></div>
          ))}
        </div>
      </section>
      <section style={{padding:'56px 40px',maxWidth:1100,margin:'0 auto'}}>
        <h2 style={{textAlign:'center',fontSize:28,fontWeight:800,marginBottom:8}}>End-to-end проверка сделки ВЭД</h2>
        <p style={{textAlign:'center',color:C.muted,marginBottom:36,fontSize:13}}>6 модулей — от санкционного скрининга до антиобхода и PDF-досье</p>
        <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:14}}>
          {feats.map(f=><Card key={f.t} style={{padding:22}}><div style={{fontSize:26,marginBottom:10}}>{f.i}</div><div style={{fontWeight:700,marginBottom:7,fontSize:14}}>{f.t}</div><div style={{color:C.muted,fontSize:12,lineHeight:1.6}}>{f.d}</div></Card>)}
        </div>
      </section>
      <section style={{padding:'48px 40px',background:`linear-gradient(135deg,${C.card},${C.bg})`,borderTop:`1px solid ${C.border}`,borderBottom:`1px solid ${C.border}`}}>
        <div style={{maxWidth:860,margin:'0 auto'}}>
          <h2 style={{textAlign:'center',fontSize:28,fontWeight:800,marginBottom:8}}>Правовая матрица</h2>
          <p style={{textAlign:'center',color:C.muted,marginBottom:32,fontSize:13}}>Aegis проверяет сделку одновременно по российскому и международному праву</p>
          <div style={{overflowX:'auto'}}>
            <table style={{width:'100%',borderCollapse:'collapse',fontSize:12}}>
              <thead><tr style={{borderBottom:`1px solid ${C.border}`}}>{['Российское право','Международный режим','Что проверяет Aegis'].map(h=><th key={h} style={{padding:'10px 12px',textAlign:'left',color:C.muted,fontWeight:600}}>{h}</th>)}</tr></thead>
              <tbody>{[['173-ФЗ (валютный контроль)','—','Допустимость расчётов, документы для банка, риск блокировки'],['183-ФЗ (экспортный контроль)','EU Reg. 2021/821 / BIS','Dual-use статус, лицензия ФСТЭК, End-User Certificate'],['115-ФЗ (AML/KYC)','FATF рекомендации','KYC-профиль, подозрительные транзакции'],['КоАП ст. 16.3','OFAC SDN / ЕС / UK / UN','Санкционный скрининг, Правило 50%, вторичные санкции'],['УК РФ ст. 189','OFAC / ЕС AML','Риск незаконного экспорта, dual-use + военный конечный пользователь']].map((r,i)=>(
                <tr key={i} style={{borderBottom:`1px solid ${C.border}`}}>{r.map((cell,j)=><td key={j} style={{padding:'10px 12px',color:j<2?C.muted:C.text,fontWeight:j===2?500:400}}>{cell}</td>)}</tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      </section>
      <section style={{padding:'52px 40px',maxWidth:940,margin:'0 auto'}}>
        <h2 style={{textAlign:'center',fontSize:28,fontWeight:800,marginBottom:8}}>Тарифы</h2>
        <p style={{textAlign:'center',color:C.muted,marginBottom:36,fontSize:13}}>Экспертиза уровня Big4 — по цене, доступной МСП</p>
        <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:18}}>
          {pricing.map(p=>(
            <Card key={p.n} style={{padding:26,position:'relative',border:p.hi?`2px solid ${C.accent}`:`1px solid ${C.border}`,boxShadow:p.hi?`0 0 28px ${C.accentBg}`:'none'}}>
              {p.hi&&<div style={{position:'absolute',top:-12,left:'50%',transform:'translateX(-50%)',background:C.accent,color:'#000',padding:'2px 12px',borderRadius:12,fontSize:10,fontWeight:800,whiteSpace:'nowrap'}}>ПОПУЛЯРНЫЙ</div>}
              <div style={{fontWeight:700,fontSize:16,marginBottom:6}}>{p.n}</div>
              <div style={{marginBottom:18}}><span style={{fontSize:28,fontWeight:900,color:p.hi?C.accent:C.text}}>{p.p}</span><span style={{color:C.muted,fontSize:12}}>{p.per}</span></div>
              <div style={{marginBottom:20}}>{p.f.map(f=><div key={f} style={{display:'flex',gap:7,marginBottom:8,fontSize:12}}><span style={{color:C.green,flexShrink:0}}>✓</span><span style={{color:C.muted}}>{f}</span></div>)}</div>
              <Btn onClick={()=>nav('auth')} v={p.hi?'primary':'outline'} style={{width:'100%',textAlign:'center',padding:'9px'}}>Выбрать</Btn>
            </Card>
          ))}
        </div>
      </section>
      <section style={{margin:'0 40px 56px',borderRadius:14,padding:'44px',background:`linear-gradient(135deg,${C.card},rgba(75,200,255,0.03))`,border:`1px solid ${C.borderHi}`,textAlign:'center'}}>
        <h2 style={{fontSize:26,fontWeight:800,marginBottom:8}}>Первые 3 проверки — бесплатно</h2>
        <p style={{color:C.muted,marginBottom:24,fontSize:13}}>Без привязки карты. Результат и PDF-досье за секунды.</p>
        <Btn onClick={()=>nav('auth')} style={{padding:'12px 36px',fontSize:14}}>Начать бесплатно →</Btn>
      </section>
      <footer style={{borderTop:`1px solid ${C.border}`,padding:'18px 40px',display:'flex',justifyContent:'space-between',alignItems:'center',color:C.muted,fontSize:11}}>
        <div style={{display:'flex',alignItems:'center',gap:8}}><Shield size={16}/><span>Aegis Comply © 2025 · Финуниверситет · Акселератор Legal-tech PRO</span></div>
        <div style={{display:'flex',gap:16}}>{'Политика,Условия,Контакты'.split(',').map(l=><span key={l} style={{cursor:'pointer'}}>{l}</span>)}</div>
      </footer>
    </div>
  );
}

// ── AUTH ────────────────────────────────────────────────────────────────────
function Auth({nav,setUser,toast}){
  const [mode,setMode]=useState('login');
  const [email,setEmail]=useState('');const [pass,setPass]=useState('');
  const [name,setName]=useState('');const [company,setCompany]=useState('');
  const [err,setErr]=useState('');const [loading,setLoading]=useState(false);
  const go=async()=>{
    if(!email||!pass){setErr('Заполните все поля');return;}
    setLoading(true);await new Promise(r=>setTimeout(r,600));
    setUser({name:name||email.split('@')[0],email,company:company||'Моя компания'});
    toast('Добро пожаловать!');nav('dashboard');setLoading(false);
  };
  return(
    <div style={{minHeight:'100vh',display:'flex',alignItems:'center',justifyContent:'center',background:`radial-gradient(ellipse at 50% 30%,rgba(75,200,255,0.06) 0%,transparent 65%)`}}>
      <div style={{width:380}}>
        <div style={{textAlign:'center',marginBottom:24}}><div style={{display:'flex',justifyContent:'center',marginBottom:12}}><Shield size={40}/></div><div style={{fontSize:18,fontWeight:800,letterSpacing:2}}>AEGIS <span style={{color:C.accent}}>COMPLY</span></div><div style={{color:C.muted,marginTop:6,fontSize:12}}>{mode==='login'?'Войдите в аккаунт':'Создайте аккаунт'}</div></div>
        <Card style={{padding:26}}>
          {mode==='register'&&<><Inp label="Имя" value={name} onChange={setName} placeholder="Иван Петров"/><Inp label="Компания" value={company} onChange={setCompany} placeholder="ООО Торговая компания"/></>}
          <Inp label="Email" value={email} onChange={setEmail} placeholder="ivan@company.ru" type="email" req/>
          <Inp label="Пароль" value={pass} onChange={setPass} placeholder="••••••••" type="password" req/>
          {err&&<div style={{color:C.red,fontSize:11,marginBottom:12}}>{err}</div>}
          <Btn onClick={go} disabled={loading} style={{width:'100%',padding:'11px',textAlign:'center',marginBottom:12}}>{loading?'Подождите...':(mode==='login'?'Войти':'Зарегистрироваться')}</Btn>
          <div style={{textAlign:'center',fontSize:11,color:C.muted}}>{mode==='login'?'Нет аккаунта? ':'Есть аккаунт? '}<span onClick={()=>setMode(m=>m==='login'?'register':'login')} style={{color:C.accent,cursor:'pointer',fontWeight:600}}>{mode==='login'?'Создать':'Войти'}</span></div>
        </Card>
        <div style={{textAlign:'center',marginTop:14}}><span onClick={()=>nav('landing')} style={{color:C.muted,fontSize:11,cursor:'pointer'}}>← На главную</span></div>
      </div>
    </div>
  );
}

// ── SHELL ───────────────────────────────────────────────────────────────────
function Shell({user,view,nav,logout,children}){
  const items=[{id:'dashboard',i:'⊞',l:'Обзор'},{id:'check',i:'🔍',l:'Новая проверка'},{id:'history',i:'📋',l:'История'},{id:'settings',i:'⚙',l:'Настройки'}];
  return(
    <div style={{display:'flex',minHeight:'100vh'}}>
      <div style={{width:206,background:C.bgDeep,borderRight:`1px solid ${C.border}`,display:'flex',flexDirection:'column',flexShrink:0,position:'sticky',top:0,height:'100vh'}}>
        <div style={{padding:'16px 16px 14px',borderBottom:`1px solid ${C.border}`,display:'flex',alignItems:'center',gap:8}}><Shield size={19}/><span style={{fontSize:12,fontWeight:800,letterSpacing:1.5}}>AEGIS <span style={{color:C.accent}}>COMPLY</span></span></div>
        <div style={{flex:1,padding:'12px 8px'}}>
          {items.map(it=>(
            <div key={it.id} onClick={()=>nav(it.id)} style={{display:'flex',alignItems:'center',gap:9,padding:'9px 10px',borderRadius:7,cursor:'pointer',marginBottom:2,fontSize:12,background:view===it.id?C.accentBg:'transparent',color:view===it.id?C.accent:C.muted,fontWeight:view===it.id?600:400,border:view===it.id?`1px solid ${C.borderHi}`:'1px solid transparent'}}>
              <span>{it.i}</span>{it.l}
            </div>
          ))}
        </div>
        <div style={{padding:'12px 16px',borderTop:`1px solid ${C.border}`}}>
          <div style={{fontSize:11,marginBottom:1,fontWeight:600,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{user.name}</div>
          <div style={{fontSize:10,color:C.muted,marginBottom:9,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{user.company}</div>
          <span onClick={logout} style={{fontSize:10,color:C.muted,cursor:'pointer'}}>Выйти →</span>
        </div>
      </div>
      <div style={{flex:1,overflow:'auto',minWidth:0}}>{children}</div>
    </div>
  );
}

// ── DASHBOARD ───────────────────────────────────────────────────────────────
function Dashboard({nav,history,user}){
  const total=history.length,highs=history.filter(h=>h.result?.overall==='HIGH').length,appr=history.filter(h=>h.result?.verdict==='APPROVED').length,caut=history.filter(h=>h.result?.verdict==='CAUTION').length;
  const chartData=history.slice(0,7).reverse().map((h,i)=>({name:`#${i+1}`,score:h.result?.score||0,color:h.result?.overall==='HIGH'?C.red:h.result?.overall==='MEDIUM'?C.amber:C.green}));
  return(
    <div style={{padding:28}}>
      <h1 style={{fontSize:20,fontWeight:800,marginBottom:3}}>Добро пожаловать, {user.name} 👋</h1>
      <p style={{color:C.muted,marginBottom:24,fontSize:13}}>Панель управления комплаенс-проверками</p>
      <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:12,marginBottom:22}}>
        {[{l:'Всего проверок',v:total,c:C.accent},{l:'Высокий риск',v:highs,c:C.red},{l:'Одобрено',v:appr,c:C.green},{l:'На проверке',v:caut,c:C.amber}].map(s=>(
          <Card key={s.l} style={{padding:16}}><div style={{fontSize:28,fontWeight:900,color:s.c,marginBottom:3}}>{s.v}</div><div style={{fontSize:11,color:C.muted}}>{s.l}</div></Card>
        ))}
      </div>
      <div style={{display:'grid',gridTemplateColumns:'2fr 1fr',gap:16,marginBottom:20}}>
        <Card style={{padding:22,background:`linear-gradient(135deg,${C.card},rgba(75,200,255,0.04))`,border:`1px solid ${C.borderHi}`}}>
          <div style={{fontSize:30,marginBottom:8}}>🔍</div>
          <h2 style={{fontSize:17,fontWeight:800,marginBottom:6}}>Новая проверка сделки</h2>
          <p style={{color:C.muted,marginBottom:16,fontSize:12,lineHeight:1.6}}>6 модулей: контрагент · товар · UBO · платёж · маршрут · PDF-досье</p>
          <Btn onClick={()=>nav('check')} style={{padding:'10px 24px'}}>Начать проверку →</Btn>
        </Card>
        <Card style={{padding:18}}>
          <div style={{fontWeight:700,marginBottom:12,fontSize:13}}>Модули анализа</div>
          {[['🏛','Санкц. скрининг'],['📦','Экспортный контроль'],['🔗','UBO / Правило 50%'],['💳','Платёжный коридор'],['🗺','Маршрут / антиобход']].map(([ic,l])=>(
            <div key={l} style={{display:'flex',gap:8,alignItems:'center',padding:'5px 0',borderBottom:`1px solid ${C.border}`,fontSize:12}}>
              <span>{ic}</span><span style={{color:C.muted}}>{l}</span><span style={{marginLeft:'auto',color:C.green,fontSize:10}}>✓</span>
            </div>
          ))}
        </Card>
      </div>
      {chartData.length>0&&(
        <Card style={{padding:18,marginBottom:16}}>
          <div style={{fontWeight:700,fontSize:13,marginBottom:14}}>Риск-скор последних проверок</div>
          <ResponsiveContainer width="100%" height={100}>
            <BarChart data={chartData} margin={{top:0,right:0,left:0,bottom:0}}>
              <XAxis dataKey="name" tick={{fontSize:10,fill:C.muted}} axisLine={false} tickLine={false}/>
              <Bar dataKey="score" radius={[4,4,0,0]}>
                {chartData.map((e,i)=><Cell key={i} fill={e.color}/>)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}
      {history.length>0&&(
        <div>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:12}}>
            <h3 style={{fontWeight:700,fontSize:14}}>Последние проверки</h3>
            <span onClick={()=>nav('history')} style={{color:C.accent,fontSize:11,cursor:'pointer'}}>Все →</span>
          </div>
          {history.slice(0,4).map((h,i)=>(
            <Card key={i} style={{marginBottom:7,padding:12,display:'flex',justifyContent:'space-between',alignItems:'center'}}>
              <div><div style={{fontWeight:600,fontSize:13,marginBottom:2}}>{h.counterparty}</div><div style={{fontSize:10,color:C.muted}}>{h.country} · {(h.product||'').slice(0,48)}</div></div>
              <div style={{display:'flex',gap:7,alignItems:'center'}}><Badge level={h.result?.overall}/><span style={{fontSize:9,color:C.muted}}>{new Date(h.date).toLocaleDateString('ru-RU')}</span></div>
            </Card>
          ))}
        </div>
      )}
      {!history.length&&<Card style={{textAlign:'center',padding:32}}><div style={{fontSize:36,marginBottom:12}}>📋</div><div style={{color:C.muted,fontSize:12}}>Проверок пока нет — начните с первой сделки</div></Card>}
    </div>
  );
}

// ── CHECK FORM ──────────────────────────────────────────────────────────────
function CheckForm({nav,setResult,addToHistory,toast,prefillForm,clearPrefill}){
  const [step,setStep]=useState(1);
  const [f,setF]=useState({cp:'',country:'',ctype:'',reg:'',product:'',tnved:'',dual:'',enduse:'',ubo:'',uboCountry:'',ownership:'',currency:'',val:'',bank:'',payMethod:'',transit:'',vessel:'',finalDest:''});
  const [err,setErr]=useState('');const [loading,setLoading]=useState(false);
  const [loadStep,setLoadStep]=useState(-1);
  useEffect(()=>{if(prefillForm){setF({...prefillForm});clearPrefill?.();toast('Данные предыдущей проверки загружены','info');}},[]); // eslint-disable-line
  const upd=(k,v)=>setF(p=>({...p,[k]:v}));
  const STEPS=[{n:1,l:'Контрагент'},{n:2,l:'Товар'},{n:3,l:'Структура'},{n:4,l:'Платёж'},{n:5,l:'Маршрут'},{n:6,l:'Итог'}];
  const LSTEPS=['🏛 Санкционные списки OFAC / ЕС / UK / UN','📦 Экспортный контроль ФЗ-183 / ТН ВЭД','🔗 Структура бенефициаров / Правило 50%','💳 Платёжный коридор и банки','🗺 Маршрут / антиобход санкций'];

  const analyze=async()=>{
    setLoading(true);setErr('');setLoadStep(0);
    LSTEPS.forEach((_,i)=>setTimeout(()=>setLoadStep(i),i*900));
    try{
      const resp=await fetch("https://api.anthropic.com/v1/messages",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          model:"claude-sonnet-4-20250514",max_tokens:2048,
          system:`You are Aegis Comply AI — compliance engine for Russian double compliance.
RULES: 1) Respond ONLY with JSON. 2) ALL text in Russian. 3) Keep each finding/flag/rec under 12 words. 4) No quotes inside text values. 5) No markdown, no backticks, no preamble.`,
          messages:[{role:"user",content:`Analyze for compliance. Respond ONLY with this JSON (Russian text, short phrases):
{"overall":"HIGH","score":75,"verdict":"BLOCKED","summary":"Two sentence summary","red_flags":["flag1","flag2","flag3"],"norms":["OFAC SDN","ФЗ-183","EU Reg 833/2014"],"modules":{"sanctions":{"risk":"HIGH","score":80,"findings":["finding1","finding2"]},"exportControl":{"risk":"MEDIUM","score":55,"findings":["finding1","finding2"]},"ubo":{"risk":"LOW","score":20,"findings":["finding1"]},"payment":{"risk":"HIGH","score":75,"findings":["finding1","finding2"]},"route":{"risk":"MEDIUM","score":50,"findings":["finding1"]}},"recs":["rec1","rec2","rec3"]}
Data: Counterparty=${f.cp}, Country=${f.country}, Type=${f.ctype||'n/a'}, Reg=${f.reg||'n/a'}, Product=${f.product}, HS=${f.tnved||'n/a'}, DualUse=${f.dual||'unknown'}, Enduse=${f.enduse||'n/a'}, UBO=${f.ubo||'n/a'}, UBOCountry=${f.uboCountry||'n/a'}, Ownership=${f.ownership||'n/a'}%, Currency=${f.currency||'n/a'}, Value=${f.val||'n/a'}, Bank=${f.bank||'n/a'}, Payment=${f.payMethod||'n/a'}, Transit=${f.transit||'direct'}, Vessel=${f.vessel||'n/a'}, FinalDest=${f.finalDest||f.country}`}]
        })
      });
      const data=await resp.json();
      const raw=data.content?.map(b=>b.type==='text'?b.text:'').join('').trim()||'';
      const res=parseSafe(raw);
      const rec={id:Date.now(),counterparty:f.cp,country:f.country,product:f.product,currency:f.currency,date:new Date().toISOString(),result:res,form:{...f}};
      addToHistory(rec);setResult({...res,checkRecord:rec});
      toast('Проверка завершена');nav('result');
    }catch(e){setErr('Ошибка: '+(e.message||'попробуйте снова'));toast('Ошибка анализа','error');}
    setLoading(false);setLoadStep(-1);
  };

  const next=()=>{
    if(step===1&&!f.cp){setErr('Введите контрагента');return;}
    if(step===1&&!f.country){setErr('Выберите страну');return;}
    if(step===2&&!f.product){setErr('Введите товар');return;}
    setErr('');setStep(s=>s+1);
  };

  return(
    <div style={{padding:28,maxWidth:640}}>
      <span onClick={()=>nav('dashboard')} style={{color:C.muted,cursor:'pointer',fontSize:11,display:'block',marginBottom:7}}>← Назад</span>
      <h1 style={{fontSize:20,fontWeight:800,marginBottom:3}}>Новая проверка сделки</h1>
      <p style={{color:C.muted,marginBottom:22,fontSize:12}}>6-модульный AI-анализ двойного комплаенса · PDF-досье</p>
      <div style={{display:'flex',gap:4,marginBottom:20}}>
        {STEPS.map(s=>(
          <div key={s.n} style={{flex:1,textAlign:'center',padding:'6px 3px',borderRadius:7,fontSize:10,background:step===s.n?C.accentBg:step>s.n?C.greenBg:C.card,border:`1px solid ${step===s.n?C.accent:step>s.n?C.green:C.border}`,color:step===s.n?C.accent:step>s.n?C.green:C.muted,fontWeight:step===s.n?700:400}}>
            <div style={{fontWeight:700,marginBottom:1}}>{step>s.n?'✓':`0${s.n}`}</div>{s.l}
          </div>
        ))}
      </div>
      <Card style={{padding:22}}>
        {step===1&&<div>
          <div style={{fontWeight:700,marginBottom:14,fontSize:14}}>① Данные контрагента</div>
          <Inp label="Наименование контрагента" value={f.cp} onChange={v=>upd('cp',v)} placeholder="HUAWEI TECHNOLOGIES CO., LTD." req/>
          <Sel label="Страна регистрации" value={f.country} onChange={v=>upd('country',v)} options={COUNTRIES} req/>
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:10}}>
            <Sel label="Тип юр. лица" value={f.ctype} onChange={v=>upd('ctype',v)} options={CTYPES}/>
            <Inp label="Рег. номер / ИНН" value={f.reg} onChange={v=>upd('reg',v)} placeholder="Номер в реестре"/>
          </div>
        </div>}
        {step===2&&<div>
          <div style={{fontWeight:700,marginBottom:14,fontSize:14}}>② Товар / Технология</div>
          <Inp label="Описание товара" value={f.product} onChange={v=>upd('product',v)} placeholder="Промышленные микропроцессоры Intel Xeon 64-бит" req/>
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:10}}>
            <Inp label="Код ТН ВЭД" value={f.tnved} onChange={v=>upd('tnved',v)} placeholder="8542310000" hint="10-значный код"/>
            <Sel label="Двойное назначение" value={f.dual} onChange={v=>upd('dual',v)} options={[{v:'NO',l:'Нет — гражданское'},{v:'POSSIBLE',l:'Возможно — уточнить'},{v:'YES',l:'Да — двойное'}]}/>
          </div>
          <Inp label="Конечное использование / пользователь" value={f.enduse} onChange={v=>upd('enduse',v)} placeholder="Гражданское производство / телеком / оборонный сектор"/>
        </div>}
        {step===3&&<div>
          <div style={{fontWeight:700,marginBottom:4,fontSize:14}}>③ Корпоративная структура / UBO</div>
          <div style={{color:C.muted,fontSize:11,marginBottom:12}}>Правило 50% OFAC — если подсанкционное лицо владеет ≥50%, компания считается подсанкционной</div>
          <Inp label="Бенефициарный владелец (UBO)" value={f.ubo} onChange={v=>upd('ubo',v)} placeholder="ФИО или наименование холдинга"/>
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:10}}>
            <Sel label="Страна UBO" value={f.uboCountry} onChange={v=>upd('uboCountry',v)} options={COUNTRIES}/>
            <Inp label="Доля участия (%)" value={f.ownership} onChange={v=>upd('ownership',v)} placeholder="Например: 75"/>
          </div>
        </div>}
        {step===4&&<div>
          <div style={{fontWeight:700,marginBottom:4,fontSize:14}}>④ Платёжный коридор</div>
          <div style={{color:C.muted,fontSize:11,marginBottom:12}}>Риск блокировки банком-корреспондентом — ключевой фактор вторичных санкций</div>
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:10}}>
            <Sel label="Валюта расчёта" value={f.currency} onChange={v=>upd('currency',v)} options={CURRENCIES}/>
            <Inp label="Сумма сделки" value={f.val} onChange={v=>upd('val',v)} placeholder="50 000 USD"/>
          </div>
          <Inp label="Банк для расчётов" value={f.bank} onChange={v=>upd('bank',v)} placeholder="DenizBank, Промсвязьбанк, ВТБ..."/>
          <Sel label="Способ расчёта" value={f.payMethod} onChange={v=>upd('payMethod',v)} options={[{v:'SWIFT',l:'SWIFT'},{v:'SPFS',l:'СПФС'},{v:'CIPS',l:'CIPS (Китай)'},{v:'LC',l:'Аккредитив (L/C)'},{v:'ADVANCE',l:'Авансовый платёж'},{v:'CRYPTO',l:'Крипто/иное'}]}/>
        </div>}
        {step===5&&<div>
          <div style={{fontWeight:700,marginBottom:4,fontSize:14}}>⑤ Маршрут / Антиобход санкций</div>
          <div style={{color:C.muted,fontSize:11,marginBottom:12}}>Транзитные юрисдикции — главный red flag при проверках ЕС/США на антиобход</div>
          <Inp label="Транзитные страны / маршрут" value={f.transit} onChange={v=>upd('transit',v)} placeholder="Турция → ОАЭ → Казахстан"/>
          <Inp label="Перевозчик / судно / логист" value={f.vessel} onChange={v=>upd('vessel',v)} placeholder="Название судна, авиаперевозчик..."/>
          <Sel label="Страна конечного назначения" value={f.finalDest} onChange={v=>upd('finalDest',v)} options={COUNTRIES}/>
          <div style={{background:C.bgDeep,borderRadius:7,padding:'9px 12px',fontSize:11,color:C.muted,borderLeft:`3px solid ${C.red}`}}>🚩 Common High Priority Items: товары требуют усиленной проверки конечного пользователя</div>
        </div>}
        {step===6&&<div>
          <div style={{fontWeight:700,marginBottom:12,fontSize:14}}>⑥ Подтвердите данные</div>
          <div style={{background:C.bgDeep,borderRadius:8,padding:14,marginBottom:14}}>
            {[['Контрагент',f.cp],['Страна',COUNTRIES.find(c=>c.v===f.country)?.l||f.country],['Тип / рег.',`${f.ctype||'—'} / ${f.reg||'—'}`],['Товар',f.product],['ТН ВЭД',f.tnved||'—'],['Двойн. назнач.',f.dual||'—'],['UBO',f.ubo||'—'],['Доля UBO',f.ownership?f.ownership+'%':'—'],['Валюта / сумма',`${f.currency||'—'} / ${f.val||'—'}`],['Банк',f.bank||'—'],['Способ расчёта',f.payMethod||'—'],['Транзит',f.transit||'прямая'],['Перевозчик',f.vessel||'—']].filter(([,v])=>v&&v!=='—').map(([k,v])=>(
              <div key={k} style={{display:'flex',justifyContent:'space-between',padding:'5px 0',borderBottom:`1px solid ${C.border}`,fontSize:12}}>
                <span style={{color:C.muted,flexShrink:0}}>{k}</span>
                <span style={{fontWeight:600,maxWidth:260,textAlign:'right',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',marginLeft:8}}>{v}</span>
              </div>
            ))}
          </div>
          {err&&<div style={{color:C.red,fontSize:11,marginBottom:12,padding:'8px 10px',background:C.redBg,borderRadius:6}}>{err}</div>}
        </div>}
        <div style={{display:'flex',justifyContent:'space-between',marginTop:16}}>
          <Btn onClick={()=>step>1?setStep(s=>s-1):nav('dashboard')} v="ghost" style={{fontSize:12}}>← Назад</Btn>
          {step<6?<Btn onClick={next} style={{fontSize:12}}>Далее →</Btn>:<Btn onClick={analyze} disabled={loading} style={{minWidth:150,textAlign:'center',fontSize:12}}>{loading?'🔄 Анализирую...':'🛡 Запустить проверку'}</Btn>}
        </div>
      </Card>
      {loading&&(
        <Card style={{marginTop:14,padding:24,border:`1px solid ${C.borderHi}`}}>
          <div style={{textAlign:'center',marginBottom:14}}><div style={{fontSize:30,marginBottom:6}}>🛡</div><div style={{fontWeight:700,fontSize:14}}>AI анализирует сделку...</div></div>
          <div style={{display:'flex',flexDirection:'column',gap:6}}>
            {LSTEPS.map((l,i)=>(
              <div key={i} style={{display:'flex',gap:8,alignItems:'center',fontSize:12,padding:'6px 10px',borderRadius:6,background:loadStep>=i?C.accentBg:'transparent',border:`1px solid ${loadStep>=i?C.borderHi:C.border}`,transition:'all 0.4s'}}>
                <span style={{color:loadStep>i?C.green:loadStep===i?C.accent:C.muted,fontSize:14}}>{loadStep>i?'✓':loadStep===i?'⟳':'○'}</span>
                <span style={{color:loadStep>=i?C.text:C.muted}}>{l}</span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

// ── RESULT ──────────────────────────────────────────────────────────────────
function Result({nav,result,toast}){
  const [tab,setTab]=useState('analysis');
  const vp=VP[result.verdict]||VP.CAUTION;
  const sc=s=>s<30?C.green:s<60?C.amber:C.red;
  const cr=result.checkRecord;
  const date=cr?new Date(cr.date).toLocaleString('ru-RU'):'—';
  const radarData=Object.entries(result.modules||{}).map(([k,m])=>({subject:{sanctions:'Санкции',exportControl:'Экспорт',ubo:'UBO',payment:'Платёж',route:'Маршрут'}[k]||k,score:m.score||0,fullMark:100}));

  return(
    <div style={{padding:28,maxWidth:820}}>
      <span onClick={()=>nav('dashboard')} style={{color:C.muted,cursor:'pointer',fontSize:11,display:'block',marginBottom:7}}>← К обзору</span>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',flexWrap:'wrap',gap:10,marginBottom:18}}>
        <div><h1 style={{fontSize:20,fontWeight:800,marginBottom:3}}>Результат проверки</h1><p style={{color:C.muted,fontSize:12,margin:0}}>{cr?.counterparty} · {cr?.country} · {date}</p></div>
        <div style={{display:'flex',gap:6,flexWrap:'wrap'}}>
          <Btn onClick={()=>nav('check')} style={{fontSize:11,padding:'7px 12px'}}>+ Новая</Btn>
          <Btn onClick={()=>{copyDossier(result,cr);toast('Скопировано в буфер','info');}} v="outline" style={{fontSize:11,padding:'7px 12px'}}>📋 Копировать</Btn>
          <Btn onClick={()=>printDossier(result,cr)} v="success" style={{fontSize:11,padding:'7px 12px'}}>🖨 Печать PDF</Btn>
        </div>
      </div>

      <Card style={{padding:22,marginBottom:14,border:`2px solid ${vp.c}`,background:vp.bg}}>
        <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',flexWrap:'wrap',gap:14}}>
          <div style={{flex:1}}>
            <div style={{fontSize:22,fontWeight:900,color:vp.c,marginBottom:6}}>{vp.l}</div>
            <p style={{color:C.muted,fontSize:13,lineHeight:1.6,maxWidth:480,margin:0}}>{result.summary}</p>
          </div>
          <div style={{textAlign:'center',flexShrink:0}}>
            <div style={{width:70,height:70,borderRadius:'50%',border:`4px solid ${sc(result.score||0)}`,display:'flex',alignItems:'center',justifyContent:'center',flexDirection:'column',margin:'0 auto 7px'}}>
              <div style={{fontSize:20,fontWeight:900,color:sc(result.score||0)}}>{result.score||0}</div>
              <div style={{fontSize:9,color:C.muted}}>риск</div>
            </div>
            <Badge level={result.overall}/>
          </div>
        </div>
      </Card>

      {(result.red_flags?.length>0||result.norms?.length>0)&&(
        <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12,marginBottom:14}}>
          {result.red_flags?.length>0&&(
            <Card style={{padding:14}}>
              <div style={{fontWeight:700,fontSize:11,marginBottom:8,color:C.red}}>🚩 Red flags</div>
              {result.red_flags.map((f,i)=><div key={i} style={{fontSize:11,color:C.muted,padding:'3px 0',borderBottom:`1px solid ${C.border}`,display:'flex',gap:5}}><span style={{color:C.red,flexShrink:0}}>!</span>{f}</div>)}
            </Card>
          )}
          {result.norms?.length>0&&(
            <Card style={{padding:14}}>
              <div style={{fontWeight:700,fontSize:11,marginBottom:8,color:C.purple}}>📐 Применимые нормы</div>
              {result.norms.map((n,i)=><div key={i} style={{fontSize:11,color:C.muted,padding:'3px 0',borderBottom:`1px solid ${C.border}`,display:'flex',gap:5}}><span style={{color:C.purple,flexShrink:0}}>§</span>{n}</div>)}
            </Card>
          )}
        </div>
      )}

      <div style={{display:'flex',gap:4,marginBottom:12}}>
        {[{id:'analysis',l:'Детальный анализ'},{id:'radar',l:'Визуализация рисков'},{id:'dossier',l:'Комплаенс-досье'}].map(t=>(
          <div key={t.id} onClick={()=>setTab(t.id)} style={{padding:'7px 14px',borderRadius:7,cursor:'pointer',fontSize:12,fontWeight:tab===t.id?700:400,background:tab===t.id?C.accentBg:C.card,color:tab===t.id?C.accent:C.muted,border:`1px solid ${tab===t.id?C.borderHi:C.border}`}}>{t.l}</div>
        ))}
      </div>

      {tab==='analysis'&&(
        <>
          <div style={{display:'grid',gridTemplateColumns:'repeat(2,1fr)',gap:12,marginBottom:14}}>
            {Object.entries(result.modules||{}).map(([k,m])=>{
              const col=sc(m.score||0);
              return(
                <Card key={k} style={{padding:16}}>
                  <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:8}}><div style={{fontWeight:700,fontSize:11}}>{ML[k]||k}</div><Badge level={m.risk}/></div>
                  <Bar score={m.score||0} color={col}/>
                  {(m.findings||[]).map((fd,i)=>(
                    <div key={i} style={{fontSize:11,color:C.muted,padding:'2px 0',display:'flex',gap:5,lineHeight:1.4}}>
                      <span style={{color:m.risk==='HIGH'?C.red:m.risk==='MEDIUM'?C.amber:C.green,flexShrink:0}}>{m.risk==='HIGH'?'⚠':m.risk==='MEDIUM'?'→':'✓'}</span>{fd}
                    </div>
                  ))}
                </Card>
              );
            })}
          </div>
          {(result.recs||[]).length>0&&(
            <Card style={{padding:18,marginBottom:14}}>
              <div style={{fontWeight:700,fontSize:13,marginBottom:12}}>💡 Рекомендации</div>
              {result.recs.map((r,i)=><div key={i} style={{padding:'8px 12px',background:C.bgDeep,borderRadius:7,marginBottom:7,borderLeft:`3px solid ${C.accent}`,fontSize:12,color:C.muted,lineHeight:1.5}}>{i+1}. {r}</div>)}
            </Card>
          )}
        </>
      )}

      {tab==='radar'&&(
        <Card style={{padding:22,marginBottom:14}}>
          <div style={{fontWeight:700,fontSize:13,marginBottom:4}}>Профиль рисков по модулям</div>
          <div style={{color:C.muted,fontSize:11,marginBottom:16}}>Чем больше площадь — тем выше совокупный риск сделки</div>
          <ResponsiveContainer width="100%" height={280}>
            <RadarChart data={radarData} margin={{top:10,right:30,bottom:10,left:30}}>
              <PolarGrid stroke={C.border}/>
              <PolarAngleAxis dataKey="subject" tick={{fill:C.muted,fontSize:12}}/>
              <Radar name="Риск" dataKey="score" stroke={C.red} fill={C.red} fillOpacity={0.25} strokeWidth={2}/>
            </RadarChart>
          </ResponsiveContainer>
          <div style={{display:'grid',gridTemplateColumns:'repeat(5,1fr)',gap:8,marginTop:8}}>
            {radarData.map(d=>(
              <div key={d.subject} style={{textAlign:'center'}}>
                <div style={{fontSize:16,fontWeight:900,color:sc(d.score)}}>{d.score}</div>
                <div style={{fontSize:10,color:C.muted}}>{d.subject}</div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {tab==='dossier'&&(
        <Card style={{padding:22,marginBottom:14}}>
          <div style={{borderBottom:`1px solid ${C.border}`,paddingBottom:14,marginBottom:16}}>
            <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
              <div style={{display:'flex',alignItems:'center',gap:10}}><Shield size={22}/><div><div style={{fontSize:13,fontWeight:800,letterSpacing:1}}>AEGIS COMPLY</div><div style={{fontSize:10,color:C.muted}}>Комплаенс-досье · evidence trail</div></div></div>
              <div style={{textAlign:'right',fontSize:10,color:C.muted}}><div>ID: {cr?.id}</div><div>{date}</div></div>
            </div>
          </div>
          <div style={{marginBottom:14}}>
            <div style={{fontSize:10,color:C.muted,marginBottom:8,fontWeight:700,textTransform:'uppercase',letterSpacing:1}}>Объект проверки</div>
            {[['Контрагент',cr?.counterparty],['Страна',cr?.country],['Товар',cr?.form?.product],['ТН ВЭД',cr?.form?.tnved||'н/у'],['Валюта / сумма',`${cr?.form?.currency||'—'} / ${cr?.form?.val||'—'}`],['Транзит',cr?.form?.transit||'прямая'],['Банк',cr?.form?.bank||'н/у'],['UBO',cr?.form?.ubo||'н/у']].map(([k,v])=>v&&(
              <div key={k} style={{display:'flex',gap:10,padding:'5px 0',borderBottom:`1px solid ${C.border}`,fontSize:11}}><span style={{color:C.muted,minWidth:90,flexShrink:0}}>{k}</span><span style={{fontWeight:500}}>{v}</span></div>
            ))}
          </div>
          <div style={{marginBottom:14}}>
            <div style={{fontSize:10,color:C.muted,marginBottom:8,fontWeight:700,textTransform:'uppercase',letterSpacing:1}}>Вердикт</div>
            <div style={{display:'inline-flex',alignItems:'center',gap:8,background:vp.bg,border:`1px solid ${vp.c}`,borderRadius:8,padding:'8px 14px'}}>
              <span style={{fontSize:18,color:vp.c}}>{vp.i}</span><span style={{fontWeight:700,color:vp.c,fontSize:13}}>{vp.l}</span><span style={{color:C.muted,fontSize:11}}>· Скор: {result.score||0}/100</span>
            </div>
          </div>
          {result.red_flags?.length>0&&<div style={{marginBottom:14}}><div style={{fontSize:10,color:C.muted,marginBottom:8,fontWeight:700,textTransform:'uppercase',letterSpacing:1}}>Риск-факторы</div>{result.red_flags.map((f,i)=><div key={i} style={{fontSize:11,padding:'4px 0',color:C.text}}>• {f}</div>)}</div>}
          {result.norms?.length>0&&<div style={{marginBottom:14}}><div style={{fontSize:10,color:C.muted,marginBottom:8,fontWeight:700,textTransform:'uppercase',letterSpacing:1}}>Применимые нормы</div><div style={{display:'flex',flexWrap:'wrap',gap:5}}>{result.norms.map((n,i)=><span key={i} style={{background:C.purpleBg,color:C.purple,border:`1px solid ${C.purple}`,padding:'2px 8px',borderRadius:12,fontSize:10}}>§ {n}</span>)}</div></div>}
          {result.recs?.length>0&&<div style={{marginBottom:14}}><div style={{fontSize:10,color:C.muted,marginBottom:8,fontWeight:700,textTransform:'uppercase',letterSpacing:1}}>Рекомендации</div>{result.recs.map((r,i)=><div key={i} style={{fontSize:11,padding:'3px 0',color:C.muted}}>• {r}</div>)}</div>}
          <div style={{borderTop:`1px solid ${C.border}`,paddingTop:12,fontSize:10,color:C.muted,lineHeight:1.6}}><strong style={{color:C.text}}>Disclaimer:</strong> Сформировано AI-агентом Aegis Comply как система поддержки принятия решений. Не является юридическим заключением. Принцип human-in-the-loop соблюдён. Aegis Comply © 2025.</div>
        </Card>
      )}
    </div>
  );
}

// ── HISTORY ─────────────────────────────────────────────────────────────────
function History({nav,history,setResult,toast}){
  const [filter,setFilter]=useState('ALL');
  const filtered=filter==='ALL'?history:history.filter(h=>h.result?.overall===filter);
  return(
    <div style={{padding:28}}>
      <h1 style={{fontSize:20,fontWeight:800,marginBottom:3}}>История проверок</h1>
      <p style={{color:C.muted,marginBottom:18,fontSize:12}}>Все комплаенс-проверки · {history.length} записей</p>
      <div style={{display:'flex',gap:6,marginBottom:16}}>
        {['ALL','LOW','MEDIUM','HIGH'].map(f=>(
          <div key={f} onClick={()=>setFilter(f)} style={{padding:'5px 12px',borderRadius:20,cursor:'pointer',fontSize:11,fontWeight:600,background:filter===f?(f==='ALL'?C.accentBg:RP[f]?.bg||C.accentBg):C.card,color:filter===f?(f==='ALL'?C.accent:RP[f]?.c||C.accent):C.muted,border:`1px solid ${filter===f?(f==='ALL'?C.accent:RP[f]?.c||C.accent):C.border}`}}>
            {f==='ALL'?'Все':RP[f]?.l||f}
          </div>
        ))}
      </div>
      {!filtered.length?(<Card style={{textAlign:'center',padding:40}}><div style={{fontSize:36,marginBottom:12}}>📋</div><div style={{color:C.muted,marginBottom:18,fontSize:12}}>{history.length?'Нет проверок с таким фильтром':'Проверок пока нет'}</div><Btn onClick={()=>nav('check')}>Начать проверку</Btn></Card>):(
        filtered.map((h,i)=>{
          const vp=VP[h.result?.verdict]||VP.CAUTION;
          return(
            <Card key={i} style={{marginBottom:8,padding:16}}>
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',flexWrap:'wrap',gap:8}}>
                <div style={{flex:1,minWidth:180}}>
                  <div style={{fontWeight:700,marginBottom:2,fontSize:13}}>{h.counterparty}</div>
                  <div style={{fontSize:11,color:C.muted,marginBottom:3}}>{h.country} · {(h.product||'').slice(0,55)}{(h.product||'').length>55?'...':''}</div>
                  <div style={{fontSize:10,color:C.muted}}>{new Date(h.date).toLocaleString('ru-RU')}</div>
                </div>
                <div style={{display:'flex',gap:6,alignItems:'center',flexWrap:'wrap'}}>
                  <Badge level={h.result?.overall}/>
                  <span style={{fontSize:11,color:vp.c,fontWeight:600}}>{vp.i} {h.result?.verdict}</span>
                  <Btn onClick={()=>{setResult({...h.result,checkRecord:h});nav('result');}} v="outline" style={{padding:'4px 10px',fontSize:10}}>Открыть</Btn>
                  <Btn onClick={()=>{printDossier(h.result,h);toast('Открываем печать...','info');}} v="ghost" style={{padding:'4px 8px',fontSize:10}}>🖨</Btn>
                </div>
              </div>
            </Card>
          );
        })
      )}
    </div>
  );
}

// ── SETTINGS ────────────────────────────────────────────────────────────────
function Settings({user,setUser,toast}){
  const [f,setF]=useState({name:user.name,company:user.company,email:user.email,inn:'',activity:''});
  const upd=(k,v)=>setF(p=>({...p,[k]:v}));
  const save=()=>{setUser(u=>({...u,name:f.name,company:f.company}));toast('Настройки сохранены');};
  return(
    <div style={{padding:28,maxWidth:560}}>
      <h1 style={{fontSize:20,fontWeight:800,marginBottom:3}}>Настройки</h1>
      <p style={{color:C.muted,marginBottom:24,fontSize:13}}>Профиль компании и параметры аккаунта</p>
      <Card style={{padding:22,marginBottom:16}}>
        <div style={{fontWeight:700,fontSize:14,marginBottom:16}}>Профиль пользователя</div>
        <Inp label="Имя" value={f.name} onChange={v=>upd('name',v)} placeholder="Имя"/>
        <Inp label="Email" value={f.email} onChange={()=>{}} placeholder="Email" type="email"/>
      </Card>
      <Card style={{padding:22,marginBottom:16}}>
        <div style={{fontWeight:700,fontSize:14,marginBottom:16}}>Данные компании</div>
        <Inp label="Наименование компании" value={f.company} onChange={v=>upd('company',v)} placeholder="ООО Торговая компания"/>
        <Inp label="ИНН компании" value={f.inn} onChange={v=>upd('inn',v)} placeholder="1234567890"/>
        <Sel label="Вид деятельности" value={f.activity} onChange={v=>upd('activity',v)} options={[{v:'import',l:'Импортёр'},{v:'export',l:'Экспортёр'},{v:'both',l:'Импортёр и экспортёр'},{v:'broker',l:'Таможенный брокер / ВЭД-агент'},{v:'bank',l:'Финансовый посредник'},{v:'legal',l:'Юридическая фирма'}]}/>
      </Card>
      <Card style={{padding:22,marginBottom:16}}>
        <div style={{fontWeight:700,fontSize:14,marginBottom:12}}>Тарифный план</div>
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',padding:'10px 14px',background:C.accentBg,borderRadius:8,border:`1px solid ${C.borderHi}`}}>
          <div><div style={{fontWeight:700,color:C.accent}}>Бизнес</div><div style={{fontSize:11,color:C.muted,marginTop:2}}>30 проверок в месяц · 6 модулей · API</div></div>
          <div style={{fontWeight:700,fontSize:16,color:C.accent}}>14 900 ₽/мес</div>
        </div>
      </Card>
      <Card style={{padding:18,marginBottom:16}}>
        <div style={{fontWeight:700,fontSize:13,marginBottom:10}}>Следующие шаги для production</div>
        {[['🔐','Реальная JWT-авторизация','Замените mock на Node.js + bcrypt'],['🗄','PostgreSQL + RLS','Данные пользователей изолированы на уровне БД'],['🔑','API-ключ на сервере','Claude API Key хранить в .env, не на фронте'],['📤','Docker + деплой','docker-compose.yml: app + postgres + nginx']].map(([i,t,d])=>(
          <div key={t} style={{display:'flex',gap:10,padding:'8px 0',borderBottom:`1px solid ${C.border}`,alignItems:'flex-start'}}>
            <span style={{fontSize:16,flexShrink:0}}>{i}</span>
            <div><div style={{fontSize:12,fontWeight:600,marginBottom:2}}>{t}</div><div style={{fontSize:11,color:C.muted}}>{d}</div></div>
          </div>
        ))}
      </Card>
      <Btn onClick={save} style={{padding:'11px 28px'}}>Сохранить изменения</Btn>
    </div>
  );
}

// ── ROOT ────────────────────────────────────────────────────────────────────
export default function App(){
  const [view,setView]=useState('landing');
  const [user,setUser]=useState(null);
  const [result,setResult]=useState(null);
  const [history,setHistory]=useState([]);
  const [toasts,setToasts]=useState([]);
  const [prefillForm,setPrefillForm]=useState(null);

  useEffect(()=>{(async()=>{try{const r=await window.storage.get('aegis_h3');if(r)setHistory(JSON.parse(r.value));}catch{}})();},[]);

  const toast=(msg,t='success')=>{const id=Date.now();setToasts(p=>[...p,{id,msg,t}]);setTimeout(()=>setToasts(p=>p.filter(x=>x.id!==id)),3500);};
  const addToHistory=(item)=>{const h=[item,...history].slice(0,50);setHistory(h);(async()=>{try{await window.storage.set('aegis_h3',JSON.stringify(h));}catch{}})();};
  const deleteCheck=(id)=>{const h=history.filter(x=>x.id!==id);setHistory(h);(async()=>{try{await window.storage.set('aegis_h3',JSON.stringify(h));}catch{}})();toast('Проверка удалена');};
  const rerunCheck=(form)=>{setPrefillForm({...form});setView('check');};
  const exportCSV=()=>{
    if(!history.length){toast('Нет данных для экспорта','error');return;}
    const hdr=['ID','Дата','Контрагент','Страна','Товар','Вердикт','Риск-скор','Уровень'];
    const rows=history.map(h=>[h.id,new Date(h.date).toLocaleString('ru-RU'),h.counterparty,h.country,h.product||'',h.result?.verdict||'',h.result?.score||0,h.result?.overall||'']);
    const csv=[hdr,...rows].map(r=>r.map(c=>`"${String(c).replace(/"/g,'""')}"`).join(',')).join('\n');
    const b=new Blob(['\uFEFF'+csv],{type:'text/csv;charset=utf-8;'});
    const u=URL.createObjectURL(b);const a=document.createElement('a');a.href=u;a.download='aegis_history.csv';a.click();URL.revokeObjectURL(u);
    toast('CSV экспортирован');
  };
  const nav=(v)=>{if(!user&&['dashboard','check','history','result','settings'].includes(v)){setView('auth');return;}setView(v);};
  const logout=()=>{setUser(null);setView('landing');};

  return(
    <div style={{minHeight:'100vh',background:C.bg,color:C.text,fontFamily:"'Inter',system-ui,sans-serif"}}>
      {view==='landing'&&<Landing nav={nav}/>}
      {view==='auth'&&<Auth nav={nav} setUser={setUser} toast={toast}/>}
      {user&&(
        <Shell user={user} view={view} nav={nav} logout={logout}>
          {view==='dashboard'&&<Dashboard nav={nav} history={history} user={user}/>}
          {view==='check'&&<CheckForm nav={nav} setResult={setResult} addToHistory={addToHistory} toast={toast} prefillForm={prefillForm} clearPrefill={()=>setPrefillForm(null)}/>}
          {view==='result'&&result&&<Result nav={nav} result={result} toast={toast}/>}
          {view==='history'&&<History nav={nav} history={history} setResult={setResult} toast={toast} deleteCheck={deleteCheck} rerunCheck={rerunCheck} exportCSV={exportCSV}/>}
          {view==='settings'&&<Settings user={user} setUser={setUser} toast={toast}/>}
        </Shell>
      )}
      <Toasts toasts={toasts}/>
    </div>
  );
}
