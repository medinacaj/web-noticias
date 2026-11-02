/* Preferencias locales compartidas con el portal; sin red ni historial de lectura. */
(function () {
  'use strict';
  var root=document.documentElement, size=document.getElementById('reading-size');
  var button=document.getElementById('reading-theme'), preference='light';
  function read(key,fallback){try{return localStorage.getItem(key)||fallback;}catch(e){return fallback;}}
  function save(key,value){try{localStorage.setItem(key,value);}catch(e){}}
  function theme(value){
    preference=['light','dark','system'].indexOf(value)>=0?value:'light';
    root.dataset.theme=preference==='system'?(matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light'):preference;
    button.setAttribute('aria-label',root.dataset.theme==='dark'?'Cambiar al modo claro':'Cambiar al modo oscuro');
  }
  function text(value){size.value=['small','normal','large'].indexOf(value)>=0?value:'normal';root.dataset.textSize=size.value;}
  theme(read('noticias:theme:v1','light'));text(read('noticias:text-size:v1','normal'));
  size.addEventListener('change',function(){text(size.value);save('noticias:text-size:v1',size.value);});
  button.addEventListener('click',function(){var value=root.dataset.theme==='dark'?'light':'dark';theme(value);save('noticias:theme:v1',value);});
  matchMedia('(prefers-color-scheme:dark)').addEventListener('change',function(){if(preference==='system')theme(preference);});
  function columns(){
    var choice=read('noticias:columns:v1','auto'), maximum=['2','3','4'].indexOf(choice)>=0?Number(choice):3;
    document.querySelectorAll('.reading-list:not(.brief-list)').forEach(function(list){
      list.style.setProperty('--columns',String(Math.max(1,Math.min(maximum,Math.floor((list.clientWidth+12)/312)))));
    });
  }
  columns();window.addEventListener('resize',columns);
}());
