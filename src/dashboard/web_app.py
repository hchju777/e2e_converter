"""비개발자용 로컬 SAV → HTML/CSV 변환 웹 애플리케이션."""

import base64
import hashlib
import json
import os
import re
import signal
import tempfile
import threading
import time
import uuid
import webbrowser
import sys
from contextlib import contextmanager
from datetime import date
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
import pyreadstat

from src.dashboard.build_dashboard import (
    _period_label,
    build_dashboard_from_history,
    read_overview,
)
from src.dashboard.generate_pdf import generate_pdf
from src.dashboard.generate_pptx import generate_pptx
from src.metrics.calc_metrics import calc_metrics, load_settings, load_spec
from src.utils.banner import filter_banner_data, validate_banner_configs
from src.utils.excel_history import (
    ExcelHistoryError,
    check_new_wave,
    next_wave,
    parse_wave,
    read_history,
    read_wave_labels,
    validate_against_spec,
    wave_start_date,
    write_history,
)
from src.utils.logger import get_logger


logger = get_logger(__name__)
HOST = "127.0.0.1"
DEFAULT_PORT = 8765
MAX_UPLOAD_BYTES = 100 * 1024 * 1024

APP_HTML = r"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>PsO Dashboard Converter v{{APP_VERSION}}</title>
  <style>
    *{box-sizing:border-box} body{margin:0;background:#f3f6fb;color:#17233c;font-family:Arial,'Noto Sans KR',sans-serif}
    .wrap{max-width:760px;margin:48px auto;padding:0 20px}.card{background:white;border-radius:18px;padding:34px;box-shadow:0 12px 36px #1a31551a}
    h1{margin:0 0 8px;font-size:28px}.sub{margin:0 0 28px;color:#61708b;line-height:1.6}
    .drop{border:2px dashed #9eb0cc;border-radius:14px;padding:42px 20px;text-align:center;background:#f9fbff;cursor:pointer;transition:.2s}
    .drop.over{border-color:#008e4e;background:#effaf5}.drop strong{display:block;font-size:18px;margin-bottom:8px}.drop span{color:#71809a}
    /* 잘못된 파일을 넣으면 그 드롭 영역 자리에서 바로 알린다(화면 아래 상태창은 놓치기 쉽다). */
    .drop.invalid{border-color:#d94a4a;background:#fff5f5;animation:shake .3s}
    .drop.invalid strong{color:#a42525}.drop.invalid span{color:#c06060}
    @keyframes shake{0%,100%{transform:translateX(0)}25%{transform:translateX(-6px)}75%{transform:translateX(6px)}}
    @media (prefers-reduced-motion: reduce){ .drop.invalid{animation:none} }
    .drop.ok{border-color:#008e4e;background:#f4fbf7}.drop.ok strong{color:#11633d}
    input[type=file]{display:none}.field{margin-top:22px}.field label{display:block;font-weight:700;margin-bottom:8px}
    input[type=text]{width:100%;padding:13px 14px;border:1px solid #cbd5e5;border-radius:9px;font-size:16px}
    textarea{width:100%;padding:13px 14px;border:1px solid #cbd5e5;border-radius:9px;font-size:15px;font-family:inherit;line-height:1.5;resize:vertical}
    input[type=date]{padding:12px 12px;border:1px solid #cbd5e5;border-radius:9px;font-size:15px;font-family:inherit}
    .daterange{display:flex;align-items:center;gap:10px}.daterange input{flex:1}.daterange span{color:#61708b}
    input[type=number]{width:90px;padding:13px 10px;border:1px solid #cbd5e5;border-radius:9px;font-size:16px;font-family:inherit}
    .periodrow{display:flex;align-items:center;gap:8px}.periodrow span{color:#17233c;font-weight:700}
    .periodrow .preview{margin-left:8px;color:#008e4e;font-weight:700}
    .hint{font-weight:400;color:#9aa7bd;font-size:12px}
    .overview-fields{margin-top:22px;padding:20px;border:1px solid #e3e9f2;border-radius:12px;background:#f9fbff}
    .overview-fields>.section-title{font-weight:700;font-size:14px;color:#17233c;margin-bottom:4px}
    .overview-fields>.section-sub{color:#71809a;font-size:12px;margin-bottom:6px}
    .overview-fields .field:first-of-type{margin-top:14px}
    button,.download{display:inline-block;border:0;border-radius:9px;padding:13px 18px;font-weight:700;text-decoration:none;cursor:pointer}
    #convert{width:100%;margin-top:22px;background:#008e4e;color:white;font-size:16px}#convert:disabled{background:#9ba8b8;cursor:not-allowed}
    .status{display:none;margin-top:22px;padding:15px;border-radius:10px;line-height:1.6;white-space:pre-wrap}.status.show{display:block}
    .working{background:#edf5ff;color:#174f91}.error{background:#fff0f0;color:#a42525}.success{background:#edf9f3;color:#11633d}
    /* 작업이 진행 중일 때는 안내 상자가 켜졌다 꺼지듯 눈에 띄게 한다. */
    .status.working{border:2px solid #7fb0ee;animation:pulse 1.2s ease-in-out infinite;font-weight:700}
    @keyframes pulse{
      0%,100%{background:#edf5ff;border-color:#a9cbf5;box-shadow:0 0 0 0 rgba(23,79,145,0)}
      50%    {background:#d3e7ff;border-color:#2f7ae0;box-shadow:0 0 14px 2px rgba(47,122,224,.45)}
    }
    @media (prefers-reduced-motion: reduce){ .status.working{animation:none;background:#d3e7ff;border-color:#2f7ae0} }
    .downloads{display:none;margin-top:18px;gap:8px;flex-wrap:wrap}.downloads.show{display:flex}
    /* 낱말이 중간에서 끊기지 않게 하고, 줄 수가 달라도 글자가 버튼 가운데에 오게 한다. */
    .download{background:#17233c;color:white;flex:1;min-width:150px;text-align:center;word-break:keep-all;line-height:1.35;
              display:flex;align-items:center;justify-content:center}
    .warnings{display:none;margin-top:16px;padding:16px 18px;border:1px solid #f0cf7a;border-radius:10px;background:#fff9e8;color:#704b00;font-size:14px;line-height:1.7}
    .warnings.show{display:block}.warnings-title{font-weight:700;font-size:15px;margin-bottom:10px}.warning-item{padding:9px 0;border-top:1px solid #f2dfad;white-space:pre-wrap;overflow-wrap:anywhere}.warning-item:first-of-type{border-top:0}
    .privacy{margin-top:22px;color:#71809a;font-size:13px;text-align:center}
  </style>
</head>
<body><div class="wrap"><div class="card">
  <h1>📊 PsO Dashboard Converter</h1>
  <div style="margin:-2px 0 12px;color:#008e4e;font-weight:700">Version {{APP_VERSION}}</div>
  <p class="sub">과거 데이터 엑셀과 이번 차수 SAV 파일을 함께 올리면, 전체 차수가 담긴 HTML 대시보드와 새 차수가 추가된 엑셀, CSV·PDF·PPTX를 만듭니다.<br>두 파일이 모두 있어야 변환할 수 있습니다.</p>
  <div id="excelDrop" class="drop"><strong>📗 과거 데이터 엑셀을 여기에 놓으세요</strong><span>또는 클릭해서 파일 선택 (.xlsx) · 지난 차수까지의 지표가 담긴 파일</span></div>
  <input id="excelFile" type="file">
  <div id="drop" class="drop"><strong>📂 SAV 파일을 여기에 놓으세요</strong><span>또는 클릭해서 파일 선택 (.sav, 최대 100MB)</span></div>
  <input id="file" type="file">
  <div class="field"><label for="periodYear">보고 차수</label>
    <div class="periodrow">
      <input id="periodYear" type="number" min="20" max="99" step="1" inputmode="numeric"><span>년</span>
      <input id="periodWave" type="number" min="1" max="12" step="1" inputmode="numeric"><span>차</span>
      <span class="preview" id="periodPreview"></span>
    </div>
  </div>
  <div class="overview-fields">
    <div class="section-title">🗂️ 조사 설계</div>
    <div class="section-sub">대시보드 "조사 설계" 장표에 들어갈 값입니다. 필요하면 수정하세요.</div>
    <div class="field"><label for="ovTarget">조사 대상 <span class="hint">(한 줄에 한 항목)</span></label><textarea id="ovTarget" rows="3">{{OV_TARGET}}</textarea></div>
    <div class="field"><label for="ovSample">표본 크기</label><input id="ovSample" type="text" value="{{OV_SAMPLE}}"></div>
    <div class="field"><label for="ovRegion">조사 지역</label><input id="ovRegion" type="text" value="{{OV_REGION}}"></div>
    <div class="field"><label for="ovMethod">자료 수집 방법</label><input id="ovMethod" type="text" value="{{OV_METHOD}}"></div>
    <div class="field"><label for="ovStart">실사 기간</label><div class="daterange"><input id="ovStart" type="date"><span>~</span><input id="ovEnd" type="date"></div></div>
  </div>
  <button id="convert" disabled>🚀 대시보드 생성</button>
  <div id="status" class="status"></div>
  <div id="downloads" class="downloads"><a id="htmlDownload" class="download">🌐 HTML 대시보드</a><a id="xlsxDownload" class="download">📗 엑셀<br>(다음 차수용)</a><a id="csvDownload" class="download">📄 CSV 결과</a><a id="pdfDownload" class="download">📋 PDF 보고서</a><a id="pptxDownload" class="download">🎯 PPTX 발표</a></div>
  <div id="warnings" class="warnings"></div>
  <div class="privacy">🔒 파일은 이 PC 내부에서만 처리되며 외부 서버로 전송되지 않습니다.</div>
</div></div>
<script>
const drop=document.getElementById('drop'), fileInput=document.getElementById('file'), button=document.getElementById('convert');
const excelDrop=document.getElementById('excelDrop'), excelInput=document.getElementById('excelFile');
const statusEl=document.getElementById('status'), downloads=document.getElementById('downloads'), warnings=document.getElementById('warnings');
let selectedFile=null, selectedExcel=null;
function clearWarnings(){warnings.className='warnings';warnings.innerHTML='';}
// 엑셀과 SAV가 모두 선택되어야만 변환할 수 있다.
function refreshConvertButton(){ button.disabled = !(selectedFile && selectedExcel); }
// 안내 문구 원본을 기억해 두었다가 오류를 지울 때 되돌린다.
const dropDefaults=new Map();
for(const zone of [excelDrop, drop]){
  dropDefaults.set(zone,{title:zone.querySelector('strong').textContent,
                         sub:zone.querySelector('span').textContent});
}
function setDropText(zone,title,sub){
  zone.querySelector('strong').textContent=title;
  zone.querySelector('span').textContent=sub;
}
function markDrop(zone,file){
  zone.classList.remove('invalid'); zone.classList.add('ok');
  setDropText(zone,'✅ '+file.name,(file.size/1024/1024).toFixed(2)+' MB');
}
/* 오류는 사용자가 방금 파일을 놓은 그 자리에 띄운다.
   화면 아래쪽 상태창만 쓰면 스크롤 밖이라 보이지 않는다. */
function markDropInvalid(zone,message,file){
  zone.classList.remove('ok'); zone.classList.remove('invalid');
  void zone.offsetWidth;                       // 같은 오류가 반복돼도 흔들림이 다시 보이게 한다
  zone.classList.add('invalid');
  setDropText(zone,message,file?('선택한 파일: '+file.name):dropDefaults.get(zone).sub);
  showStatus('error',message+(file?('\n선택한 파일: '+file.name):''));
}
function resetOutputs(){ downloads.classList.remove('show'); clearWarnings(); statusEl.className='status'; }
function selectFile(file){
  try{
    if(!file){ markDropInvalid(drop,'❌ 파일을 인식하지 못했습니다. 다시 선택해 주세요.',null); return; }
    if(!/\.sav$/i.test(file.name)){
      selectedFile=null; refreshConvertButton();
      markDropInvalid(drop,'❌ sav 형식의 파일을 업로드하세요.',file); return;
    }
    selectedFile=file; markDrop(drop,file); refreshConvertButton(); resetOutputs();
  }catch(error){ markDropInvalid(drop,'❌ 파일을 읽지 못했습니다: '+error.message,null); }
}
async function selectExcel(file){
  try{
    if(!file){ markDropInvalid(excelDrop,'❌ 파일을 인식하지 못했습니다. 다시 선택해 주세요.',null); return; }
    if(!/\.(xlsx|xlsm)$/i.test(file.name)){
      selectedExcel=null; refreshConvertButton();
      markDropInvalid(excelDrop,'❌ xlsx 형식의 파일을 업로드하세요.',file); return;
    }
    selectedExcel=file; markDrop(excelDrop,file); refreshConvertButton(); resetOutputs();
    // 엑셀에 담긴 차수를 읽어 조사 기간 기본값을 채운다.
    setDropText(excelDrop,'✅ '+file.name,'차수를 확인하는 중...');
    const response=await fetch('/excel-info',{method:'POST',
      headers:{'Content-Type':'application/octet-stream'}, body:file});
    const info=await response.json();
    if(!response.ok){
      selectedExcel=null; refreshConvertButton();
      markDropInvalid(excelDrop,'❌ '+(info.error||'엑셀을 읽지 못했습니다.'),file); return;
    }
    setDropText(excelDrop,'✅ '+file.name,
      info.count+'개 차수 ('+info.first+' ~ '+info.latest+') · '+(file.size/1024/1024).toFixed(2)+' MB');
    // 보고 차수는 엑셀에 아직 없는 바로 다음 차수로 맞춘다.
    periodYear.value=String(info.next_year);
    periodWave.value=String(info.next_number);
    refreshPeriod();
    // 실사 시작일은 엑셀의 첫 차수가 시작한 달의 1일, 종료일은 오늘로 맞춘다.
    ovStart.value=info.fieldwork_start;
    ovEnd.value=todayISO();
    if(ovEnd.value<ovStart.value) ovEnd.value=ovStart.value;
    syncDateBounds();
  }catch(error){
    selectedExcel=null; refreshConvertButton();
    markDropInvalid(excelDrop,'❌ 파일을 읽지 못했습니다: '+error.message,null);
  }
}
function showStatus(type,text){statusEl.className='status show '+type;statusEl.textContent=text;}

/* 저장 위치와 파일 이름을 사용자가 고르게 한다.
   1) File System Access API를 지원하면(Chrome/Edge — Windows·macOS·Linux) 운영체제 저장 대화상자를 띄운다.
   2) 지원하지 않으면(Firefox/Safari 등) 파일 이름만 입력받아 브라우저 기본 다운로드 폴더에 저장한다.

   중요: 저장 대화상자는 사용자가 버튼을 누른 직후 몇 초 안에만 열 수 있다. PDF/PPTX처럼
   만드는 데 30초씩 걸리는 파일은 다 만든 뒤에 열려고 하면 권한이 만료돼 대화상자가 뜨지 않는다.
   그래서 저장 위치를 '먼저' 고르고(pickSaveTarget), 파일이 준비되면 그때 쓴다(writeToTarget). */
async function pickSaveTarget(suggestedName, mime, description){
  if(window.showSaveFilePicker){
    const extension='.'+suggestedName.split('.').pop();
    try{
      const handle=await window.showSaveFilePicker({
        suggestedName,
        types:[{description:description, accept:{[mime]:[extension]}}],
      });
      return {handle, name:suggestedName};
    }catch(error){
      // 사용자가 대화상자에서 '취소'를 누른 경우에만 중단한다.
      if(error && error.name==='AbortError') return null;
      // 그 밖의 오류(권한 제한, 미지원 환경 등)는 아래 폴백으로 저장한다.
    }
  }
  const name=window.prompt('저장할 파일 이름을 입력하세요.\n(브라우저의 기본 다운로드 폴더에 저장됩니다)', suggestedName);
  if(name===null) return null;
  return {handle:null, name:(name.trim()||suggestedName)};
}

async function writeToTarget(target, blob){
  if(target.handle){
    const writable=await target.handle.createWritable();
    await writable.write(blob);
    await writable.close();
    return true;
  }
  const url=URL.createObjectURL(blob);
  const link=document.createElement('a');
  link.href=url; link.download=target.name;
  document.body.appendChild(link); link.click(); link.remove();
  setTimeout(()=>URL.revokeObjectURL(url), 1000);
  return true;
}

const EXPORTS={
  htmlDownload:{key:'html', base:'PsO_dashboard',    ext:'.html', mime:'text/html',  label:'HTML 대시보드'},
  xlsxDownload:{key:'xlsx', base:'PsO_history',      ext:'.xlsx',
                mime:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', label:'엑셀'},
  csvDownload: {key:'csv',  base:'PsO_metrics',      ext:'.csv',  mime:'text/csv',   label:'CSV 결과'},
  pdfDownload: {key:'pdf',  base:'PsO_report',       ext:'.pdf',  mime:'application/pdf', label:'PDF 보고서'},
  pptxDownload:{key:'pptx', base:'PsO_presentation', ext:'.pptx',
                mime:'application/vnd.openxmlformats-officedocument.presentationml.presentation', label:'PPTX 발표자료'},
};

drop.onclick=()=>fileInput.click(); fileInput.onchange=e=>selectFile(e.target.files[0]);
for(const event of ['dragenter','dragover']) drop.addEventListener(event,e=>{e.preventDefault();drop.classList.add('over')});
for(const event of ['dragleave','drop']) drop.addEventListener(event,e=>{e.preventDefault();drop.classList.remove('over')});
drop.addEventListener('drop',e=>selectFile(e.dataTransfer.files[0]));
excelDrop.onclick=()=>excelInput.click(); excelInput.onchange=e=>selectExcel(e.target.files[0]);
for(const event of ['dragenter','dragover']) excelDrop.addEventListener(event,e=>{e.preventDefault();excelDrop.classList.add('over')});
for(const event of ['dragleave','drop']) excelDrop.addEventListener(event,e=>{e.preventDefault();excelDrop.classList.remove('over')});
excelDrop.addEventListener('drop',e=>selectExcel(e.dataTransfer.files[0]));
const ovStart=document.getElementById('ovStart'), ovEnd=document.getElementById('ovEnd');
const periodYear=document.getElementById('periodYear'), periodWave=document.getElementById('periodWave');
const periodPreview=document.getElementById('periodPreview');
const pad=n=>String(n).padStart(2,'0');

// 보고 차수 기본값: 연도는 올해, 차수는 1
periodYear.value=String(new Date().getFullYear()).slice(-2);
periodWave.value='1';

function clampNumber(input, fallback){
  const value=parseInt(input.value,10);
  const min=parseInt(input.min,10), max=parseInt(input.max,10);
  if(!Number.isFinite(value)) return fallback;
  return Math.min(max, Math.max(min, value));
}
function periodParts(){
  return {year: clampNumber(periodYear, 26), wave: clampNumber(periodWave, 1)};
}
function periodText(){
  const {year, wave}=periodParts();
  return year+'년 '+wave+'차';
}
function todayISO(){
  const now=new Date();
  return now.getFullYear()+'-'+pad(now.getMonth()+1)+'-'+pad(now.getDate());
}
function refreshPeriod(){ periodPreview.textContent=periodText(); }

// 실사 기간 초기값. 엑셀을 올리면 시작일은 엑셀의 첫 차수 기준으로 다시 채워진다.
ovStart.value=todayISO();
ovEnd.value=todayISO();

// 방어 로직: 시작일이 종료일보다 뒤가 되는 상황을 애초에 막는다.
// 달력에서 선택 불가 영역(min/max)으로 막고, 직접 입력 등으로 뒤집히면 자동 보정한다.
function syncDateBounds(){ ovEnd.min=ovStart.value||''; ovStart.max=ovEnd.value||''; }
ovStart.addEventListener('change',()=>{ if(ovStart.value&&ovEnd.value&&ovEnd.value<ovStart.value) ovEnd.value=ovStart.value; syncDateBounds(); });
ovEnd.addEventListener('change',()=>{ if(ovStart.value&&ovEnd.value&&ovStart.value>ovEnd.value) ovStart.value=ovEnd.value; syncDateBounds(); });
for(const input of [periodYear, periodWave]){
  input.addEventListener('change', refreshPeriod);
  input.addEventListener('input', refreshPeriod);
}
refreshPeriod();
function collectOverview(){
  return {
    target:document.getElementById('ovTarget').value.split('\n').map(s=>s.trim()).filter(Boolean),
    sample:document.getElementById('ovSample').value.trim(),
    region:document.getElementById('ovRegion').value.trim(),
    method:document.getElementById('ovMethod').value.trim(),
    fieldwork_start:document.getElementById('ovStart').value,
    fieldwork_end:document.getElementById('ovEnd').value,
  };
}
button.onclick=async()=>{
  if(!selectedFile){showStatus('error','❌ SAV 파일을 선택해 주세요.');return;}
  if(!selectedExcel){showStatus('error','❌ 과거 데이터 엑셀을 선택해 주세요.');return;}
  const period=periodText();
  const overview=collectOverview();
  if(!overview.fieldwork_start||!overview.fieldwork_end){showStatus('error','❌ 실사 기간의 시작일과 종료일을 선택해 주세요.');return;}
  if(overview.fieldwork_end<overview.fieldwork_start){showStatus('error','❌ 실사 종료일은 시작일보다 빠를 수 없습니다.');return;}
  const overviewHeader=btoa(unescape(encodeURIComponent(JSON.stringify(overview))));
  button.disabled=true; downloads.classList.remove('show'); clearWarnings(); showStatus('working','⏳ 엑셀의 과거 차수를 읽고 SAV의 지표를 계산하고 있습니다...');
  try{
    // 본문은 [엑셀][SAV] 순서로 이어 붙이고, 앞쪽 엑셀 길이를 헤더로 알려준다.
    const response=await fetch('/convert?period='+encodeURIComponent(period),{method:'POST',
      headers:{'Content-Type':'application/octet-stream',
               'X-File-Name':encodeURIComponent(selectedFile.name),
               'X-Excel-Name':encodeURIComponent(selectedExcel.name),
               'X-Excel-Bytes':String(selectedExcel.size),
               'X-Overview-Data':overviewHeader},
      body:new Blob([selectedExcel, selectedFile])});
    const data=await response.json(); if(!response.ok)throw new Error(data.error||'변환에 실패했습니다.');
    showStatus('success',`✅ 변환 완료\n응답자 ${data.respondents}명 · 지표 ${data.metrics}개 · 경고 ${data.warning_count}건\n대시보드 차수 ${data.waves}개 (${data.period} 추가됨)`);
    const suffix=period?('_'+period.replace(/\s+/g,'')):'';
    downloads.classList.add('show');
    for(const [id,cfg] of Object.entries(EXPORTS)){
      const link=document.getElementById(id);
      link.href='#'; link.dataset.busy='';
      link.onclick=async(event)=>{
        event.preventDefault();
        if(link.dataset.busy==='1') return;
        link.dataset.busy='1';
        try{
          // 저장 위치를 먼저 묻는다. PDF/PPTX는 생성에 오래 걸려서, 만든 뒤에 물으면
          // 대화상자를 띄울 권한이 만료돼 기본 다운로드 폴더로 떨어져 버린다.
          const target=await pickSaveTarget(cfg.base+suffix+cfg.ext, cfg.mime, cfg.label);
          if(!target){ showStatus('success','저장을 취소했습니다.'); return; }
          const slow=(cfg.key==='pdf'||cfg.key==='pptx');
          if(slow) showStatus('working','⏳ '+cfg.label+'를 만들고 있습니다.\n최대 30초 정도 걸릴 수 있으니 이 창을 닫지 말고 기다려 주세요.');
          const fileResponse=await fetch(data[cfg.key+'_url']);
          if(!fileResponse.ok){
            let message=cfg.label+' 생성에 실패했습니다.';
            try{ message=(await fileResponse.json()).error||message; }catch(_){}
            throw new Error(message);
          }
          const blob=await fileResponse.blob();
          await writeToTarget(target, blob);
          showStatus('success','✅ '+cfg.label+'를 저장했습니다.\n'+target.name);
        }catch(error){ showStatus('error','❌ '+error.message); }
        finally{ link.dataset.busy=''; }
      };
    }
    if(data.warnings.length){
      warnings.className='warnings show';
      warnings.innerHTML='<div class="warnings-title">⚠️ 계산 경고 '+data.warning_count+'건</div>';
      data.warnings.slice(0,20).forEach((message,index)=>{
        const item=document.createElement('div'); item.className='warning-item';
        item.textContent=(index+1)+'. '+message.split(' | ').join('\n   '); warnings.appendChild(item);
      });
      if(data.warnings.length>20){const more=document.createElement('div');more.className='warning-item';more.textContent='외 '+(data.warnings.length-20)+'건은 CSV의 경고 컬럼에서 확인하세요.';warnings.appendChild(more)}
    }
  }catch(error){showStatus('error','❌ '+error.message)}finally{button.disabled=false}
};
</script></body></html>"""


def bundled_resource(relative_path: str) -> Path:
    """개발 환경 또는 PyInstaller EXE 내부의 리소스 경로를 반환한다."""
    base_dir = Path(getattr(sys, "_MEIPASS", Path.cwd()))
    return base_dir / relative_path


def get_app_version() -> str:
    version = bundled_resource("config/VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError(f"VERSION은 x.y.z 형식이어야 합니다: {version}")
    return version


def load_web_settings() -> dict:
    settings = load_settings(str(bundled_resource("config/settings.json")))
    settings["spec_path"] = str(bundled_resource("config/metric_spec.csv"))
    # PyInstaller spec도 이 설정값의 상대경로를 그대로 보존해 번들에 포함한다.
    settings["dashboard_template"] = str(bundled_resource(settings["dashboard_template"]))
    return settings


def format_fieldwork(start: str, end: str) -> str:
    """'YYYY-MM-DD' 시작/종료 날짜를 '2025년 1월 1일 ~ 2026년 7월 26일' 형식으로 변환한다.

    실사 기간이 해를 넘길 수 있으므로 시작일과 종료일 모두 연도를 표기한다.
    """
    try:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
    except (TypeError, ValueError):
        raise ValueError("실사 기간 날짜 형식이 올바르지 않습니다.")
    if end_date < start_date:
        raise ValueError("실사 종료일은 시작일보다 빠를 수 없습니다.")
    return (
        f"{start_date.year}년 {start_date.month}월 {start_date.day}일 "
        f"~ {end_date.year}년 {end_date.month}월 {end_date.day}일"
    )


def parse_overview_input(raw_header: str | None) -> dict | None:
    """웹 폼이 보낸 X-Overview-Data(base64 JSON)를 대시보드 OVERVIEW 형식으로 변환한다."""
    if not raw_header:
        return None
    data = json.loads(base64.b64decode(raw_header).decode("utf-8"))
    target = [str(item).strip() for item in data.get("target", []) if str(item).strip()]
    return {
        "target": target,
        "sample": str(data.get("sample", "")).strip(),
        "region": str(data.get("region", "")).strip(),
        "method": str(data.get("method", "")).strip(),
        "fieldwork": format_fieldwork(data.get("fieldwork_start"), data.get("fieldwork_end")),
    }


def render_app_html(settings: dict) -> str:
    """템플릿의 조사 설계 기본값을 웹 입력창 초기값으로 채워 앱 HTML을 생성한다."""
    overview = read_overview(settings["dashboard_template"])
    page = APP_HTML.replace("{{APP_VERSION}}", get_app_version())
    page = page.replace("{{OV_TARGET}}", escape("\n".join(overview.get("target", []))))
    page = page.replace("{{OV_SAMPLE}}", escape(str(overview.get("sample", "")), quote=True))
    page = page.replace("{{OV_REGION}}", escape(str(overview.get("region", "")), quote=True))
    page = page.replace("{{OV_METHOD}}", escape(str(overview.get("method", "")), quote=True))
    return page


def convert_sav(
    sav_path: Path,
    excel_path: Path,
    period: str,
    settings: dict,
    output_dir: Path,
    sav_hash: str,
    excel_hash: str,
    overview: dict | None = None,
) -> dict:
    """업로드된 히스토릭 엑셀과 SAV로 대시보드·CSV·갱신된 엑셀을 만든다.

    과거 차수 값은 엑셀이 정본이며, SAV는 새 차수 하나만 만들어 낸다.
    PDF/PPTX는 여기서 만들지 않는다 — 실제로 다운로드가 요청될 때 lazy하게 생성한다
    (ConverterServer.get_or_build_report 참고).
    """
    _period_label(period)  # 계산 전에 차수 형식을 먼저 검증한다.

    specs = load_spec(settings["spec_path"], "전체")
    logger.info("📗 히스토릭 엑셀 읽는 중: %s", excel_path.name)
    history = read_history(excel_path)
    validate_against_spec(history, [spec.question for spec in specs])
    period = check_new_wave(history, period)

    logger.info("📂 업로드 SAV 읽는 중: %s", sav_path.name)
    df, _meta = pyreadstat.read_sav(str(sav_path))
    logger.info("📊 SAV 로드 완료: 응답자 %d명, 변수 %d개", len(df), len(df.columns))

    banner_configs = settings["dashboard_banners"]
    validate_banner_configs(banner_configs)
    banner_values = {}
    result_frames = []
    warning_messages = []

    for config in banner_configs:
        name = config["name"]
        banner_df = filter_banner_data(df, config)
        logger.info("🧮 %s 배너 계산 중 (%d명)", name, len(banner_df))
        result = calc_metrics(banner_df, specs, period)
        failures = result[result["오류"] != ""]
        if not failures.empty:
            first = failures.iloc[0]
            raise ValueError(f"{name} 배너 계산 실패: {first['문항']} - {first['오류']}")
        result["배너조건"] = name
        result_frames.append(result)
        banner_values[name] = [None if pd.isna(value) else value for value in result[period].tolist()]
        for row in result[result["경고"] != ""][["항목", "문항", "경고"]].to_dict("records"):
            warning_messages.append(f"{name} | {row['항목']} | {row['문항']} | {row['경고']}")

    output_dir.mkdir(parents=True, exist_ok=True)
    result_df = pd.concat(result_frames, ignore_index=True)
    csv_path = output_dir / "metrics.csv"
    html_path = output_dir / "dashboard.html"
    xlsx_path = output_dir / "history.xlsx"

    result_df.to_csv(csv_path, index=False, encoding="utf-8-sig", na_rep="NaN")

    # 과거 차수는 엑셀이 정본이다. 엑셀의 모든 차수 + 이번 SAV 차수로 대시보드를 다시 만든다.
    periods = history.waves + [period]
    period_values = dict(history.values)
    period_values[period] = banner_values
    build_dashboard_from_history(
        settings["dashboard_template"], str(html_path), periods, period_values, overview
    )
    write_history(history.source_path, xlsx_path, period, banner_values)

    logger.info(
        "✅ 변환 완료: 지표 %d개, 경고 %d개, 대시보드 %d개 차수",
        len(result_df), len(warning_messages), len(periods),
    )
    # 조사 설계 값도 대시보드(및 PDF/PPTX의 조사 설계 장표)에 반영되므로 캐시 키에 포함한다.
    overview_key = hashlib.sha256(
        json.dumps(overview or {}, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    return {
        "html_path": html_path,
        "csv_path": csv_path,
        "xlsx_path": xlsx_path,
        "period": period,
        # 같은 SAV(내용 동일) + 같은 차수 + 같은 조사 설계 + 같은 히스토리는 항상 같은 결과이므로,
        # 업로드 토큰이 달라도 PDF/PPTX 캐시를 공유할 수 있도록 내용 기반 키를 만든다.
        "cache_key": f"{sav_hash}:{period}:{overview_key}:{excel_hash}",
        "respondents": len(df),
        "metrics": len(result_df),
        "waves": len(periods),
        "warnings": warning_messages,
    }


class ConverterServer(ThreadingHTTPServer):
    def __init__(self, address, handler, settings):
        super().__init__(address, handler)
        self.settings = settings
        self.temp_dir = tempfile.TemporaryDirectory(prefix="pso_converter_")
        self.jobs: dict[str, dict] = {}
        self.jobs_lock = threading.Lock()
        self._active_jobs = 0
        self._active_jobs_lock = threading.Lock()

        # PDF/PPTX는 요청이 실제로 들어올 때 lazy하게 만들고, 같은 SAV+차수(cache_key)에
        # 대해서는 다시 만들지 않고 캐시된 파일을 그대로 돌려준다.
        self._report_cache_dir = Path(self.temp_dir.name) / "_report_cache"
        self._report_cache_dir.mkdir(exist_ok=True)
        self.report_cache: dict[str, dict[str, Path]] = {}
        self.report_cache_lock = threading.Lock()
        self._report_build_locks: dict[str, threading.Lock] = {}

    @property
    def active_job_count(self) -> int:
        with self._active_jobs_lock:
            return self._active_jobs

    @contextmanager
    def track_job(self):
        """/convert, /download 처리 구간을 표시한다. 종료 시 이 구간이 끝날 때까지 temp_dir을 지우지 않는다."""
        with self._active_jobs_lock:
            self._active_jobs += 1
        try:
            yield
        finally:
            with self._active_jobs_lock:
                self._active_jobs -= 1

    def _build_lock_for(self, cache_key: str, kind: str) -> threading.Lock:
        lock_key = f"{cache_key}:{kind}"
        with self.report_cache_lock:
            lock = self._report_build_locks.get(lock_key)
            if lock is None:
                lock = threading.Lock()
                self._report_build_locks[lock_key] = lock
            return lock

    def get_or_build_report(self, kind: str, cache_key: str, dashboard_html: Path, period: str) -> Path:
        """PDF/PPTX를 요청 시점에 만들고(lazy), 같은 cache_key로 이미 만든 게 있으면 그걸 재사용한다."""
        cached = self._cached_report_path(cache_key, kind)
        if cached is not None:
            logger.info("♻️ 캐시된 %s 재사용 (key=%s)", kind.upper(), cache_key[:16])
            return cached

        # 같은 키에 대한 생성은 한 번만: 동시에 두 요청이 들어와도 한쪽만 실제로 만든다.
        with self._build_lock_for(cache_key, kind):
            cached = self._cached_report_path(cache_key, kind)
            if cached is not None:
                logger.info("♻️ 캐시된 %s 재사용 (key=%s)", kind.upper(), cache_key[:16])
                return cached

            # cache_key(예: "<sha256>:26년 6차")에는 Windows 경로에 쓸 수 없는 문자(:)가
            # 섞여 있을 수 있으므로, 폴더명은 별도로 해시해서 만든다.
            safe_dir_name = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()
            out_dir = self._report_cache_dir / safe_dir_name
            out_dir.mkdir(parents=True, exist_ok=True)
            extension = "pdf" if kind == "pdf" else "pptx"
            out_path = out_dir / f"report.{extension}"

            logger.info("🛠️ %s 최초 요청 — 생성 시작 (key=%s)", kind.upper(), cache_key[:16])
            if kind == "pdf":
                generate_pdf(str(out_path), str(dashboard_html), period)
            else:
                generate_pptx(str(out_path), str(dashboard_html), period)

            with self.report_cache_lock:
                self.report_cache.setdefault(cache_key, {})[kind] = out_path
            return out_path

    def _cached_report_path(self, cache_key: str, kind: str) -> Path | None:
        with self.report_cache_lock:
            path = self.report_cache.get(cache_key, {}).get(kind)
        if path is not None and path.exists():
            return path
        return None

    def server_close(self):
        super().server_close()
        self.temp_dir.cleanup()


class ConverterHandler(BaseHTTPRequestHandler):
    server: ConverterServer

    def log_message(self, format, *args):
        logger.debug(format, *args)

    def _json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            body = render_app_html(self.server.settings).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        parts = path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "download" and parts[2] in {"html", "csv", "xlsx", "pdf", "pptx"}:
            kind = parts[2]
            with self.server.jobs_lock:
                job = self.server.jobs.get(parts[1])
            if not job:
                self.send_error(HTTPStatus.NOT_FOUND)
                return

            if kind in ("html", "csv", "xlsx"):
                file_path = job[f"{kind}_path"]
            else:
                try:
                    with self.server.track_job():
                        file_path = self.server.get_or_build_report(
                            kind, job["cache_key"], job["html_path"], job["period"]
                        )
                except Exception:
                    logger.exception("💥 %s 생성 실패", kind.upper())
                    self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"{kind.upper()} 생성에 실패했습니다."})
                    return

            body = file_path.read_bytes()

            filename_map = {
                "html": "PsO_dashboard.html",
                "csv": "PsO_metrics.csv",
                "xlsx": "PsO_history.xlsx",
                "pdf": "PsO_report.pdf",
                "pptx": "PsO_presentation.pptx",
            }
            content_type_map = {
                "html": "text/html; charset=utf-8",
                "csv": "text/csv; charset=utf-8",
                "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "pdf": "application/pdf",
                "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            }
            
            filename = filename_map[kind]
            content_type = content_type_map[kind]
            
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/excel-info":
            self._handle_excel_info()
            return
        if parsed.path != "/convert":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        with self.server.track_job():
            self._handle_convert(parsed)

    def _handle_excel_info(self):
        """업로드된 엑셀의 차수 정보를 돌려준다(화면 기본값 채우기용)."""
        temp_path = None
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_UPLOAD_BYTES:
                raise ValueError("엑셀 파일을 읽을 수 없습니다.")
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as handle:
                temp_path = Path(handle.name)
            self._receive(temp_path, length)
            waves = read_wave_labels(temp_path)
            upcoming = next_wave(waves[-1])
            year, number = parse_wave(upcoming)
            self._json(HTTPStatus.OK, {
                "waves": waves,
                "first": waves[0],
                "latest": waves[-1],
                "count": len(waves),
                "fieldwork_start": wave_start_date(waves[0]),
                # 아직 엑셀에 없는 바로 다음 차수를 보고 차수 기본값으로 제안한다.
                "next_wave": upcoming,
                "next_year": year,
                "next_number": number,
            })
        except ExcelHistoryError as error:
            logger.warning("⚠️ 엑셀 정보 읽기 실패: %s", error)
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except Exception as error:
            # openpyxl의 원문 오류(예: File is not a zip file)는 사용자에게 의미가 없다.
            logger.warning("⚠️ 엑셀 파일을 열지 못했습니다: %s", error)
            self._json(HTTPStatus.BAD_REQUEST, {
                "error": "엑셀 파일을 열지 못했습니다. 올바른 xlsx 파일인지 확인해 주세요."
            })
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def _receive(self, path: Path, length: int) -> str:
        """요청 본문에서 length 바이트를 읽어 파일로 저장하고 sha256을 돌려준다."""
        hasher = hashlib.sha256()
        remaining = length
        with path.open("wb") as file:
            while remaining:
                chunk = self.rfile.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise ValueError("파일 업로드가 중간에 끊겼습니다.")
                file.write(chunk)
                hasher.update(chunk)
                remaining -= len(chunk)
        return hasher.hexdigest()

    def _handle_convert(self, parsed):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                raise ValueError("업로드된 파일이 비어 있습니다.")
            if length > MAX_UPLOAD_BYTES:
                raise ValueError("업로드 파일은 합쳐서 100MB 이하여야 합니다.")
            period = parse_qs(parsed.query).get("period", [""])[0].strip()
            if not period:
                raise ValueError("보고 차수를 입력해 주세요.")
            encoded_name = self.headers.get("X-File-Name", "uploaded.sav")
            filename = Path(encoded_name).name
            if not filename.lower().endswith(".sav"):
                raise ValueError(".sav 파일만 업로드할 수 있습니다.")
            excel_name = Path(self.headers.get("X-Excel-Name", "")).name
            if not excel_name.lower().endswith((".xlsx", ".xlsm")):
                raise ValueError("과거 데이터 엑셀(.xlsx)을 함께 올려 주세요.")
            # 본문은 [엑셀 바이트][SAV 바이트] 순서로 이어 붙여 보낸다.
            excel_length = int(self.headers.get("X-Excel-Bytes", "0"))
            if excel_length <= 0 or excel_length >= length:
                raise ValueError("엑셀 파일이 올바르게 전송되지 않았습니다.")
            overview = parse_overview_input(self.headers.get("X-Overview-Data"))

            token = uuid.uuid4().hex
            job_dir = Path(self.server.temp_dir.name) / token
            job_dir.mkdir()
            excel_path = job_dir / "history_input.xlsx"
            sav_path = job_dir / "input.sav"
            excel_hash = self._receive(excel_path, excel_length)
            sav_hash = self._receive(sav_path, length - excel_length)

            result = convert_sav(
                sav_path, excel_path, period, self.server.settings, job_dir,
                sav_hash, excel_hash, overview,
            )
            with self.server.jobs_lock:
                self.server.jobs[token] = result
            self._json(HTTPStatus.OK, {
                "version": get_app_version(),
                "respondents": result["respondents"], "metrics": result["metrics"],
                "waves": result["waves"], "period": result["period"],
                "warning_count": len(result["warnings"]), "warnings": result["warnings"],
                "html_url": f"/download/{token}/html", "csv_url": f"/download/{token}/csv",
                "xlsx_url": f"/download/{token}/xlsx",
                "pdf_url": f"/download/{token}/pdf", "pptx_url": f"/download/{token}/pptx",
            })
        except Exception as error:
            logger.exception("💥 변환 실패")
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})


def _install_shutdown_handlers(shutdown_event: threading.Event) -> None:
    """Ctrl+C(SIGINT), SIGTERM, Ctrl+Break(Windows SIGBREAK)를 받으면 종료 이벤트를 켠다."""

    def handle_signal(signum, _frame):
        logger.info("🛑 종료 신호를 받았습니다 (signal=%s)", signum)
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_signal)
    if hasattr(signal, "SIGBREAK"):  # Windows: Ctrl+Break
        signal.signal(signal.SIGBREAK, handle_signal)


def _graceful_shutdown(server: ConverterServer, timeout: float = 60.0) -> None:
    """새 요청을 막고, 진행 중인 변환 작업이 끝날 때까지 기다린 뒤 정리한다."""
    logger.info("⏹️ 새 요청 수신을 중단합니다")
    server.shutdown()  # serve_forever 루프 종료 (다른 스레드에서 호출해야 함)

    waited = 0.0
    interval = 1.0
    while server.active_job_count > 0 and waited < timeout:
        logger.info("⏳ 진행 중인 변환 작업 %d건이 끝나기를 기다리는 중... (%.0fs 경과)",
                    server.active_job_count, waited)
        time.sleep(interval)
        waited += interval

    if server.active_job_count > 0:
        logger.warning("⚠️ %d건의 작업이 끝나지 않았지만 종료를 진행합니다", server.active_job_count)

    server.server_close()
    logger.info("✅ 변환기를 안전하게 종료했습니다")


def main():
    settings = load_web_settings()
    server = ConverterServer((HOST, DEFAULT_PORT), ConverterHandler, settings)
    url = f"http://{HOST}:{server.server_port}/"
    logger.info("🚀 PsO 변환기 v%s 실행: %s", get_app_version(), url)
    logger.info("🔒 SAV 파일은 이 PC 안에서만 처리됩니다")
    if os.environ.get("PSO_NO_BROWSER") != "1":
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    shutdown_event = threading.Event()
    _install_shutdown_handlers(shutdown_event)

    server_thread = threading.Thread(target=server.serve_forever, name="pso-http-server", daemon=True)
    server_thread.start()

    try:
        while not shutdown_event.is_set():
            shutdown_event.wait(0.5)
    except KeyboardInterrupt:
        # signal 핸들러가 걸리지 않는 환경을 위한 안전망
        logger.info("🛑 Ctrl+C를 감지했습니다")
    finally:
        _graceful_shutdown(server, timeout=60.0)
        server_thread.join(timeout=5)


if __name__ == "__main__":
    main()
