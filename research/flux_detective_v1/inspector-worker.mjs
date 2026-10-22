import {inspectCase} from './inspector.mjs';
self.onmessage=event=>{
  const {id,raw}=event.data??{};
  if(!Number.isSafeInteger(id)||id<1)return;
  try{self.postMessage({id,result:inspectCase(raw)});}
  catch(error){self.postMessage({id,error:String(error.message),kernel_checked:false});}
};
