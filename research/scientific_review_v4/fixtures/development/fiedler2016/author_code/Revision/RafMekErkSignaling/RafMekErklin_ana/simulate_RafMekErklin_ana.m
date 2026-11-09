% simulate_RafMekErklin_ana.m is the matlab interface to the cvodes mex
%   which simulates the ordinary differential equation and respective
%   sensitivities according to user specifications.
%
% USAGE:
% ======
% [...] = simulate_RafMekErklin_ana(tout,theta)
% [...] = simulate_RafMekErklin_ana(tout,theta,kappa,sens_ind,options)
% [status,tout,x,y,sx,sy,sol] = simulate_RafMekErklin_ana(...)
%
% INPUTS:
% =======
% tout ... 1 dimensional vector of timepoints at which a solution to the ODE is desired
% theta ... 1 dimensional parameter vector of parameters for which sensitivities are desired.
%           this corresponds to the specification in model.sym.p
% kappa ... 1 dimensional parameter vector of parameters for which sensitivities are not desired.
%           this corresponds to the specification in model.sym.k
% sens_ind ... 1 dimensional vector of indexes for which sensitivities must be computed.
%           default value is 1:length(theta).
% options ... additional options to pass to the cvodes solver. Refer to the cvodes guide for more documentation.
%    .cvodes_atol ... absolute tolerance for the solver. default is specified in the user-provided syms function.
%    .cvodes_rtol ... relative tolerance for the solver. default is specified in the user-provided syms function.
%    .maxsteps    ... maximal number of integration steps. default is specified in the user-provided syms function.
%    .tstart    ... start of integration. for all timepoints before this, values will be set to initial value.
%    .lmm    ... linear multistep method for forward problem.
%        1: Adams-Bashford
%        2: BDF (DEFAULT)
%    .iter    ... iteration method for linear multistep.
%        1: Functional
%        2: Newton (DEFAULT)
%    .linsol   ... linear solver module.
%        direct solvers:
%        1: Dense (DEFAULT)
%        2: Band (not implented)
%        3: LAPACK Dense (not implented)
%        4: LAPACK Band  (not implented)
%        5: Diag (not implented)
%        implicit krylov solvers:
%        6: SPGMR
%        7: SPBCG
%        8: SPTFQMR
%    .stldet   ... flag for stability limit detection. this should be turned on for stiff problems.
%        0: OFF
%        1: ON (DEFAULT)
%    .qPositiveX   ... vector of 0 or 1 of same dimension as state vector. 1 enforces positivity of states.
%    .sensi_meth   ... method for sensitivity computation.
%        1: Forward Sensitivity Analysis (DEFAULT)
%        2: Adjoint Sensitivity Analysis
%    .ism   ... only available for sensi_meth == 1. Method for computation of forward sensitivities.
%        1: Simultaneous (DEFAULT)
%        2: Staggered
%        3: Staggered1
%    .Nd   ... only available for sensi_meth == 2. Number of Interpolation nodes for forward solution. 
%              Default is 1000. 
%    .interpType   ... only available for sensi_meth == 2. Interpolation method for forward solution.
%        1: Hermite (DEFAULT)
%        2: Polynomial
%    .lmmB   ... only available for sensi_meth == 2. linear multistep method for backward problem.
%        1: Adams-Bashford
%        2: BDF (DEFAULT)
%    .iterB   ... only available for sensi_meth == 2. iteration method for linear multistep.
%        1: Functional
%        2: Newton (DEFAULT)
%
% Outputs:
% ========
% status ... flag for status of integration. generally status<0 for failed integration
% tout ... vector at which the solution was computed
% x ... time-resolved state vector
% y ... time-resolved output vector
% sx ... time-resolved state sensitivity vector
% sy ... time-resolved output sensitivity vector
% sol ... solution struct containing additional information
%     .xdot time-resolved right-hand side of differential equation
function varargout = simulate_RafMekErklin_ana(varargin)

% DO NOT CHANGE ANYTHING IN THIS FILE UNLESS YOU ARE VERY SURE ABOUT WHAT YOU ARE DOING
% MANUAL CHANGES TO THIS FILE CAN RESULT IN WRONG SOLUTIONS AND CRASHING OF MATLAB
if(nargin<2)
    error('Not enough input arguments.');
else
    tout=varargin{1};
    phi=varargin{2};
end
if(nargin>=3)
    kappa=varargin{3};
else
    kappa=[];
end
if(nargin>=4)
    sens_ind=varargin{4};
else
    sens_ind = 1:length(phi);
end
theta = phi;

try
    if(varargin{5}.speedup)
        persistent old_theta old_tout old_kappa old_nargout
        persistent old_status old_t old_x old_y old_sx old_sy old_sol
    end
catch
end

