% D = struct with D.measurements, D.conditions and D.t{i} time points for
% condition i
% noise ~ N(0,sigma_pMek*scaling) bzw. N(0, sigma_pErk*scaling)
function [J,dJdxi,f,S,F] = system_timeseriesData_JNormal_lin_v2(r,z,J_fun,J_prior,J_pen,f_fun,f_rhs,D,options)
%% Options
global errorCount
n_theta = options.n_theta;
n_x = options.n_x;
n_sigma = length(z)-n_theta-n_x;
u = D.conditions;
n_u = size(u,1);
n_r = size(D.measurement{1},2);

u_s = D.u_s;
xi = z(1:n_theta);% (log) parameters
theta = exp(xi);% lin parameters
x_0 = z(n_theta+n_sigma+1:end); % lin initial states
noise2 = repmat(z(n_theta+1:n_theta+n_sigma)',length(D.t{1}),n_r/2); % sigma_pMek sigma_pErk
%% System (f)
% Right-hand side of model for log parameters
[grad_f]=f_rhs(0,x_0,xi,u_s);
f = grad_f(:,1);
nabla_theta_f = grad_f(:,2:n_theta+1);
nabla_x_f = grad_f(:,n_theta+2:end);
f = [f,nabla_x_f];
% Sensitivity matrix (S)
try
    S = -(nabla_x_f+diag(diag(nabla_x_f)+1e-3*max(diag(nabla_x_f)))*1e-2)\nabla_theta_f;%S = -nabla_x_f\nabla_theta_f;
%    S = -(nabla_x_f+diag(diag(nabla_x_f+1e-5))*1e-4*eye(n_x))\nabla_theta_f;%S = -nabla_x_f\nabla_theta_f; 
catch
    S = -pinv(nabla_x_f+diag(diag(nabla_x_f+1e-5))*1e-4*eye(n_x))*nabla_theta_f;
end
%% Assignment of parameters (theta) and states (x)
%y = zeros(size(D.measurement));
% n_y = length(y);
J = 0;
S_y = zeros(n_theta+n_sigma);
dJdxi = zeros(n_theta+n_sigma,1);
%n_t1 = 1;
for i = 1:n_u
    t_m = D.t{i};
    n_t = length(t_m);
    % evtl. an f_fun anpassen
    [status,~,~,y_i,~,sy_i,~] = f_fun(t_m,[theta;x_0],u(i,:));
    if status<0
        errorCount = errorCount-1;
    end
%     if max(max(isnan(y_i)))
%         y_i;
%     end
    y = y_i(:);
    S_theta = reshape(sy_i(:,:,1:n_theta),[],n_theta)*diag(theta);
    S_x0 = reshape(sy_i(:,:,n_theta+1:end),[],n_x);
    % nt_1 = n_t1 + length(y_i(:))-1;
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
    
    % Second derivative
    d2sigmadtheta2 = zeros(n_theta+n_sigma,n_theta+n_sigma,length(y));
    for k = 1:length(y)
        d2sigmadtheta2(n_theta-n_r+ceil(k/n_t),n_theta-n_r+ceil(k/n_t),k) = 4;
        d2sigmadtheta2(n_theta-n_r+ceil(k/n_t),n_theta+2-mod(ceil(k/n_t),n_sigma),k) = 2;
        d2sigmadtheta2(n_theta+2-mod(ceil(k/n_t),n_sigma),n_theta-n_r+ceil(k/n_t),k) = 2;
        d2sigmadtheta2(n_theta+2-mod(ceil(k/n_t),n_sigma),n_theta+2-mod(ceil(k/n_t),n_sigma),k) = 1;
    end
    
    d2sigmadtheta2 = bsxfun(@times,permute(sigma2(:),[3,2,1]),d2sigmadtheta2);
    
    %% Objective function (J)
    [J_i,grad_J] = J_fun(D.measurement{i}(:),y,sigma2(:),dyxi_ik,dsigmadtheta);
    J = J + J_i;
  
    %% Calculation of FIM    
    S_y = S_y + calculateFIM_normal(D.measurement{i}(:),y,sigma2(:),dyxi_ik,dsigmadtheta,d2sigmadtheta2);
    dJdxi = dJdxi + grad_J;
end
S = [S, zeros(n_x,n_sigma)];
% prior
[J_xi_prior,nabla_xi_J_prior, S_xi_prior] = J_prior([xi;z(n_theta+1:n_theta+n_sigma)],D.prior,D.sigma);
J = J + J_xi_prior;
dJdxi = dJdxi + nabla_xi_J_prior;
% F = S_y+diag(diag(S_y+1e-5))*1e-4*eye(n_theta)+1/D.sigma^2*eye(n_theta);

% penalty
[J_xi_pen,nabla_xi_J_pen,S_xi_pen] = J_pen([xi;z(n_theta+1:n_theta+n_sigma)],D.theta_max,D.theta_min,D.delta);
J = J + J_xi_pen;
dJdxi = dJdxi + nabla_xi_J_pen;

% Fischer Information
% F = S_y+diag(diag(S_y+1e-5))*1e-4*eye(n_theta+n_sigma)+S_theta_prior+S_theta_pen;
F = S_y+diag(diag(S_y)+max(diag(S_y)))*1e+0+S_xi_prior+S_xi_pen;
end