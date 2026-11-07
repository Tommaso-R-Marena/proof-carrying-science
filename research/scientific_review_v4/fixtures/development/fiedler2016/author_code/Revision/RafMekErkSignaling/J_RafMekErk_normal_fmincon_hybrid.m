function [J,dJdtheta] = J_RafMekErk_normal_fmincon_hybrid(z,J_fun,J_prior,J_pen,f_rhs,f_fun,D,options)
%save ('test_stupid_error','z')
global errorCount
eps_x0 = options.xTol;% 1e-8;
eps = options.convTol;% 1e-9;

n_theta = options.n_theta;
n_x = options.n_x;
n_sigma = length(z)-n_theta;
u = D.conditions;
n_u = size(u,1);
n_r = size(D.measurement{1},2);

u_s = D.u_s;
xi = z(1:n_theta);% (log) parameters
theta = exp(xi);
noise2 = repmat(z(n_theta+1:n_theta+n_sigma)',length(D.t{1}),n_r/2); % sigma_pMek sigma_pErk
%% Load steady state for previous best known solution (in this run)
load('current_state');

%% Simulate till steady state is reached
converged = false;
x_0 = x_0_old;
T = 1;
while ~converged
    % model with feedback
    % ts_sust_Ras and ts_trans_Ras = theta(9,10) are set to 0 for the steadystate calulation
    % [status,~,X,~,~,~,sol] = f_fun([0,T],[theta(1:8);0;0;theta(11:end);x_0],u_s);     
    % model without feedback
    [status,~,X,~,~,~,sol] = f_fun([0,T],[theta(1:7);0;0;theta(10:end);x_0],u_s);     
    x_0 = X(end,:)';
    if max(abs(sol.xdot(end,:)'./(x_0+eps_x0)) > eps)
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
% S=dx_0dtheta = - Jacobian(theta,x_0)^(-1)*df/dtheta(theta,x_0); % sensitivity

% for log parameters
[grad_f]=f_rhs(0,x_0,xi,u_s);
f = grad_f(:,1);
nabla_theta_f = grad_f(:,2:n_theta+1);
nabla_x_f = grad_f(:,n_theta+2:end);
% Sensitivity matrix (S)
try
    S = -nabla_x_f\nabla_theta_f;%-pinv(nabla_x_f+diag(diag(nabla_x_f+1e-5))*1e-4*eye(n_x))*nabla_theta_f;
catch
    S = -pinv(nabla_x_f)*nabla_theta_f;%-(nabla_x_f+diag(diag(nabla_x_f)+1e-3*max(diag(nabla_x_f)))*1e-2)\nabla_theta_f;%S = -nabla_x_f\nabla_theta_f;
%    S = -(nabla_x_f+diag(diag(nabla_x_f+1e-5))*1e-4*eye(n_x))\nabla_theta_f;%S = -nabla_x_f\nabla_theta_f;
end

%% Evaluation of objective function
%dJ/dtheta = fun(theta,x0,dx_0dtheta)

J = 0;
dJdtheta = zeros(length(z),1);
for i = 1:n_u
    t_m = D.t{i};
    n_t = length(t_m);
    [status,~,~,y_i,~,sy_i,~] = f_fun(t_m,[theta;x_0],u(i,:));
    if status<0
        errorCount = errorCount-1;
    end
    y = y_i(:);
    S_theta = reshape(sy_i(:,:,1:n_theta),[],n_theta)*diag(theta);
    S_x0 = reshape(sy_i(:,:,n_theta+1:end),[],n_x);
    %% Computation of derivatives
    scale = theta(end-n_r+1:end)';
    sigma2 = bsxfun(@times,exp(noise2),scale.^2);
    
    dsigma2dtheta = zeros(length(y),n_sigma);
    dsigma2dtheta([1:n_t,2*n_t+1:3*n_t,4*n_t+1:5*n_t,6*n_t+1:7*n_t],1) = ones(n_t*n_r/2,1);
    dsigma2dtheta([n_t+1:2*n_t,3*n_t+1:4*n_t,5*n_t+1:6*n_t,7*n_t+1:8*n_t],2) = ones(n_t*n_r/2,1);
    
    dscaledtheta = zeros(length(y),n_r);
    dscaledtheta(1:n_t,1) = 2*ones(n_t,1);
    dscaledtheta(n_t+1:2*n_t,2) = 2*ones(n_t,1);
    dscaledtheta(2*n_t+1:3*n_t,3) = 2*ones(n_t,1);
    dscaledtheta(3*n_t+1:4*n_t,4) = 2*ones(n_t,1);
    dscaledtheta(4*n_t+1:5*n_t,5) = 2*ones(n_t,1);
    dscaledtheta(5*n_t+1:6*n_t,6) = 2*ones(n_t,1);
    dscaledtheta(6*n_t+1:7*n_t,7) = 2*ones(n_t,1);
    dscaledtheta(7*n_t+1:8*n_t,8) = 2*ones(n_t,1);
    
    dsigmadtheta = [zeros(length(y),n_theta-n_r),...
        bsxfun(@times,dscaledtheta,sigma2(:)),bsxfun(@times,dsigma2dtheta,sigma2(:))];
    
    % Parameter derivative
    dyxi_ik = S_theta + S_x0*S;
    dyxi_ik = [dyxi_ik, zeros(length(y),n_sigma)];
    %% Objective function (J)
    [J_i,grad_J] = J_fun(D.measurement{i}(:),y,sigma2(:),dyxi_ik,dsigmadtheta);
    J = J + J_i;
    
    dJdtheta = dJdtheta + grad_J;
end
%% prior function
[J_theta_prior,nabla_theta_J_prior,~] = J_prior([xi;z(n_theta+1:n_theta+n_sigma)],D.prior,D.sigma);
J = J + J_theta_prior;
dJdtheta = dJdtheta + [nabla_theta_J_prior];

%% penalty function
[J_theta_pen,nabla_theta_J_pen,~] = J_pen([xi;z(n_theta+1:n_theta+n_sigma)],D.theta_max,D.theta_min,D.delta);
J = J + J_theta_pen;
dJdtheta = dJdtheta + [nabla_theta_J_pen];

%% Save best known solution (in this run)
if J < J_old
    % theta_old = theta;
    x_0_old = x_0;
    J_old = J;
    save('current_state','theta_old','x_0_old','J_old')
end
end
end