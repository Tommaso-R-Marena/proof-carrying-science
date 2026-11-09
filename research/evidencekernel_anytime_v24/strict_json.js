'use strict';
/* Strict cross-language JSON reader for security-relevant certificates.
 * JSON.parse silently accepts duplicate object keys; this pass rejects them,
 * along with floating point literals, unsafe integers and lone surrogates.
 * JSON.parse remains the standards-conformant syntax/type parser.
 */
const fs=require('node:fs');
const assert=require('node:assert/strict');
function checkNoDuplicateKeys(text){
 let pos=0;
 function ws(){while(pos<text.length && /\s/.test(text[pos]))pos++;}
 function str(){
  assert.equal(text[pos],'"');let i=++pos,escaped=false;
  for(;pos<text.length;pos++){
   let c=text[pos];
   if(escaped){escaped=false;continue;}
   if(c==='\\'){escaped=true;continue;}
   if(c==='"'){
    let v=JSON.parse(text.slice(i-1,pos+1));pos++;
    // Prevent UTF-8 replacement-character disagreement for unpaired surrogates.
    for(let k=0;k<v.length;k++){
     const code=v.charCodeAt(k);
     if(code>=0xd800 && code<=0xdbff){
      assert.ok(k+1<v.length && v.charCodeAt(k+1)>=0xdc00 && v.charCodeAt(k+1)<=0xdfff,
         'unpaired high surrogate in JSON string');k++;
     }else if(code>=0xdc00 && code<=0xdfff)throw Error('unpaired low surrogate in JSON string');
    }
    return v;
   }
  }
  throw Error('unterminated JSON string');
 }
 function val(){
  ws();const c=text[pos];
  if(c==='"'){str();return;}
  if(c==='{'){
   pos++;ws();const seen=new Set();
   if(text[pos]==='}'){pos++;return;}
   while(true){
    ws();assert.equal(text[pos],'"','expected object key');const key=str();
    if(seen.has(key))throw Error(`duplicate JSON key: ${key}`);
    seen.add(key);ws();assert.equal(text[pos++],':');val();ws();
    if(text[pos]==='}'){pos++;return;}
    assert.equal(text[pos++],',');
   }
  }
  if(c==='['){
   pos++;ws();if(text[pos]===']'){pos++;return;}
   while(true){val();ws();if(text[pos]===']'){pos++;return;}
    assert.equal(text[pos++],',');}
  }
  const tail=text.slice(pos);
  const t=/^(?:true|false|null|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)/.exec(tail);
  if(!t)throw Error('invalid JSON token');
  if(/^-?[0-9]/.test(t[0]) && (/[.eE]/.test(t[0]) || !Number.isSafeInteger(Number(t[0]))))
   throw Error('JSON floating point or unsafe integer prohibited');
  pos+=t[0].length;
 }
 val();ws();assert.equal(pos,text.length,'trailing data');
}
function parseStrict(text){
 if(Buffer.byteLength(text,'utf8')>8000000)throw Error('JSON document too large');
 const value=JSON.parse(text);
 checkNoDuplicateKeys(text);
 return value;
}
function readStrict(file){
 const buffer=fs.readFileSync(file);
 if(buffer.length>8000000)throw Error('JSON document too large');
 const decoder=new TextDecoder('utf-8',{fatal:true});
 return parseStrict(decoder.decode(buffer));
}
module.exports={parseStrict,readStrict};
if(require.main===module){
 try{console.log(JSON.stringify(readStrict(process.argv[2])));}
 catch(e){console.error('REJECTED:',e.message);process.exit(2);}
}