options_cvode.cvodes_atol = 1e-08;
options_cvode.cvodes_rtol = 1e-08;
options_cvode.cvodes_maxsteps = 10000;
options_cvode.nx = 3; % MUST NOT CHANGE THIS VALUE
options_cvode.ny = 8; % MUST NOT CHANGE THIS VALUE
options_cvode.np = length(sens_ind); % MUST NOT CHANGE THIS VALUE
options_cvode.tstart = 0;
CW_DENSE       =1;
CW_BAND        =2;
CW_LAPACKDENSE =3;
CW_LAPACKBAND  =4;
CW_DIAG        =5;
CW_SPGMR       =6;
CW_SPBCG       =7;
CW_SPTFQMR     =8;
CW_FSA =1;
CW_ASA =2;
CV_ADAMS =1;
CV_BDF =2;
CV_HERMITE =1;
CV_POLYNOMIAL =2;
CV_SIMULTANEOUS =1;
CV_STAGGERED =2;
CV_STAGGERED1 =3;
CV_FUNCTIONAL=1;
CV_NEWTON =2;

CW_TRUE=1;
CW_FALSE=0;

options_cvode.lmm = CV_BDF;
options_cvode.iter = CV_NEWTON;
options_cvode.linsol = CW_DENSE;
options_cvode.stldet = CW_TRUE;
options_cvode.Nd = 1000;
options_cvode.interpType = CV_HERMITE;
options_cvode.lmmB = CV_BDF;
options_cvode.iterB = CV_NEWTON;
options_cvode.ism = CV_SIMULTANEOUS;
options_cvode.sensi_meth = CW_FSA;

options_cvode.qPositiveX = zeros(length(tout),3);
if(max(sens_ind)>length(theta))
    error('Sensitivity index exceeds parameter dimension!')
end

try
    if(all([all(tout==old_tout),all(theta==old_theta),all(kappa==old_kappa),nargout<=old_nargout,varargin{5}.speedup]))
        varargout{1} = old_status;
        varargout{2} = old_t;
        varargout{3} = old_x;
        varargout{4} = old_y;
        if(nargout>4)
            varargout{5} = old_sx;
            varargout{6} = old_sy;
            varargout{7} = old_sol;
        end
        return;
    end
catch
end

sol.status = 0;
sol.t = tout;
sol.x = zeros(length(tout),3);
sol.y = zeros(length(tout),8);
sol.xdot = zeros(length(tout),3);
sol.numsteps = zeros(length(tout),1);
sol.numrhsevals = zeros(length(tout),1);
sol.numlinsolvsetups = zeros(length(tout),1);
sol.numerrtestfails = zeros(length(tout),1);
sol.order = zeros(length(tout),1);
sol.numnonlinsolviters = zeros(length(tout),1);
sol.numjacevals = zeros(length(tout),1);
sol.numliniters = zeros(length(tout),1);
sol.numconvfails = zeros(length(tout),1);
sol.numprecevals = zeros(length(tout),1);
sol.numprecsolves = zeros(length(tout),1);

sol.numjtimesevals = zeros(length(tout),1);
sol.numstepsS = zeros(length(tout),1);
sol.numrhsevalsS = zeros(length(tout),1);
sol.numlinsolvsetupsS = zeros(length(tout),1);
sol.numerrtestfailsS = zeros(length(tout),1);
sol.orderS = zeros(length(tout),1);
sol.numnonlinsolvitersS = zeros(length(tout),1);
sol.numjacevalsS = zeros(length(tout),1);
sol.numlinitersS = zeros(length(tout),1);
sol.numconvfailsS = zeros(length(tout),1);
sol.numprecevalsS = zeros(length(tout),1);
sol.numprecsolvesS = zeros(length(tout),1);
sol.numjtimesevalsS = zeros(length(tout),1);
if(nargout>4)
    sol.xS = zeros(length(tout),3,length(sens_ind));
    sol.yS = zeros(length(tout),8,length(sens_ind));
    options_cvode.sensi = 1;
else
    options_cvode.sensi = 0;
end

plist = sens_ind-1;
pbar = abs(theta);
pbar(pbar==0) = 1;
xscale = [];
if(nargin>=5)
    options_cvode = setdefault(varargin{5},options_cvode);
else
end
   RafMekErklin_ana(sol,tout,theta(1:20),kappa(1:2),options_cvode,plist,pbar,xscale);
    varargout{1} = sol.status;
    varargout{2} = sol.t;
    varargout{3} = sol.x;
    varargout{4} = sol.y;
if(nargout>4)
    Sx = sol.xS;
    Sy = sol.yS;
    varargout{5} = Sx;
    varargout{6} = Sy;
    varargout{7} = sol;
end
old_status = sol.status;
old_t = sol.t;
old_x = sol.x;
old_y = sol.y;
if(nargout>4)
    old_sx = Sx;
    old_sy = Sy;
    old_sol = sol;
end
old_theta = theta;
old_kappa = kappa;
old_tout = tout;
old_nargout = nargout;
end
