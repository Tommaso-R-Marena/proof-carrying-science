#include "RafMekErklin.h"
#include <cvodes/cvodes.h>
#include <cvodes/cvodes_band.h>
#include <cvodes/cvodes_bandpre.h>
#include <cvodes/cvodes_dense.h>
#include <cvodes/cvodes_diag.h>
#include <cvodes/cvodes_spbcgs.h>
#include <cvodes/cvodes_spgmr.h>
#include <cvodes/cvodes_sptfqmr.h>
#include <nvector/nvector_serial.h>
#include <sundials/sundials_types.h>
#include <sundials/sundials_math.h>
#include <udata.h>
#include <math.h>
#include <mex.h>


 int xdot_RafMekErklin(realtype t, N_Vector x, N_Vector xdot, void *user_data)
{
  int ix;
  UserData data = (UserData) user_data;
  double *qpositivex = data->qpositivex;
  double *p = data->p;
  double *k = data->k;
  double *u = data->u;
  double *x_tmp = N_VGetArrayPointer(x);
  double *xdot_tmp = N_VGetArrayPointer(xdot);
  memset(xdot_tmp,0,sizeof(double)*3);
  xdot_tmp[0] = -p[0]*x_tmp[0]+((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6])/(p[6]+x_tmp[2]);
  xdot_tmp[1] = -p[2]*x_tmp[1]-((x_tmp[1]-1.0)*p[3]*x_tmp[0])/(k[0]/p[10]+1.0);
  xdot_tmp[2] = -p[4]*x_tmp[2]-((x_tmp[2]-1.0)*p[5]*x_tmp[1])/(k[1]/p[11]+1.0);
  for (ix=0; ix<3; ix++) {
    if(mxIsNaN(xdot_tmp[ix])) xdot_tmp[ix] = 0.0;
    if(qpositivex[ix]>0.5 && x_tmp[ix]<0.0 && xdot_tmp[ix]<0.0) xdot_tmp[ix] = -xdot_tmp[ix];
  }

  return(0);
}


 int xBdot_RafMekErklin(realtype t, N_Vector x, N_Vector xB, N_Vector xBdot, void *user_data)
{
  int ixB;
  UserData data = (UserData) user_data;
  double *p = data->p;
  double *k = data->k;
  double *u = data->u;
  double *x_tmp = N_VGetArrayPointer(x);
  double *xB_tmp = N_VGetArrayPointer(xB);
  double *xBdot_tmp = N_VGetArrayPointer(xBdot);
  memset(xBdot_tmp,0,sizeof(double)*24);
  xBdot_tmp[0] = (p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*xB_tmp[0]+((x_tmp[1]-1.0)*p[3]*p[10]*xB_tmp[1])/(k[0]+p[10]);
  xBdot_tmp[1] = (p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*xB_tmp[1]+((x_tmp[2]-1.0)*p[5]*p[11]*xB_tmp[2])/(k[1]+p[11]);
  xBdot_tmp[2] = (p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*xB_tmp[2]+1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*xB_tmp[0];
  xBdot_tmp[3] = (p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*xB_tmp[3]+((x_tmp[1]-1.0)*p[3]*p[10]*xB_tmp[4])/(k[0]+p[10]);
  xBdot_tmp[4] = (p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*xB_tmp[4]+((x_tmp[2]-1.0)*p[5]*p[11]*xB_tmp[5])/(k[1]+p[11]);
  xBdot_tmp[5] = (p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*xB_tmp[5]+1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*xB_tmp[3];
  xBdot_tmp[6] = (p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*xB_tmp[6]+((x_tmp[1]-1.0)*p[3]*p[10]*xB_tmp[7])/(k[0]+p[10]);
  xBdot_tmp[7] = (p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*xB_tmp[7]+((x_tmp[2]-1.0)*p[5]*p[11]*xB_tmp[8])/(k[1]+p[11]);
  xBdot_tmp[8] = (p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*xB_tmp[8]+1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*xB_tmp[6];
  xBdot_tmp[9] = (p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*xB_tmp[9]+((x_tmp[1]-1.0)*p[3]*p[10]*xB_tmp[10])/(k[0]+p[10]);
  xBdot_tmp[10] = (p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*xB_tmp[10]+((x_tmp[2]-1.0)*p[5]*p[11]*xB_tmp[11])/(k[1]+p[11]);
  xBdot_tmp[11] = (p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*xB_tmp[11]+1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*xB_tmp[9];
  xBdot_tmp[12] = (p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*xB_tmp[12]+((x_tmp[1]-1.0)*p[3]*p[10]*xB_tmp[13])/(k[0]+p[10]);
  xBdot_tmp[13] = (p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*xB_tmp[13]+((x_tmp[2]-1.0)*p[5]*p[11]*xB_tmp[14])/(k[1]+p[11]);
  xBdot_tmp[14] = (p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*xB_tmp[14]+1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*xB_tmp[12];
  xBdot_tmp[15] = (p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*xB_tmp[15]+((x_tmp[1]-1.0)*p[3]*p[10]*xB_tmp[16])/(k[0]+p[10]);
  xBdot_tmp[16] = (p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*xB_tmp[16]+((x_tmp[2]-1.0)*p[5]*p[11]*xB_tmp[17])/(k[1]+p[11]);
  xBdot_tmp[17] = (p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*xB_tmp[17]+1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*xB_tmp[15];
  xBdot_tmp[18] = (p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*xB_tmp[18]+((x_tmp[1]-1.0)*p[3]*p[10]*xB_tmp[19])/(k[0]+p[10]);
  xBdot_tmp[19] = (p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*xB_tmp[19]+((x_tmp[2]-1.0)*p[5]*p[11]*xB_tmp[20])/(k[1]+p[11]);
  xBdot_tmp[20] = (p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*xB_tmp[20]+1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*xB_tmp[18];
  xBdot_tmp[21] = (p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*xB_tmp[21]+((x_tmp[1]-1.0)*p[3]*p[10]*xB_tmp[22])/(k[0]+p[10]);
  xBdot_tmp[22] = (p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*xB_tmp[22]+((x_tmp[2]-1.0)*p[5]*p[11]*xB_tmp[23])/(k[1]+p[11]);
  xBdot_tmp[23] = (p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*xB_tmp[23]+1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*xB_tmp[21];
  for (ixB=0; ixB<24; ixB++) {
    if(mxIsNaN(xBdot_tmp[ixB])) xBdot_tmp[ixB] = 0.0;
  }

  return(0);
}


 int xQB_RafMekErklin(realtype t, N_Vector x, N_Vector xB, N_Vector qBdot, void *user_data)
{
  int iyp;
  int ip;
  UserData data = (UserData) user_data;
  double *p = data->p;
  int *plist = data->plist;
  int np = *data->np;
  int ny = *data->ny;
  double *k = data->k;
  double *u = data->u;
  double *x_tmp = N_VGetArrayPointer(x);
  double *xB_tmp = N_VGetArrayPointer(xB);
  double *qBdot_tmp = N_VGetArrayPointer(qBdot);
  memset(qBdot_tmp,0,sizeof(double)*8*np);
  for(ip=0; ip<np; ip++) {
  switch (plist[ip]) {
  case 0: {
  qBdot_tmp[0+ip*ny] = x_tmp[0]*xB_tmp[0];
  qBdot_tmp[1+ip*ny] = x_tmp[0]*xB_tmp[3];
  qBdot_tmp[2+ip*ny] = x_tmp[0]*xB_tmp[6];
  qBdot_tmp[3+ip*ny] = x_tmp[0]*xB_tmp[9];
  qBdot_tmp[4+ip*ny] = x_tmp[0]*xB_tmp[12];
  qBdot_tmp[5+ip*ny] = x_tmp[0]*xB_tmp[15];
  qBdot_tmp[6+ip*ny] = x_tmp[0]*xB_tmp[18];
  qBdot_tmp[7+ip*ny] = x_tmp[0]*xB_tmp[21];
  } break;

  case 1: {
  qBdot_tmp[0+ip*ny] = -((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[6]*xB_tmp[0])/(p[6]+x_tmp[2]);
  qBdot_tmp[1+ip*ny] = -((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[6]*xB_tmp[3])/(p[6]+x_tmp[2]);
  qBdot_tmp[2+ip*ny] = -((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[6]*xB_tmp[6])/(p[6]+x_tmp[2]);
  qBdot_tmp[3+ip*ny] = -((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[6]*xB_tmp[9])/(p[6]+x_tmp[2]);
  qBdot_tmp[4+ip*ny] = -((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[6]*xB_tmp[12])/(p[6]+x_tmp[2]);
  qBdot_tmp[5+ip*ny] = -((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[6]*xB_tmp[15])/(p[6]+x_tmp[2]);
  qBdot_tmp[6+ip*ny] = -((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[6]*xB_tmp[18])/(p[6]+x_tmp[2]);
  qBdot_tmp[7+ip*ny] = -((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[6]*xB_tmp[21])/(p[6]+x_tmp[2]);
  } break;

  case 2: {
  qBdot_tmp[0+ip*ny] = x_tmp[1]*xB_tmp[1];
  qBdot_tmp[1+ip*ny] = x_tmp[1]*xB_tmp[4];
  qBdot_tmp[2+ip*ny] = x_tmp[1]*xB_tmp[7];
  qBdot_tmp[3+ip*ny] = x_tmp[1]*xB_tmp[10];
  qBdot_tmp[4+ip*ny] = x_tmp[1]*xB_tmp[13];
  qBdot_tmp[5+ip*ny] = x_tmp[1]*xB_tmp[16];
  qBdot_tmp[6+ip*ny] = x_tmp[1]*xB_tmp[19];
  qBdot_tmp[7+ip*ny] = x_tmp[1]*xB_tmp[22];
  } break;

  case 3: {
  qBdot_tmp[0+ip*ny] = ((x_tmp[1]-1.0)*p[10]*x_tmp[0]*xB_tmp[1])/(k[0]+p[10]);
  qBdot_tmp[1+ip*ny] = ((x_tmp[1]-1.0)*p[10]*x_tmp[0]*xB_tmp[4])/(k[0]+p[10]);
  qBdot_tmp[2+ip*ny] = ((x_tmp[1]-1.0)*p[10]*x_tmp[0]*xB_tmp[7])/(k[0]+p[10]);
  qBdot_tmp[3+ip*ny] = ((x_tmp[1]-1.0)*p[10]*x_tmp[0]*xB_tmp[10])/(k[0]+p[10]);
  qBdot_tmp[4+ip*ny] = ((x_tmp[1]-1.0)*p[10]*x_tmp[0]*xB_tmp[13])/(k[0]+p[10]);
  qBdot_tmp[5+ip*ny] = ((x_tmp[1]-1.0)*p[10]*x_tmp[0]*xB_tmp[16])/(k[0]+p[10]);
  qBdot_tmp[6+ip*ny] = ((x_tmp[1]-1.0)*p[10]*x_tmp[0]*xB_tmp[19])/(k[0]+p[10]);
  qBdot_tmp[7+ip*ny] = ((x_tmp[1]-1.0)*p[10]*x_tmp[0]*xB_tmp[22])/(k[0]+p[10]);
  } break;

  case 4: {
  qBdot_tmp[0+ip*ny] = x_tmp[2]*xB_tmp[2];
  qBdot_tmp[1+ip*ny] = x_tmp[2]*xB_tmp[5];
  qBdot_tmp[2+ip*ny] = x_tmp[2]*xB_tmp[8];
  qBdot_tmp[3+ip*ny] = x_tmp[2]*xB_tmp[11];
  qBdot_tmp[4+ip*ny] = x_tmp[2]*xB_tmp[14];
  qBdot_tmp[5+ip*ny] = x_tmp[2]*xB_tmp[17];
  qBdot_tmp[6+ip*ny] = x_tmp[2]*xB_tmp[20];
  qBdot_tmp[7+ip*ny] = x_tmp[2]*xB_tmp[23];
  } break;

  case 5: {
  qBdot_tmp[0+ip*ny] = ((x_tmp[2]-1.0)*p[11]*x_tmp[1]*xB_tmp[2])/(k[1]+p[11]);
  qBdot_tmp[1+ip*ny] = ((x_tmp[2]-1.0)*p[11]*x_tmp[1]*xB_tmp[5])/(k[1]+p[11]);
  qBdot_tmp[2+ip*ny] = ((x_tmp[2]-1.0)*p[11]*x_tmp[1]*xB_tmp[8])/(k[1]+p[11]);
  qBdot_tmp[3+ip*ny] = ((x_tmp[2]-1.0)*p[11]*x_tmp[1]*xB_tmp[11])/(k[1]+p[11]);
  qBdot_tmp[4+ip*ny] = ((x_tmp[2]-1.0)*p[11]*x_tmp[1]*xB_tmp[14])/(k[1]+p[11]);
  qBdot_tmp[5+ip*ny] = ((x_tmp[2]-1.0)*p[11]*x_tmp[1]*xB_tmp[17])/(k[1]+p[11]);
  qBdot_tmp[6+ip*ny] = ((x_tmp[2]-1.0)*p[11]*x_tmp[1]*xB_tmp[20])/(k[1]+p[11]);
  qBdot_tmp[7+ip*ny] = ((x_tmp[2]-1.0)*p[11]*x_tmp[1]*xB_tmp[23])/(k[1]+p[11]);
  } break;

  case 6: {
  qBdot_tmp[0+ip*ny] = -xB_tmp[0]*(((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1])/(p[6]+x_tmp[2])-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]);
  qBdot_tmp[1+ip*ny] = -xB_tmp[3]*(((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1])/(p[6]+x_tmp[2])-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]);
  qBdot_tmp[2+ip*ny] = -xB_tmp[6]*(((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1])/(p[6]+x_tmp[2])-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]);
  qBdot_tmp[3+ip*ny] = -xB_tmp[9]*(((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1])/(p[6]+x_tmp[2])-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]);
  qBdot_tmp[4+ip*ny] = -xB_tmp[12]*(((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1])/(p[6]+x_tmp[2])-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]);
  qBdot_tmp[5+ip*ny] = -xB_tmp[15]*(((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1])/(p[6]+x_tmp[2])-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]);
  qBdot_tmp[6+ip*ny] = -xB_tmp[18]*(((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1])/(p[6]+x_tmp[2])-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]);
  qBdot_tmp[7+ip*ny] = -xB_tmp[21]*(((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1])/(p[6]+x_tmp[2])-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]);
  } break;

  case 7: {
  qBdot_tmp[0+ip*ny] = ((x_tmp[0]-1.0)*p[1]*p[6]*xB_tmp[0])/(p[6]+x_tmp[2]);
  qBdot_tmp[1+ip*ny] = ((x_tmp[0]-1.0)*p[1]*p[6]*xB_tmp[3])/(p[6]+x_tmp[2]);
  qBdot_tmp[2+ip*ny] = ((x_tmp[0]-1.0)*p[1]*p[6]*xB_tmp[6])/(p[6]+x_tmp[2]);
  qBdot_tmp[3+ip*ny] = ((x_tmp[0]-1.0)*p[1]*p[6]*xB_tmp[9])/(p[6]+x_tmp[2]);
  qBdot_tmp[4+ip*ny] = ((x_tmp[0]-1.0)*p[1]*p[6]*xB_tmp[12])/(p[6]+x_tmp[2]);
  qBdot_tmp[5+ip*ny] = ((x_tmp[0]-1.0)*p[1]*p[6]*xB_tmp[15])/(p[6]+x_tmp[2]);
  qBdot_tmp[6+ip*ny] = ((x_tmp[0]-1.0)*p[1]*p[6]*xB_tmp[18])/(p[6]+x_tmp[2]);
  qBdot_tmp[7+ip*ny] = ((x_tmp[0]-1.0)*p[1]*p[6]*xB_tmp[21])/(p[6]+x_tmp[2]);
  } break;

  case 8: {
  qBdot_tmp[0+ip*ny] = -(t*exp(-t/p[8])*exp(-t/p[9])*(x_tmp[0]-1.0)*p[1]*p[6]*1.0/(p[8]*p[8])*xB_tmp[0])/(p[6]+x_tmp[2]);
  qBdot_tmp[1+ip*ny] = -(t*exp(-t/p[8])*exp(-t/p[9])*(x_tmp[0]-1.0)*p[1]*p[6]*1.0/(p[8]*p[8])*xB_tmp[3])/(p[6]+x_tmp[2]);
  qBdot_tmp[2+ip*ny] = -(t*exp(-t/p[8])*exp(-t/p[9])*(x_tmp[0]-1.0)*p[1]*p[6]*1.0/(p[8]*p[8])*xB_tmp[6])/(p[6]+x_tmp[2]);
  qBdot_tmp[3+ip*ny] = -(t*exp(-t/p[8])*exp(-t/p[9])*(x_tmp[0]-1.0)*p[1]*p[6]*1.0/(p[8]*p[8])*xB_tmp[9])/(p[6]+x_tmp[2]);
  qBdot_tmp[4+ip*ny] = -(t*exp(-t/p[8])*exp(-t/p[9])*(x_tmp[0]-1.0)*p[1]*p[6]*1.0/(p[8]*p[8])*xB_tmp[12])/(p[6]+x_tmp[2]);
  qBdot_tmp[5+ip*ny] = -(t*exp(-t/p[8])*exp(-t/p[9])*(x_tmp[0]-1.0)*p[1]*p[6]*1.0/(p[8]*p[8])*xB_tmp[15])/(p[6]+x_tmp[2]);
  qBdot_tmp[6+ip*ny] = -(t*exp(-t/p[8])*exp(-t/p[9])*(x_tmp[0]-1.0)*p[1]*p[6]*1.0/(p[8]*p[8])*xB_tmp[18])/(p[6]+x_tmp[2]);
  qBdot_tmp[7+ip*ny] = -(t*exp(-t/p[8])*exp(-t/p[9])*(x_tmp[0]-1.0)*p[1]*p[6]*1.0/(p[8]*p[8])*xB_tmp[21])/(p[6]+x_tmp[2]);
  } break;

  case 9: {
  qBdot_tmp[0+ip*ny] = -(t*exp(-t/p[9])*(x_tmp[0]-1.0)*(exp(-t/p[8])-1.0)*p[1]*p[6]*1.0/(p[9]*p[9])*xB_tmp[0])/(p[6]+x_tmp[2]);
  qBdot_tmp[1+ip*ny] = -(t*exp(-t/p[9])*(x_tmp[0]-1.0)*(exp(-t/p[8])-1.0)*p[1]*p[6]*1.0/(p[9]*p[9])*xB_tmp[3])/(p[6]+x_tmp[2]);
  qBdot_tmp[2+ip*ny] = -(t*exp(-t/p[9])*(x_tmp[0]-1.0)*(exp(-t/p[8])-1.0)*p[1]*p[6]*1.0/(p[9]*p[9])*xB_tmp[6])/(p[6]+x_tmp[2]);
  qBdot_tmp[3+ip*ny] = -(t*exp(-t/p[9])*(x_tmp[0]-1.0)*(exp(-t/p[8])-1.0)*p[1]*p[6]*1.0/(p[9]*p[9])*xB_tmp[9])/(p[6]+x_tmp[2]);
  qBdot_tmp[4+ip*ny] = -(t*exp(-t/p[9])*(x_tmp[0]-1.0)*(exp(-t/p[8])-1.0)*p[1]*p[6]*1.0/(p[9]*p[9])*xB_tmp[12])/(p[6]+x_tmp[2]);
  qBdot_tmp[5+ip*ny] = -(t*exp(-t/p[9])*(x_tmp[0]-1.0)*(exp(-t/p[8])-1.0)*p[1]*p[6]*1.0/(p[9]*p[9])*xB_tmp[15])/(p[6]+x_tmp[2]);
  qBdot_tmp[6+ip*ny] = -(t*exp(-t/p[9])*(x_tmp[0]-1.0)*(exp(-t/p[8])-1.0)*p[1]*p[6]*1.0/(p[9]*p[9])*xB_tmp[18])/(p[6]+x_tmp[2]);
  qBdot_tmp[7+ip*ny] = -(t*exp(-t/p[9])*(x_tmp[0]-1.0)*(exp(-t/p[8])-1.0)*p[1]*p[6]*1.0/(p[9]*p[9])*xB_tmp[21])/(p[6]+x_tmp[2]);
  } break;

  case 10: {
  qBdot_tmp[0+ip*ny] = (x_tmp[1]-1.0)*k[0]*p[3]*x_tmp[0]*xB_tmp[1]*1.0/pow(k[0]+p[10],2.0);
  qBdot_tmp[1+ip*ny] = (x_tmp[1]-1.0)*k[0]*p[3]*x_tmp[0]*xB_tmp[4]*1.0/pow(k[0]+p[10],2.0);
  qBdot_tmp[2+ip*ny] = (x_tmp[1]-1.0)*k[0]*p[3]*x_tmp[0]*xB_tmp[7]*1.0/pow(k[0]+p[10],2.0);
  qBdot_tmp[3+ip*ny] = (x_tmp[1]-1.0)*k[0]*p[3]*x_tmp[0]*xB_tmp[10]*1.0/pow(k[0]+p[10],2.0);
  qBdot_tmp[4+ip*ny] = (x_tmp[1]-1.0)*k[0]*p[3]*x_tmp[0]*xB_tmp[13]*1.0/pow(k[0]+p[10],2.0);
  qBdot_tmp[5+ip*ny] = (x_tmp[1]-1.0)*k[0]*p[3]*x_tmp[0]*xB_tmp[16]*1.0/pow(k[0]+p[10],2.0);
  qBdot_tmp[6+ip*ny] = (x_tmp[1]-1.0)*k[0]*p[3]*x_tmp[0]*xB_tmp[19]*1.0/pow(k[0]+p[10],2.0);
  qBdot_tmp[7+ip*ny] = (x_tmp[1]-1.0)*k[0]*p[3]*x_tmp[0]*xB_tmp[22]*1.0/pow(k[0]+p[10],2.0);
  } break;

  case 11: {
  qBdot_tmp[0+ip*ny] = (x_tmp[2]-1.0)*k[1]*p[5]*x_tmp[1]*xB_tmp[2]*1.0/pow(k[1]+p[11],2.0);
  qBdot_tmp[1+ip*ny] = (x_tmp[2]-1.0)*k[1]*p[5]*x_tmp[1]*xB_tmp[5]*1.0/pow(k[1]+p[11],2.0);
  qBdot_tmp[2+ip*ny] = (x_tmp[2]-1.0)*k[1]*p[5]*x_tmp[1]*xB_tmp[8]*1.0/pow(k[1]+p[11],2.0);
  qBdot_tmp[3+ip*ny] = (x_tmp[2]-1.0)*k[1]*p[5]*x_tmp[1]*xB_tmp[11]*1.0/pow(k[1]+p[11],2.0);
  qBdot_tmp[4+ip*ny] = (x_tmp[2]-1.0)*k[1]*p[5]*x_tmp[1]*xB_tmp[14]*1.0/pow(k[1]+p[11],2.0);
  qBdot_tmp[5+ip*ny] = (x_tmp[2]-1.0)*k[1]*p[5]*x_tmp[1]*xB_tmp[17]*1.0/pow(k[1]+p[11],2.0);
  qBdot_tmp[6+ip*ny] = (x_tmp[2]-1.0)*k[1]*p[5]*x_tmp[1]*xB_tmp[20]*1.0/pow(k[1]+p[11],2.0);
  qBdot_tmp[7+ip*ny] = (x_tmp[2]-1.0)*k[1]*p[5]*x_tmp[1]*xB_tmp[23]*1.0/pow(k[1]+p[11],2.0);
  } break;

  case 12: {

  } break;

  case 13: {

  } break;

  case 14: {

  } break;

  case 15: {

  } break;

  case 16: {

  } break;

  case 17: {

  } break;

  case 18: {

  } break;

  case 19: {

  } break;

  case 20: {

  } break;

  case 21: {

  } break;

  case 22: {

  } break;

  }
  }

  for (iyp=0; iyp<8*np; iyp++) {
    if(mxIsNaN(qBdot_tmp[iyp])) qBdot_tmp[iyp] = 0.0;
  }

  return(0);
}


 void x0_RafMekErklin(N_Vector x0, void *user_data)
{
  UserData data = (UserData) user_data;
  double *p = data->p;
  double *k = data->k;
  double *u = data->u;
  double *x0_tmp = N_VGetArrayPointer(x0);
  memset(x0_tmp,0,sizeof(double)*3);
  x0_tmp[0] = p[20];
  x0_tmp[1] = p[21];
  x0_tmp[2] = p[22];  
  
  return;
}


 int Jv_RafMekErklin(N_Vector v, N_Vector Jv, realtype t,
  	N_Vector x, N_Vector xdot, void *user_data, N_Vector tmp)
{
  int ix;
  UserData data = (UserData) user_data;
  double *p = data->p;
  double *k = data->k;
  double *u = data->u;
  double *x_tmp = N_VGetArrayPointer(x);
  double *v_tmp = N_VGetArrayPointer(v);
  double *Jv_tmp = N_VGetArrayPointer(Jv);
  memset(Jv_tmp,0,sizeof(double)*3);
  Jv_tmp[0] = -(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*v_tmp[0]-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*v_tmp[2];
  Jv_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*v_tmp[1]-((x_tmp[1]-1.0)*p[3]*p[10]*v_tmp[0])/(k[0]+p[10]);
  Jv_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*v_tmp[2]-((x_tmp[2]-1.0)*p[5]*p[11]*v_tmp[1])/(k[1]+p[11]);
  for (ix=0; ix<3; ix++) {
    if(mxIsNaN(Jv_tmp[ix])) Jv_tmp[ix] = 0.0;
  }

  return(0);
}
 int JvB_RafMekErklin(N_Vector vB, N_Vector JvB, realtype t,
  	N_Vector x, N_Vector xB, N_Vector xBdot, void *user_data, N_Vector tmpB)
{
  int ix;
  UserData data = (UserData) user_data;
  double *p = data->p;
  double *k = data->k;
  double *u = data->u;
  double *x_tmp = N_VGetArrayPointer(x);
  double *xB_tmp = N_VGetArrayPointer(xB);
  double *vB_tmp = N_VGetArrayPointer(vB);
  double *JvB_tmp = N_VGetArrayPointer(JvB);
  memset(JvB_tmp,0,sizeof(double)*3);
  JvB_tmp[0] = (p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*vB_tmp[0]+((x_tmp[1]-1.0)*p[3]*p[10]*vB_tmp[1])/(k[0]+p[10]);
  JvB_tmp[1] = (p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*vB_tmp[1]+((x_tmp[2]-1.0)*p[5]*p[11]*vB_tmp[2])/(k[1]+p[11]);
  JvB_tmp[2] = (p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*vB_tmp[2]+1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*vB_tmp[0];
  for (ix=0; ix<3; ix++) {
    if(mxIsNaN(JvB_tmp[ix])) JvB_tmp[ix] = 0.0;
  }

  return(0);
}


 int J_RafMekErklin(long int N, realtype t, N_Vector x,
  	N_Vector xdot, DlsMat J, void *user_data, 
  	N_Vector tmp1, N_Vector tmp2, N_Vector tmp3)
{
  int iJ;
  UserData data = (UserData) user_data;
  double *p = data->p;
  double *k = data->k;
  double *u = data->u;
  double *x_tmp = N_VGetArrayPointer(x);
  memset(J->data,0,sizeof(double)*9);
  J->data[0] = -p[0]+((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]);
  J->data[1] = -((x_tmp[1]-1.0)*p[3]*p[10])/(k[0]+p[10]);
  J->data[4] = -p[2]-(p[3]*x_tmp[0])/(k[0]/p[10]+1.0);
  J->data[5] = -((x_tmp[2]-1.0)*p[5]*p[11])/(k[1]+p[11]);
  J->data[6] = -1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6];
  J->data[8] = -p[4]-(p[5]*x_tmp[1])/(k[1]/p[11]+1.0);
  for (iJ=0; iJ<9; iJ++) {
    if(mxIsNaN(J->data[iJ])) J->data[iJ] = 0.0;
  }

  return(0);
}


 int JB_RafMekErklin(long int NeqB, realtype t, N_Vector x,
  	N_Vector xB, N_Vector xdotB, DlsMat JB, void *user_data, 
  	N_Vector tmp1B, N_Vector tmp2B, N_Vector tmp3B)
{
  int iJ;
  UserData data = (UserData) user_data;
  double *p = data->p;
  double *k = data->k;
  double *u = data->u;
  double *x_tmp = N_VGetArrayPointer(x);
  double *xB_tmp = N_VGetArrayPointer(xB);
  memset(JB->data,0,sizeof(double)*9);
  JB->data[0] = -p[0]+((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]);
  JB->data[1] = -((x_tmp[1]-1.0)*p[3]*p[10])/(k[0]+p[10]);
  JB->data[4] = -p[2]-(p[3]*x_tmp[0])/(k[0]/p[10]+1.0);
  JB->data[5] = -((x_tmp[2]-1.0)*p[5]*p[11])/(k[1]+p[11]);
  JB->data[6] = -1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6];
  JB->data[8] = -p[4]-(p[5]*x_tmp[1])/(k[1]/p[11]+1.0);
  for (iJ=0; iJ<9; iJ++) {
    if(mxIsNaN(JB->data[iJ])) JB->data[iJ] = 0.0;
  }

  return(0);
}


 int sx_RafMekErklin(int Ns, realtype t, N_Vector x, N_Vector xdot,
  	int ip, N_Vector sx, N_Vector sxdot, void *user_data, 
  	N_Vector tmp1, N_Vector tmp2)
{
  int ix;
  UserData data = (UserData) user_data;
  double *p = data->p;
  int *plist = data->plist;
  double *k = data->k;
  double *u = data->u;
  double *x_tmp = N_VGetArrayPointer(x);
  double *sx_tmp = N_VGetArrayPointer(sx);
  double *sxdot_tmp = N_VGetArrayPointer(sxdot);
  switch (plist[ip]) {
  case 0: {
  memset(sxdot_tmp,0,sizeof(double)*3);
  sxdot_tmp[0] = -x_tmp[0]-(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*sx_tmp[0]-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*sx_tmp[2];
  sxdot_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*sx_tmp[1]-((x_tmp[1]-1.0)*p[3]*p[10]*sx_tmp[0])/(k[0]+p[10]);
  sxdot_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*sx_tmp[2]-((x_tmp[2]-1.0)*p[5]*p[11]*sx_tmp[1])/(k[1]+p[11]);
  } break;

  case 1: {
  memset(sxdot_tmp,0,sizeof(double)*3);
  sxdot_tmp[0] = -(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*sx_tmp[0]+((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[6])/(p[6]+x_tmp[2])-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*sx_tmp[2];
  sxdot_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*sx_tmp[1]-((x_tmp[1]-1.0)*p[3]*p[10]*sx_tmp[0])/(k[0]+p[10]);
  sxdot_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*sx_tmp[2]-((x_tmp[2]-1.0)*p[5]*p[11]*sx_tmp[1])/(k[1]+p[11]);
  } break;

  case 2: {
  memset(sxdot_tmp,0,sizeof(double)*3);
  sxdot_tmp[0] = -(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*sx_tmp[0]-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*sx_tmp[2];
  sxdot_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*sx_tmp[1]-x_tmp[1]-((x_tmp[1]-1.0)*p[3]*p[10]*sx_tmp[0])/(k[0]+p[10]);
  sxdot_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*sx_tmp[2]-((x_tmp[2]-1.0)*p[5]*p[11]*sx_tmp[1])/(k[1]+p[11]);
  } break;

  case 3: {
  memset(sxdot_tmp,0,sizeof(double)*3);
  sxdot_tmp[0] = -(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*sx_tmp[0]-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*sx_tmp[2];
  sxdot_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*sx_tmp[1]-((x_tmp[1]-1.0)*p[10]*x_tmp[0])/(k[0]+p[10])-((x_tmp[1]-1.0)*p[3]*p[10]*sx_tmp[0])/(k[0]+p[10]);
  sxdot_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*sx_tmp[2]-((x_tmp[2]-1.0)*p[5]*p[11]*sx_tmp[1])/(k[1]+p[11]);
  } break;

  case 4: {
  memset(sxdot_tmp,0,sizeof(double)*3);
  sxdot_tmp[0] = -(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*sx_tmp[0]-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*sx_tmp[2];
  sxdot_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*sx_tmp[1]-((x_tmp[1]-1.0)*p[3]*p[10]*sx_tmp[0])/(k[0]+p[10]);
  sxdot_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*sx_tmp[2]-x_tmp[2]-((x_tmp[2]-1.0)*p[5]*p[11]*sx_tmp[1])/(k[1]+p[11]);
  } break;

  case 5: {
  memset(sxdot_tmp,0,sizeof(double)*3);
  sxdot_tmp[0] = -(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*sx_tmp[0]-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*sx_tmp[2];
  sxdot_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*sx_tmp[1]-((x_tmp[1]-1.0)*p[3]*p[10]*sx_tmp[0])/(k[0]+p[10]);
  sxdot_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*sx_tmp[2]-((x_tmp[2]-1.0)*p[11]*x_tmp[1])/(k[1]+p[11])-((x_tmp[2]-1.0)*p[5]*p[11]*sx_tmp[1])/(k[1]+p[11]);
  } break;

  case 6: {
  memset(sxdot_tmp,0,sizeof(double)*3);
  sxdot_tmp[0] = -(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*sx_tmp[0]+((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1])/(p[6]+x_tmp[2])-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*sx_tmp[2];
  sxdot_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*sx_tmp[1]-((x_tmp[1]-1.0)*p[3]*p[10]*sx_tmp[0])/(k[0]+p[10]);
  sxdot_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*sx_tmp[2]-((x_tmp[2]-1.0)*p[5]*p[11]*sx_tmp[1])/(k[1]+p[11]);
  } break;

  case 7: {
  memset(sxdot_tmp,0,sizeof(double)*3);
  sxdot_tmp[0] = -(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*sx_tmp[0]-((x_tmp[0]-1.0)*p[1]*p[6])/(p[6]+x_tmp[2])-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*sx_tmp[2];
  sxdot_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*sx_tmp[1]-((x_tmp[1]-1.0)*p[3]*p[10]*sx_tmp[0])/(k[0]+p[10]);
  sxdot_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*sx_tmp[2]-((x_tmp[2]-1.0)*p[5]*p[11]*sx_tmp[1])/(k[1]+p[11]);
  } break;

  case 8: {
  memset(sxdot_tmp,0,sizeof(double)*3);
  sxdot_tmp[0] = -(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*sx_tmp[0]-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*sx_tmp[2]+(t*exp(-t/p[8])*exp(-t/p[9])*(x_tmp[0]-1.0)*p[1]*p[6]*1.0/(p[8]*p[8]))/(p[6]+x_tmp[2]);
  sxdot_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*sx_tmp[1]-((x_tmp[1]-1.0)*p[3]*p[10]*sx_tmp[0])/(k[0]+p[10]);
  sxdot_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*sx_tmp[2]-((x_tmp[2]-1.0)*p[5]*p[11]*sx_tmp[1])/(k[1]+p[11]);
  } break;

  case 9: {
  memset(sxdot_tmp,0,sizeof(double)*3);
  sxdot_tmp[0] = -(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*sx_tmp[0]-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*sx_tmp[2]+(t*exp(-t/p[9])*(x_tmp[0]-1.0)*(exp(-t/p[8])-1.0)*p[1]*p[6]*1.0/(p[9]*p[9]))/(p[6]+x_tmp[2]);
  sxdot_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*sx_tmp[1]-((x_tmp[1]-1.0)*p[3]*p[10]*sx_tmp[0])/(k[0]+p[10]);
  sxdot_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*sx_tmp[2]-((x_tmp[2]-1.0)*p[5]*p[11]*sx_tmp[1])/(k[1]+p[11]);
  } break;

  case 10: {
  memset(sxdot_tmp,0,sizeof(double)*3);
  sxdot_tmp[0] = -(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*sx_tmp[0]-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*sx_tmp[2];
  sxdot_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*sx_tmp[1]-(x_tmp[1]-1.0)*k[0]*p[3]*x_tmp[0]*1.0/pow(k[0]+p[10],2.0)-((x_tmp[1]-1.0)*p[3]*p[10]*sx_tmp[0])/(k[0]+p[10]);
  sxdot_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*sx_tmp[2]-((x_tmp[2]-1.0)*p[5]*p[11]*sx_tmp[1])/(k[1]+p[11]);
  } break;

  case 11: {
  memset(sxdot_tmp,0,sizeof(double)*3);
  sxdot_tmp[0] = -(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*sx_tmp[0]-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*sx_tmp[2];
  sxdot_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*sx_tmp[1]-((x_tmp[1]-1.0)*p[3]*p[10]*sx_tmp[0])/(k[0]+p[10]);
  sxdot_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*sx_tmp[2]-(x_tmp[2]-1.0)*k[1]*p[5]*x_tmp[1]*1.0/pow(k[1]+p[11],2.0)-((x_tmp[2]-1.0)*p[5]*p[11]*sx_tmp[1])/(k[1]+p[11]);
  } break;

  case 12: {
  memset(sxdot_tmp,0,sizeof(double)*3);
  sxdot_tmp[0] = -(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*sx_tmp[0]-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*sx_tmp[2];
  sxdot_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*sx_tmp[1]-((x_tmp[1]-1.0)*p[3]*p[10]*sx_tmp[0])/(k[0]+p[10]);
  sxdot_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*sx_tmp[2]-((x_tmp[2]-1.0)*p[5]*p[11]*sx_tmp[1])/(k[1]+p[11]);
  } break;

  case 13: {
  memset(sxdot_tmp,0,sizeof(double)*3);
  sxdot_tmp[0] = -(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*sx_tmp[0]-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*sx_tmp[2];
  sxdot_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*sx_tmp[1]-((x_tmp[1]-1.0)*p[3]*p[10]*sx_tmp[0])/(k[0]+p[10]);
  sxdot_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*sx_tmp[2]-((x_tmp[2]-1.0)*p[5]*p[11]*sx_tmp[1])/(k[1]+p[11]);
  } break;

  case 14: {
  memset(sxdot_tmp,0,sizeof(double)*3);
  sxdot_tmp[0] = -(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*sx_tmp[0]-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*sx_tmp[2];
  sxdot_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*sx_tmp[1]-((x_tmp[1]-1.0)*p[3]*p[10]*sx_tmp[0])/(k[0]+p[10]);
  sxdot_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*sx_tmp[2]-((x_tmp[2]-1.0)*p[5]*p[11]*sx_tmp[1])/(k[1]+p[11]);
  } break;

  case 15: {
  memset(sxdot_tmp,0,sizeof(double)*3);
  sxdot_tmp[0] = -(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*sx_tmp[0]-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*sx_tmp[2];
  sxdot_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*sx_tmp[1]-((x_tmp[1]-1.0)*p[3]*p[10]*sx_tmp[0])/(k[0]+p[10]);
  sxdot_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*sx_tmp[2]-((x_tmp[2]-1.0)*p[5]*p[11]*sx_tmp[1])/(k[1]+p[11]);
  } break;

  case 16: {
  memset(sxdot_tmp,0,sizeof(double)*3);
  sxdot_tmp[0] = -(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*sx_tmp[0]-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*sx_tmp[2];
  sxdot_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*sx_tmp[1]-((x_tmp[1]-1.0)*p[3]*p[10]*sx_tmp[0])/(k[0]+p[10]);
  sxdot_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*sx_tmp[2]-((x_tmp[2]-1.0)*p[5]*p[11]*sx_tmp[1])/(k[1]+p[11]);
  } break;

  case 17: {
  memset(sxdot_tmp,0,sizeof(double)*3);
  sxdot_tmp[0] = -(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*sx_tmp[0]-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*sx_tmp[2];
  sxdot_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*sx_tmp[1]-((x_tmp[1]-1.0)*p[3]*p[10]*sx_tmp[0])/(k[0]+p[10]);
  sxdot_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*sx_tmp[2]-((x_tmp[2]-1.0)*p[5]*p[11]*sx_tmp[1])/(k[1]+p[11]);
  } break;

  case 18: {
  memset(sxdot_tmp,0,sizeof(double)*3);
  sxdot_tmp[0] = -(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*sx_tmp[0]-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*sx_tmp[2];
  sxdot_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*sx_tmp[1]-((x_tmp[1]-1.0)*p[3]*p[10]*sx_tmp[0])/(k[0]+p[10]);
  sxdot_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*sx_tmp[2]-((x_tmp[2]-1.0)*p[5]*p[11]*sx_tmp[1])/(k[1]+p[11]);
  } break;

  case 19: {
  memset(sxdot_tmp,0,sizeof(double)*3);
  sxdot_tmp[0] = -(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*sx_tmp[0]-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*sx_tmp[2];
  sxdot_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*sx_tmp[1]-((x_tmp[1]-1.0)*p[3]*p[10]*sx_tmp[0])/(k[0]+p[10]);
  sxdot_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*sx_tmp[2]-((x_tmp[2]-1.0)*p[5]*p[11]*sx_tmp[1])/(k[1]+p[11]);
  } break;

  case 20: {
  memset(sxdot_tmp,0,sizeof(double)*3);
  sxdot_tmp[0] = -(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*sx_tmp[0]-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*sx_tmp[2];
  sxdot_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*sx_tmp[1]-((x_tmp[1]-1.0)*p[3]*p[10]*sx_tmp[0])/(k[0]+p[10]);
  sxdot_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*sx_tmp[2]-((x_tmp[2]-1.0)*p[5]*p[11]*sx_tmp[1])/(k[1]+p[11]);
  } break;

  case 21: {
  memset(sxdot_tmp,0,sizeof(double)*3);
  sxdot_tmp[0] = -(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*sx_tmp[0]-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*sx_tmp[2];
  sxdot_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*sx_tmp[1]-((x_tmp[1]-1.0)*p[3]*p[10]*sx_tmp[0])/(k[0]+p[10]);
  sxdot_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*sx_tmp[2]-((x_tmp[2]-1.0)*p[5]*p[11]*sx_tmp[1])/(k[1]+p[11]);
  } break;

  case 22: {
  memset(sxdot_tmp,0,sizeof(double)*3);
  sxdot_tmp[0] = -(p[0]-((exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*p[1]*p[6])/(p[6]+x_tmp[2]))*sx_tmp[0]-1.0/pow(p[6]+x_tmp[2],2.0)*(exp(-t/p[9])*(exp(-t/p[8])-1.0)-p[7])*(x_tmp[0]-1.0)*p[1]*p[6]*sx_tmp[2];
  sxdot_tmp[1] = -(p[2]+(p[3]*x_tmp[0])/(k[0]/p[10]+1.0))*sx_tmp[1]-((x_tmp[1]-1.0)*p[3]*p[10]*sx_tmp[0])/(k[0]+p[10]);
  sxdot_tmp[2] = -(p[4]+(p[5]*x_tmp[1])/(k[1]/p[11]+1.0))*sx_tmp[2]-((x_tmp[2]-1.0)*p[5]*p[11]*sx_tmp[1])/(k[1]+p[11]);
  } break;

  }
 for (ix=0; ix<3; ix++) {
    if(mxIsNaN(sxdot_tmp[ix])) sxdot_tmp[ix] = 0.0;
  }

  return(0);
}


 void sx0_RafMekErklin(int ip, N_Vector sx0, void *user_data)
{
  UserData data = (UserData) user_data;
  double *p = data->p;
  int *plist = data->plist;
  double *k = data->k;
  double *u = data->u;
  double *sx0_tmp = N_VGetArrayPointer(sx0);
  switch (ip) {
  case 0: {
  memset(sx0_tmp,0,sizeof(double)*3);

  } break;

  case 1: {
  memset(sx0_tmp,0,sizeof(double)*3);

  } break;

  case 2: {
  memset(sx0_tmp,0,sizeof(double)*3);

  } break;

  case 3: {
  memset(sx0_tmp,0,sizeof(double)*3);

  } break;

  case 4: {
  memset(sx0_tmp,0,sizeof(double)*3);

  } break;

  case 5: {
  memset(sx0_tmp,0,sizeof(double)*3);

  } break;

  case 6: {
  memset(sx0_tmp,0,sizeof(double)*3);

  } break;

  case 7: {
  memset(sx0_tmp,0,sizeof(double)*3);

  } break;

  case 8: {
  memset(sx0_tmp,0,sizeof(double)*3);

  } break;

  case 9: {
  memset(sx0_tmp,0,sizeof(double)*3);

  } break;

  case 10: {
  memset(sx0_tmp,0,sizeof(double)*3);

  } break;

  case 11: {
  memset(sx0_tmp,0,sizeof(double)*3);

  } break;

  case 12: {
  memset(sx0_tmp,0,sizeof(double)*3);

  } break;

  case 13: {
  memset(sx0_tmp,0,sizeof(double)*3);

  } break;

  case 14: {
  memset(sx0_tmp,0,sizeof(double)*3);

  } break;

  case 15: {
  memset(sx0_tmp,0,sizeof(double)*3);

  } break;

  case 16: {
  memset(sx0_tmp,0,sizeof(double)*3);

  } break;

  case 17: {
  memset(sx0_tmp,0,sizeof(double)*3);

  } break;

  case 18: {
  memset(sx0_tmp,0,sizeof(double)*3);

  } break;

  case 19: {
  memset(sx0_tmp,0,sizeof(double)*3);

  } break;

  case 20: {
  memset(sx0_tmp,0,sizeof(double)*3);
  sx0_tmp[0] = 1.0;
  } break;

  case 21: {
  memset(sx0_tmp,0,sizeof(double)*3);
  sx0_tmp[1] = 1.0;
  } break;

  case 22: {
  memset(sx0_tmp,0,sizeof(double)*3);
  sx0_tmp[2] = 1.0;
  } break;

  }

  return;
}


void y_RafMekErklin(double t, int nt, int it, double *y, double *p, double *k, double *u, double *x){
  y[it+nt*0] = p[12]*x[it+nt*1];
  y[it+nt*1] = p[13]*x[it+nt*2];
  y[it+nt*2] = p[14]*x[it+nt*1];
  y[it+nt*3] = p[15]*x[it+nt*2];
  y[it+nt*4] = p[16]*x[it+nt*1];
  y[it+nt*5] = p[17]*x[it+nt*2];
  y[it+nt*6] = p[18]*x[it+nt*1];
  y[it+nt*7] = p[19]*x[it+nt*2];    
    return;
}


void dydp_RafMekErklin(double t, int nt, int it, double *dydp, double *y, double *p, double *k, double *u, double *x, int *plist, int np, int ny){
  
  int ip;
  for(ip=0; ip<np; ip++) {
  switch (plist[ip]) {
  case 0: {

  } break;

  case 1: {

  } break;

  case 2: {

  } break;

  case 3: {

  } break;

  case 4: {

  } break;

  case 5: {

  } break;

  case 6: {

  } break;

  case 7: {

  } break;

  case 8: {

  } break;

  case 9: {

  } break;

  case 10: {

  } break;

  case 11: {

  } break;

  case 12: {
  dydp[it+nt*(0+ip*ny)] = x[it+nt*1];
  } break;

  case 13: {
  dydp[it+nt*(1+ip*ny)] = x[it+nt*2];
  } break;

  case 14: {
  dydp[it+nt*(2+ip*ny)] = x[it+nt*1];
  } break;

  case 15: {
  dydp[it+nt*(3+ip*ny)] = x[it+nt*2];
  } break;

  case 16: {
  dydp[it+nt*(4+ip*ny)] = x[it+nt*1];
  } break;

  case 17: {
  dydp[it+nt*(5+ip*ny)] = x[it+nt*2];
  } break;

  case 18: {
  dydp[it+nt*(6+ip*ny)] = x[it+nt*1];
  } break;

  case 19: {
  dydp[it+nt*(7+ip*ny)] = x[it+nt*2];
  } break;

  case 20: {

  } break;

  case 21: {

  } break;

  case 22: {

  } break;

  }
  }
  
  return;
}


void dydx_RafMekErklin(double t,double *dydx, double *y, double *p, double *k, double *x){
  memset(dydx,0,sizeof(double)*24);
  dydx[8] = p[12];
  dydx[10] = p[14];
  dydx[12] = p[16];
  dydx[14] = p[18];
  dydx[17] = p[13];
  dydx[19] = p[15];
  dydx[21] = p[17];
  dydx[23] = p[19];  
  return;
}


void fsy_RafMekErklin(double t, int nt, int it, int ip, int np, int nx, int ny, double *sy, double *p, double *k, double *x, double *sx){
  switch (ip) {
  case 0: {
  sy[it+nt*(0+np*ny)] = p[12]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(1+np*ny)] = p[13]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(2+np*ny)] = p[14]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(3+np*ny)] = p[15]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(4+np*ny)] = p[16]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(5+np*ny)] = p[17]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(6+np*ny)] = p[18]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(7+np*ny)] = p[19]*sx[it+nt*(2+np*nx)];
  } break;

  case 1: {
  sy[it+nt*(0+np*ny)] = p[12]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(1+np*ny)] = p[13]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(2+np*ny)] = p[14]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(3+np*ny)] = p[15]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(4+np*ny)] = p[16]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(5+np*ny)] = p[17]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(6+np*ny)] = p[18]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(7+np*ny)] = p[19]*sx[it+nt*(2+np*nx)];
  } break;

  case 2: {
  sy[it+nt*(0+np*ny)] = p[12]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(1+np*ny)] = p[13]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(2+np*ny)] = p[14]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(3+np*ny)] = p[15]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(4+np*ny)] = p[16]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(5+np*ny)] = p[17]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(6+np*ny)] = p[18]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(7+np*ny)] = p[19]*sx[it+nt*(2+np*nx)];
  } break;

  case 3: {
  sy[it+nt*(0+np*ny)] = p[12]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(1+np*ny)] = p[13]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(2+np*ny)] = p[14]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(3+np*ny)] = p[15]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(4+np*ny)] = p[16]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(5+np*ny)] = p[17]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(6+np*ny)] = p[18]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(7+np*ny)] = p[19]*sx[it+nt*(2+np*nx)];
  } break;

  case 4: {
  sy[it+nt*(0+np*ny)] = p[12]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(1+np*ny)] = p[13]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(2+np*ny)] = p[14]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(3+np*ny)] = p[15]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(4+np*ny)] = p[16]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(5+np*ny)] = p[17]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(6+np*ny)] = p[18]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(7+np*ny)] = p[19]*sx[it+nt*(2+np*nx)];
  } break;

  case 5: {
  sy[it+nt*(0+np*ny)] = p[12]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(1+np*ny)] = p[13]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(2+np*ny)] = p[14]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(3+np*ny)] = p[15]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(4+np*ny)] = p[16]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(5+np*ny)] = p[17]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(6+np*ny)] = p[18]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(7+np*ny)] = p[19]*sx[it+nt*(2+np*nx)];
  } break;

  case 6: {
  sy[it+nt*(0+np*ny)] = p[12]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(1+np*ny)] = p[13]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(2+np*ny)] = p[14]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(3+np*ny)] = p[15]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(4+np*ny)] = p[16]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(5+np*ny)] = p[17]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(6+np*ny)] = p[18]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(7+np*ny)] = p[19]*sx[it+nt*(2+np*nx)];
  } break;

  case 7: {
  sy[it+nt*(0+np*ny)] = p[12]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(1+np*ny)] = p[13]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(2+np*ny)] = p[14]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(3+np*ny)] = p[15]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(4+np*ny)] = p[16]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(5+np*ny)] = p[17]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(6+np*ny)] = p[18]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(7+np*ny)] = p[19]*sx[it+nt*(2+np*nx)];
  } break;

  case 8: {
  sy[it+nt*(0+np*ny)] = p[12]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(1+np*ny)] = p[13]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(2+np*ny)] = p[14]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(3+np*ny)] = p[15]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(4+np*ny)] = p[16]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(5+np*ny)] = p[17]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(6+np*ny)] = p[18]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(7+np*ny)] = p[19]*sx[it+nt*(2+np*nx)];
  } break;

  case 9: {
  sy[it+nt*(0+np*ny)] = p[12]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(1+np*ny)] = p[13]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(2+np*ny)] = p[14]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(3+np*ny)] = p[15]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(4+np*ny)] = p[16]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(5+np*ny)] = p[17]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(6+np*ny)] = p[18]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(7+np*ny)] = p[19]*sx[it+nt*(2+np*nx)];
  } break;

  case 10: {
  sy[it+nt*(0+np*ny)] = p[12]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(1+np*ny)] = p[13]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(2+np*ny)] = p[14]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(3+np*ny)] = p[15]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(4+np*ny)] = p[16]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(5+np*ny)] = p[17]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(6+np*ny)] = p[18]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(7+np*ny)] = p[19]*sx[it+nt*(2+np*nx)];
  } break;

  case 11: {
  sy[it+nt*(0+np*ny)] = p[12]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(1+np*ny)] = p[13]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(2+np*ny)] = p[14]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(3+np*ny)] = p[15]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(4+np*ny)] = p[16]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(5+np*ny)] = p[17]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(6+np*ny)] = p[18]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(7+np*ny)] = p[19]*sx[it+nt*(2+np*nx)];
  } break;

  case 12: {
  sy[it+nt*(0+np*ny)] = p[12]*sx[it+nt*(1+np*nx)]+x[it+nt*1];
  sy[it+nt*(1+np*ny)] = p[13]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(2+np*ny)] = p[14]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(3+np*ny)] = p[15]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(4+np*ny)] = p[16]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(5+np*ny)] = p[17]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(6+np*ny)] = p[18]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(7+np*ny)] = p[19]*sx[it+nt*(2+np*nx)];
  } break;

  case 13: {
  sy[it+nt*(0+np*ny)] = p[12]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(1+np*ny)] = p[13]*sx[it+nt*(2+np*nx)]+x[it+nt*2];
  sy[it+nt*(2+np*ny)] = p[14]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(3+np*ny)] = p[15]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(4+np*ny)] = p[16]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(5+np*ny)] = p[17]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(6+np*ny)] = p[18]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(7+np*ny)] = p[19]*sx[it+nt*(2+np*nx)];
  } break;

  case 14: {
  sy[it+nt*(0+np*ny)] = p[12]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(1+np*ny)] = p[13]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(2+np*ny)] = p[14]*sx[it+nt*(1+np*nx)]+x[it+nt*1];
  sy[it+nt*(3+np*ny)] = p[15]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(4+np*ny)] = p[16]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(5+np*ny)] = p[17]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(6+np*ny)] = p[18]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(7+np*ny)] = p[19]*sx[it+nt*(2+np*nx)];
  } break;

  case 15: {
  sy[it+nt*(0+np*ny)] = p[12]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(1+np*ny)] = p[13]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(2+np*ny)] = p[14]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(3+np*ny)] = p[15]*sx[it+nt*(2+np*nx)]+x[it+nt*2];
  sy[it+nt*(4+np*ny)] = p[16]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(5+np*ny)] = p[17]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(6+np*ny)] = p[18]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(7+np*ny)] = p[19]*sx[it+nt*(2+np*nx)];
  } break;

  case 16: {
  sy[it+nt*(0+np*ny)] = p[12]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(1+np*ny)] = p[13]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(2+np*ny)] = p[14]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(3+np*ny)] = p[15]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(4+np*ny)] = p[16]*sx[it+nt*(1+np*nx)]+x[it+nt*1];
  sy[it+nt*(5+np*ny)] = p[17]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(6+np*ny)] = p[18]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(7+np*ny)] = p[19]*sx[it+nt*(2+np*nx)];
  } break;

  case 17: {
  sy[it+nt*(0+np*ny)] = p[12]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(1+np*ny)] = p[13]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(2+np*ny)] = p[14]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(3+np*ny)] = p[15]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(4+np*ny)] = p[16]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(5+np*ny)] = p[17]*sx[it+nt*(2+np*nx)]+x[it+nt*2];
  sy[it+nt*(6+np*ny)] = p[18]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(7+np*ny)] = p[19]*sx[it+nt*(2+np*nx)];
  } break;

  case 18: {
  sy[it+nt*(0+np*ny)] = p[12]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(1+np*ny)] = p[13]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(2+np*ny)] = p[14]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(3+np*ny)] = p[15]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(4+np*ny)] = p[16]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(5+np*ny)] = p[17]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(6+np*ny)] = p[18]*sx[it+nt*(1+np*nx)]+x[it+nt*1];
  sy[it+nt*(7+np*ny)] = p[19]*sx[it+nt*(2+np*nx)];
  } break;

  case 19: {
  sy[it+nt*(0+np*ny)] = p[12]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(1+np*ny)] = p[13]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(2+np*ny)] = p[14]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(3+np*ny)] = p[15]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(4+np*ny)] = p[16]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(5+np*ny)] = p[17]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(6+np*ny)] = p[18]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(7+np*ny)] = p[19]*sx[it+nt*(2+np*nx)]+x[it+nt*2];
  } break;

  case 20: {
  sy[it+nt*(0+np*ny)] = p[12]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(1+np*ny)] = p[13]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(2+np*ny)] = p[14]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(3+np*ny)] = p[15]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(4+np*ny)] = p[16]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(5+np*ny)] = p[17]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(6+np*ny)] = p[18]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(7+np*ny)] = p[19]*sx[it+nt*(2+np*nx)];
  } break;

  case 21: {
  sy[it+nt*(0+np*ny)] = p[12]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(1+np*ny)] = p[13]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(2+np*ny)] = p[14]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(3+np*ny)] = p[15]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(4+np*ny)] = p[16]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(5+np*ny)] = p[17]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(6+np*ny)] = p[18]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(7+np*ny)] = p[19]*sx[it+nt*(2+np*nx)];
  } break;

  case 22: {
  sy[it+nt*(0+np*ny)] = p[12]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(1+np*ny)] = p[13]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(2+np*ny)] = p[14]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(3+np*ny)] = p[15]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(4+np*ny)] = p[16]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(5+np*ny)] = p[17]*sx[it+nt*(2+np*nx)];
  sy[it+nt*(6+np*ny)] = p[18]*sx[it+nt*(1+np*nx)];
  sy[it+nt*(7+np*ny)] = p[19]*sx[it+nt*(2+np*nx)];
  } break;

  }
  
  return;
}
