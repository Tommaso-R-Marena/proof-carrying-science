/*
 * Fixed screened-graph float32 evaluator for independent numerical differential
 * testing. It is not an ONNX parser, a sandbox, a verified compiler, or PCS
 * authority. Python serializes a screened graph into this bounded protocol.
 * Compilation requires -fno-fast-math -ffp-contract=off, and round-to-nearest.
 */
#pragma STDC FENV_ACCESS ON
#pragma STDC FP_CONTRACT OFF
#include <fenv.h>
#include <float.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define WIDTH 16
#define NODES 64
#define SLOTS (NODES + 1)
static float activation[SLOTS][WIDTH];
static unsigned lengths[SLOTS];

static float decode(uint32_t u) {
  float f;
  memcpy(&f,&u,sizeof(f));
  return f;
}
static uint32_t encode(float f) {
  uint32_t u;
  memcpy(&u,&f,sizeof(u));
  return u;
}
static int readword(uint32_t *out) {
  unsigned int u;
  if (scanf("%u", &u) != 1) return 0;
  *out = (uint32_t)u;
  return 1;
}
static int fin(float f) { return isfinite(f); }
static int read_float(float *out) {
  uint32_t u;
  if (!readword(&u)) return 0;
  float f = decode(u);
  if (!fin(f)) return 0;
  *out=f;
  return 1;
}
int main(void) {
  char magic[16];
  unsigned ni,nn,output_slot,no;
  if (scanf("%15s %u %u %u %u",magic,&ni,&nn,&output_slot,&no)!=5 ||
      strcmp(magic,"PCS32V1") || ni==0 || ni>WIDTH || nn>NODES ||
      output_slot>nn || no==0 || no>WIDTH) return 11;
  if (sizeof(float)!=4 || FLT_RADIX!=2 || FLT_MANT_DIG!=24 ||
      FLT_MAX_EXP!=128 || fesetround(FE_TONEAREST) ||
      fegetround()!=FE_TONEAREST) return 12;
  volatile float minsub=decode(UINT32_C(1));
  volatile float one=1.0f;
  volatile float denorm=minsub*one;
  if (encode(denorm)!=UINT32_C(1)) return 13; /* reject DAZ/FTZ */
  lengths[0]=ni;
  for (unsigned j=0;j<ni;j++) {
    if(!read_float(&activation[0][j])) return 14;
  }
  for (unsigned i=0;i<nn;i++) {
    unsigned op,a,b,n,m;
    if(scanf("%u %u %u %u %u",&op,&a,&b,&n,&m)!=5 ||
       a>i || b>i || n>WIDTH || m>WIDTH || n==0 || m==0 ||
       lengths[a]!=n) return 15;
    unsigned dest=i+1;
    if (op==1 || op==2) { /* MatMul / Gemm */
      float w[WIDTH][WIDTH];
      for (unsigned row=0;row<n;row++)
        for (unsigned col=0;col<m;col++)
          if(!read_float(&w[row][col])) return 16;
      float bias[WIDTH]={0};
      if (op==2) for(unsigned col=0;col<m;col++)
        if(!read_float(&bias[col])) return 17;
      for (unsigned col=0;col<m;col++) {
        volatile float acc=0.0f;
        for (unsigned row=0;row<n;row++) {
          volatile float p=activation[a][row]*w[row][col];
          volatile float z=acc+p;
          acc=z;
          if (!fin(acc)) return 18;
        }
        if(op==2){ volatile float z=acc+bias[col];acc=z; }
        if (!fin(acc)) return 19;
        activation[dest][col]=acc;
      }
      lengths[dest]=m;
    } else if (op==3) { /* Add dynamic + dynamic */
      if(lengths[b]!=n || m!=n) return 20;
      for(unsigned j=0;j<n;j++){
        volatile float v=activation[a][j]+activation[b][j];
        if(!fin(v)) return 21;
        activation[dest][j]=v;
      }
      lengths[dest]=n;
    } else if (op==4) { /* Add dynamic + constant */
      if(m!=n) return 22;
      for(unsigned j=0;j<n;j++){
        float c;
        if(!read_float(&c)) return 23;
        volatile float v=activation[a][j]+c;
        if(!fin(v)) return 24;
        activation[dest][j]=v;
      }
      lengths[dest]=n;
    } else if (op==5 || op==6) { /* ReLU / Identity */
      if (m!=n) return 25;
      for(unsigned j=0;j<n;j++) {
        float v=activation[a][j];
        activation[dest][j]=(op==5 && v<0.0f)?0.0f:v;
      }
      lengths[dest]=n;
    } else return 26;
  }
  if(lengths[output_slot]!=no) return 27;
  for(unsigned j=0;j<no;j++)
    printf("%08x%s", encode(activation[output_slot][j]), j+1==no?"\n":" ");
  return 0;
}
