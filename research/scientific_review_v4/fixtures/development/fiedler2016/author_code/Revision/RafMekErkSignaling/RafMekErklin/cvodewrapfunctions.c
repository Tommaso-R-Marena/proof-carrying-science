#include "RafMekErklin.c"
                
                int cvodewrap_init(void *cvode_mem, N_Vector x, double t){
                    return CVodeInit(cvode_mem, xdot_RafMekErklin, RCONST(t), x);
                }
                int cvodewrap_binit(void *cvode_mem, int which, N_Vector xB, double t){
                    return CVodeInitB(cvode_mem, which, xBdot_RafMekErklin, RCONST(t), xB);
                }
                int cvodewrap_qbinit(void *cvode_mem, int which, N_Vector xQB){
                    return CVodeQuadInitB(cvode_mem, which, xQB_RafMekErklin, xQB);
                }
                
                void fx0(N_Vector x0, void *user_data){
                    UserData data = (UserData) user_data;
                    x0_RafMekErklin(x0, data);
                }
                
                int cvodewrap_SetDenseJacFn(void *cvode_mem){
                    return CVDlsSetDenseJacFn(cvode_mem, J_RafMekErklin);
                }
                int cvodewrap_SetBandJacFn(void *cvode_mem){
                    /*return CVDlsSetBandJacFn(cvode_mem, J_RafMekErklin)*/;
                    return -1;
                }
                int cvodewrap_SetJacTimesVecFn(void *cvode_mem){
                    return CVSpilsSetJacTimesVecFn(cvode_mem, Jv_RafMekErklin);
                }
                int cvodewrap_SetDenseJacFnB(void *cvode_mem,int which){
                    return CVDlsSetDenseJacFnB(cvode_mem, which, JB_RafMekErklin);
                }
                int cvodewrap_SetBandJacFnB(void *cvode_mem,int which){
                    /*return CVDlsSetBandJacFn(cvode_mem, which, JB_RafMekErklin)*/;
                    return -1;
                }
                int cvodewrap_SetJacTimesVecFnB(void *cvode_mem,int which){
                    return CVSpilsSetJacTimesVecFnB(cvode_mem, which, JvB_RafMekErklin);
                }
                
                void fsx0(N_Vector *sx0, void *user_data){
                    UserData data = (UserData) user_data;
                    int ip;
;                    int *plist = data->plist;
                    int np = *data->np;
                    for (ip=0; ip<np; ip++) {
                       sx0_RafMekErklin(plist[ip], sx0[ip], data);
                    }
                }
                
                int cvodewrap_SensInit1(void *cvode_mem, int np, int sensi_meth, N_Vector *sx){
                    return CVodeSensInit1(cvode_mem, np, sensi_meth, sx_RafMekErklin, sx);
                }
                
                
                
                
                
                void fy(double t, int nt, int it, double *y, double *p, double *k, double *u, double *x){
                    y_RafMekErklin(t, nt, it, y, p, k, u, x);
                }
                
                void fxdot(realtype t, N_Vector x, N_Vector xdot, void *user_data){
                    xdot_RafMekErklin(t,x,xdot,user_data);
                }
                void fdydp(double t, int nt, int it,double *dydp, double *y, double *p, double *k, double *u, double *x, int *plist, int np, int ny){
                    dydp_RafMekErklin(t, nt, it, dydp, y, p, k, u, x, plist, np, ny);
                }
                void fdydx(double t,double *dydx, double *y, double *p, double *k, double *x){
                    dydx_RafMekErklin(t, dydx, y, p, k, x);
                }
                
                
                void fsy(double t, int nt, int it, int *plist, int nx, int ny, int np, double *sy, double *p, double *k, double *x, double *sx){
                    int ip;
;                    for (ip=0; ip<np; ip++) {
                        fsy_RafMekErklin(t, nt, it, plist[ip], ip,  nx, ny,  sy, p, k, x, sx);
                    }
                }
                void cvodewrap_ErrHandlerFn(int error_code, const char *module, const char *function, char *msg, void *eh_data){
                    char buffer [250];                    sprintf(buffer,"CVODES ERROR: in module %s in function %s : %s ",module,function,msg);                    mexWarnMsgTxt(buffer);                }
