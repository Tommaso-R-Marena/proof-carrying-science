% x_0_old = x_0(theta_old)
% J_old = J(theta_old,x_0_old)
% save('current_state','theta_old','x_0_old','J_old')

function [J,dJdtheta] = J_fmincon_DoseResp_normal_hybrid(z,J_fun,J_pen,f_rhs,f_fun,D,options)
n_theta = options.n_theta;
n_x = options.n_x;
eps_x0 = options.xTol; %1e-7;
eps = options.convTol; %1e-9;

u = D.u;
n_u = length(u);
n_r = size(D.Ey,2);

n_sigma = length(z)-n_theta;

theta = z(1:n_theta);% parameters
sigma2 = z(n_theta+1:n_theta+n_sigma); % noise
%% Load steady state for previous best known solution (in this run)
load('current_state');

%% Simulate till steady state is reach
converged = false;
x_0 = x_0_old;
T = 1;
while ~converged
    [~,X] = ode15s(@(t,x)f_fun(0,x,theta,u),[0,T],x_0);
    x_0 = X(end,:)';
    if max(abs(f_fun(0,x_0,theta,u)./(x_0+eps_x0)) > eps)
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


if ~converged
    
else
    %% Evaluation of parameter dependence of x_0
%dx_0dtheta = - Jacobian(theta,x_0)^(-1)*df/dtheta(theta,x_0); % sensitivity
    dx_0dtheta = zeros(n_u,n_x,n_theta);
for i = 1:n_u
   [grad_f(:,:)]=f_rhs(1,x_0(1+(i-1)*n_x:i*n_x),theta,u(i));
   %f(i,:) = grad_f(:,1)';
   nabla_theta_f = grad_f(:,2:n_theta+1);
   nabla_x_f = grad_f(:,n_theta+2:end);
   % Sensitivity matrix (S)
   dx_0dtheta(i,:,:) = -nabla_x_f\nabla_theta_f;
end


%% Evaluation of objective function
%dJ/dtheta = fun(theta,x0,dx_0dtheta)

J = 0;
dJdtheta = zeros(n_theta+n_sigma,1);
y = x_0(2:n_x:end);
for i=1:n_r
    [Jr,grad_Jr] = J_fun(y,D.Ey(:,i),exp(sigma2)*ones(n_u,1));
    J = J + Jr;
    nabla_x_u_J = grad_Jr(1:length(y));
    nabla_sigma_J = grad_Jr(length(y)+1:end);
    dsigmadtheta = ones(n_u,1);
    nabla_sigma_J = nabla_sigma_J*(bsxfun(@times,dsigmadtheta,exp(sigma2)));
    dydtheta_u = squeeze(dx_0dtheta(:,n_x,:));
    dJdtheta = dJdtheta + [(nabla_x_u_J*dydtheta_u)';nabla_sigma_J'];
end

%% penalty function
[J_theta_pen,nabla_theta_J_pen,~] = J_pen([theta;z(n_theta+1:n_theta+n_sigma)],D.theta_max,D.theta_min,D.delta);
J = J + J_theta_pen;
dJdtheta = dJdtheta + nabla_theta_J_pen;

%% Save best known solution (in this run)
if J < J_old
    % theta_old = theta;
    x_0_old = x_0;
    J_old = J;
    save('current_state','theta_old','x_0_old','J_old')
end
end

