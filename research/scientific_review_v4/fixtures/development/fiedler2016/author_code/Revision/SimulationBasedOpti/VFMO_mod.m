% VFMO_mod.m provides the gradient for the simulation-based optimization
%
% USAGE:
% ======
% [...] = VFMO_mod(r,z,system_fun,options)
% [grad] = VFMO_mod(...)
% [grad,J] = VFMO_mod(...)
%
% INPUTS:
% =======
% r ... simulation time
% z ... parameter-state vector
% system_fun ... function using the biological ODE and the objective
%                function to provide the objective function value (J),
%                gradient wtr to the parameters theta (dJdtheta),
%                right-hand-side of biological ODE (f), sensetivity dx_s/dtheta (S)
%                and Fisher Information Matrix (F)
% options ... option struct
%   .method ... gradient descent or newton type descent direction
%   .retraction_factor ... different implementations of the retraction
%                          factor (proof only for 'const')
% OUTPUTS:
% ========
% grad ... gradient of the simulation-based optimization method ([dtheta,dx_s])
% J ... objective function value at z
%
% 2015/12/07 Anna Fiedler

function [varargout] = VFMO_mod (r,z,system_fun,options)
%% Options

global maxSteps;

lambda = options.lambda;

if ~isfield(options,'method')
    options.method = 'newton-method';
end

if ~isfield(options,'retraction_factor')
    options.retraction_factor = 'const';
end

%% Evaluation of J, dJ/dtheta, f, grad_f, S, F using system_fun
[J,dJdtheta,f_Jxf,S,F] = system_fun(r,z);

f = f_Jxf(:,1);

%% Vector field
% Parameter derivative
switch options.method
    case 'gradient-descent'
        dtheta = -dJdtheta;
    case 'newton-method'
        try
            dtheta = -pinv(F)*dJdtheta;
        catch
            dtheta = -F\dJdtheta;
        end
    case 'none'
        dtheta = zeros(n_theta,1);
end

% State derivative

% retraction factor implementations (for now only for 'const' convergence is proven)
switch options.retraction_factor
    case 'balance'
        lambda_min = 10;
        l = - S*dtheta./f;
        lambda = max(2*max(l),lambda_min);
    case 'min_ev'
        w = min(abs(eig(nabla_x_f)));
        lambda = lambda*(1/w);
    case 'norm_f'
        lambda = lambda*norm(f,1);
    case 'const'
end

dx = S*dtheta + lambda*f;

% The term 'lambda*f' functions as a correction term which compensations
% initial errors in the steady state as well as errors accumulated during
% the numerical integration.

%% Output assignment
grad = [dtheta;dx];

%% Checking stop criteria
global ng
global ngx

ngx = norm(f./(z(end-length(dx)+1:end)+1e-6));
ng = norm(dtheta);

maxSteps = maxSteps-1;

%% Output
if nargout == 1
    varargout{1} = grad;
else
    varargout{1} = grad;
    varargout{2} = J;
end
end