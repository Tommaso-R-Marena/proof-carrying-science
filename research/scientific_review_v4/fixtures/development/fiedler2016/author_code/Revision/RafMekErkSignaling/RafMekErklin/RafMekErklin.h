#ifndef _MY_RafMekErklin
#define _MY_RafMekErklin

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

             void x0_RafMekErklin(N_Vector x0, void *user_data);
             int J_RafMekErklin(long int N, realtype t, N_Vector x,N_Vector fx, DlsMat J, void *user_data,N_Vector tmp1, N_Vector tmp2, N_Vector tmp3);
             int Jv_RafMekErklin(N_Vector v, N_Vector Jv, realtype t, N_Vector x, N_Vector xdot, void *user_data, N_Vector tmp);
             int sx_RafMekErklin(int Ns, realtype t, N_Vector x, N_Vector xdot,int ip, N_Vector sx, N_Vector sxdot, void *user_data, N_Vector tmp1, N_Vector tmp2);
             void sx0_RafMekErklin(int ip, N_Vector sx0, void *user_data);
             void y_RafMekErklin(double t, int nt, int it, double *y, double *p, double *k, double *u, double *x);
             void dydp_RafMekErklin(double t, int nt, int it, double *dydp, double *y, double *p, double *k, double *u, double *x, int *plist, int np, int ny);
             void dydx_RafMekErklin(double t, double *dydx, double *y, double *p, double *k, double *x);
             void sy_RafMekErklin(double t, int nt, int it, int ip, int sp, int nx, int ny, double *sy, double *p, double *k, double *u, double *x, double *sx);


#endif /* _MY_RafMekErklin */
