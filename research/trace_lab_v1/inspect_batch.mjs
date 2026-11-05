// Test harness only; the public browser inspector has no submitted-code interface.
import {readFileSync} from 'node:fs';
import {inspectCase} from '../flux_detective_v1/inspector.mjs';
const inputs=JSON.parse(readFileSync(0,'utf8'));
process.stdout.write(JSON.stringify(inputs.map(raw=>{try{return {result:inspectCase(raw)};}catch(error){return {error:error.message};}}))+'\n');
