% Manifold_opt.m is a multistart routine for simulation-based optimization
%
% USAGE:
% ======
% [...] = Manifold_opt(parameters,vf_function,options)
% [parameters] = Manifold(...)
%
% INPUTS:
% =======
% parameters ... parameter struct
%   .number ... number of parameter
%   .guess ... initial guess of parameter
%   .min ... lower bound for parameter values       
%   .max ... upper bound for parameter values        
% vf_function ... function providing the right-hand-side of the
%                 simulation-based optimization ODE
% options ... option struct
%   .n_starts ... number of multistarts
%   .op ... ODE solver (ode15s) options
%   .R_max ... maximal simulation time
%   .maxSteps ... maximal number vf_function evalutations
%   .steadyState ... analytical steady state (if provided startpoints for 
%                    multistart will be automatically drawn to be on the manifold)
% OUTPUTS:
% ========
% parameters ... parameter struct
%   .number ... number of parameter
%   .guess ... initial guess of parameter
%   .min ... lower bound for parameter values       
%   .max ... upper bound for parameter values     
%   .MS ... multistart results
%       .par0 ... multistart start points
%       .par_evol ... solver path (theta,x_s)
%       .par ... endpoint of simulation (theta^*,x_s^*)
%       .gradient ... gradient at endpoint
%       .n_iter ... number of iterations
%       .t_cpu ... CPU time
%       .stopCrit ... stop criterium at endpoint
%       .errorCount ... number of unsuccessful soltuions of biological ODE 
%       .logPost ... log-likelihood value after optimization (
%                     =-1*objective funciton value)
%       .logPost0 ... log-likelihood value for par0
%       .hessian ... hessian at end of optimization (not yet implemented)
%       .n_objfun ... number of objective function evaluations (not yet implemented)
%
% 2015/12/07 Anna Fiedler

function [parameters] = Manifold_opt(varargin)
if nargin >= 2
    parameters = varargin{1};
    vf_function = varargin{2};
else
    error('Manifold_opt.m requires at least two inputs.')
end
% random seed
rng(70);

% set default options
options.n_starts = 1;
options.op = odeset('Events',@event);%'abstol',1e-6,'reltol',1e-6
options.R_max = 10^12;
options.maxSteps = 3000;
if nargin == 3
    options = setdefault(varargin{3},options);
end

% latin hypercube sampling
if options.n_starts == 1
    z0 = parameters.guess;
else
    z0 = [parameters.guess,bsxfun(@plus,parameters.min,bsxfun(@times,...
          parameters.max - parameters.min,lhsdesign(options.n_starts - ...
          size(parameters.guess,2),parameters.number,'smooth','off')'))];
end

% start on manifold if analytical steady state is available
if isfield(options,'steadyState')
    for i = 1:options.n_starts
        x_0 = options.steadyState(z0(:,i));
        z0(end-length(x_0)+1:end,i) = x_0;
    end
end

% initialization of parameters struct
parameters.MS.par0 = z0;
parameters.MS.par_evol = cell(options.n_starts,1);
parameters.MS.par = nan(parameters.number,options.n_starts);
parameters.MS.gradient = nan(parameters.number,options.n_starts);
parameters.MS.n_iter = nan(options.n_starts,1);
parameters.MS.t_cpu = nan(options.n_starts,1);
parameters.MS.stopCrit = nan(options.n_starts,2);
parameters.MS.errorCount = nan(options.n_starts,1);
parameters.MS.logPost = nan(options.n_starts,1);
parameters.MS.logPost0 = nan(options.n_starts,1);
parameters.MS.hessian = nan(parameters.number,parameters.number,options.n_starts); %To Do
parameters.MS.n_objfun = nan(options.n_starts); % To Do

R_max = options.R_max;
for i=1:options.n_starts
    % initialization of global variables (stopping cirteria)
    global maxSteps;
    global ng 
    global ngx
    global errorCount;
    errorCount = 100;
    maxSteps = options.maxSteps;
    
    try
        T_cpu = cputime;
        [~,Z_ODE_SD] = ode15s(vf_function,[0 R_max],z0(:,i),options.op);
        parameters.MS.t_cpu(i) = cputime - T_cpu;
        
        parameters.MS.par_evol{i} = Z_ODE_SD;
        parameters.MS.par(:,i) = Z_ODE_SD(end,:)';
        parameters.MS.n_iter(i) = options.maxSteps-maxSteps;
        parameters.MS.stopCrit(i,:) = [ng, ngx];
        parameters.MS.errorCount(i) = 100 - errorCount;
        [parameters.MS.gradient(:,i),parameters.MS.logPost(i)] = vf_function(0,Z_ODE_SD(end,:)');
        parameters.MS.logPost(i) = -parameters.MS.logPost(i);
        [~,parameters.MS.logPost0(i)] = vf_function(0,parameters.MS.par0(:,i));
        parameters.MS.logPost0(i) = -parameters.MS.logPost0(i);
        
        disp(['start ' num2str(i) '/' num2str(options.n_starts) ])
    catch
        disp(['start ' num2str(i) '/' num2str(options.n_starts) ' optimization failed'])
    end
end
