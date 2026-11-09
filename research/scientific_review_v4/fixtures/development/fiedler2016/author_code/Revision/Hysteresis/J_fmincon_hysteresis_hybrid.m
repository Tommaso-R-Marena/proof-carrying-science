% x_0_old = x_0(theta_old)
% J_old = J(theta_old,x_0_old)
% save('current_state','theta_old','x_0_old','J_old')

function [J,dJdtheta] = J_fmincon_hysteresis_hybrid(z,f_rhs,D,options)
eps_x0 = options.xTol; %1e-7;
eps = options.convTol; %1e-9;

theta = z(1);% parameters

%% Load steady state for previous best known solution (in this run)
load('current_state');
x_0_evol = [x_0_evol, x_0_old];
theta_evol = [theta_evol, theta];

%% Simulate till steady state is reach
converged = false;
x_0 = x_0_old;
T = 1;
while ~converged
    [~,X] = ode15s(@(t,x)f_rhs(t,[theta;x]),[0,T],x_0);
    x_0 = X(end,:)';
    if max(abs(f_rhs(0,[theta;x_0])./(x_0+eps_x0)) > eps)
        T = 10*T;
    else
        converged = true;
    end
    if T > 1e+15
        J = Inf;
        dJdtheta = zeros;
        break
    end
end

x_0_evol = [x_0_evol, x_0];
theta_evol = [theta_evol, theta];
if ~converged
    
else
    %% Evaluation of parameter dependence of x_0
%dx_0dtheta = - Jacobian(theta,x_0)^(-1)*df/dtheta(theta,x_0); % sensitivity

[f,grad_f]=f_rhs(0,[theta;x_0]);
nabla_theta_f = grad_f(1);
nabla_x_f = grad_f(2);
% Sensitivity matrix (S)
S = -nabla_x_f\nabla_theta_f;


%% Evaluation of objective function
%dJ/dtheta = fun(theta,x0,dx_0dtheta)

J = 0.5*(D-x_0)^2;
dJdtheta = -(D-x_0)*S;
%% Save best known solution (in this run)
%if J < J_old
    % theta_old = theta;
    x_0_old = x_0;
    J_old = J;
    save('current_state','theta_old','x_0_old','J_old','x_0_evol','theta_evol')
% else
%     save('current_state','theta_old','x_0_old','J_old','x_0_evol','theta_evol')
% end
end

