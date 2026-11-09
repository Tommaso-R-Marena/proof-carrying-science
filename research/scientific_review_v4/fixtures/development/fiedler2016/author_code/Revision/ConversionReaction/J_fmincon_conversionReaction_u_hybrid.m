% x_0_old = x_0(theta_old)
% J_old = J(theta_old,x_0_old)
% save('current_state','theta_old','x_0_old','J_old')

function [J,dJdtheta] = J_fmincon_conversionReaction_u_semia(z,J_fun,f_rhs,f_fun,D,options)
n_theta = options.n_theta;
%n_x = options.n_x;
eps_x0 = options.xTol; %1e-7;
eps = options.convTol; %1e-9;

u = D.conditions;
n_u = size(u,1);
n_r = size(D.measurement{1},2);

u_s = D.u_s;

theta = z(1:n_theta);% parameters

%sigma2 = z(n_theta+1:n_theta+n_sigma); % noise
%% Load steady state for previous best known solution (in this run)
load('current_state');
x_0_evol = [x_0_evol, x_0_old];
theta_evol = [theta_evol, theta];

% J_old

%% Simulate till steady state is reach
converged = false;
x_0 = x_0_old;
T = 1;
while ~converged
    [~,X] = ode15s(@(t,x)f_rhs(t,[theta;x],u_s),[0,T],x_0);
    x_0 = X(end,:)';
    if max(abs(f_rhs(0,[theta;x_0],u_s)./(x_0+eps_x0)) > eps)
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

[f,grad_f]=f_rhs(0,[theta;x_0],u_s);
%f(i,:) = grad_f(:,1)';
nabla_theta_f = grad_f(1:n_theta);
nabla_x_f = grad_f(n_theta+1:end);
% Sensitivity matrix (S)
dx_0dtheta = -nabla_x_f\nabla_theta_f;


%% Evaluation of objective function
%dJ/dtheta = fun(theta,x0,dx_0dtheta)

J = 0;
dJdtheta = zeros(n_theta,1);

for i = 1:n_u
    t_m = D.t{i};
    ic = [0,0,1]';
    
    % evtl. an f_fun anpassen
    [~,x_sens] = ode15s(@(t,x) f_fun(t,[theta;x],u(i,:)),t_m,[x_0;ic]);
    
     xs = x_sens(:,1)';
     S_theta = x_sens(:,2:3);
     S_x0 = x_sens(:,4:end);
     
     %% Computation of derivatives
     % Parameter derivative
     dyxi_ik = S_theta + S_x0*dx_0dtheta;
    % Objective function value
    [J_i,grad_J] = J_fun(D.measurement{i}(:),xs(:),dyxi_ik);
    J = J + J_i;

    dJdtheta = dJdtheta + grad_J;
end
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

