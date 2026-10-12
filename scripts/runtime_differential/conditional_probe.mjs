// Test-only adapter to the actual receiver-selected browser module.
import {pathToFileURL} from 'node:url';
import readline from 'node:readline';
const {checkConditional}=await import(pathToFileURL(process.argv[2]).href);
for await(const line of readline.createInterface({input:process.stdin})){
  if(Buffer.byteLength(line)>262144)throw Error('Test input exceeds bound');
  const {task,limits}=JSON.parse(line);
  try{console.log(JSON.stringify({accepted:true,receipt:await checkConditional(task,{limits})}));}
  catch(error){console.log(JSON.stringify({accepted:false,error:String(error.message)}));}
}
