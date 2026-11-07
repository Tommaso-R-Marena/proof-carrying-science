function [J,dJdxi] = J_RafMekErk_normal_lin_fminconv2(z,f_fun,J_fun,J_prior,J_pen,D,options)
global errorCount
n_theta = options.n_theta;
n_x = options.n_x;
u = D.conditions;
n_u = size(u,1);
n_sigma = length(z)-n_theta-n_x;
n_r = size(D.measurement{1},2);

xi = z(1:n_theta);% (log) parameters
theta = exp(xi); %lin parameters
x_0 = z(n_theta+n_sigma+1:end); % lin initial states
noise2 = repmat(z(n_theta+1:n_theta+n_sigma)',length(D.t{1}),n_r/2); % sigma_pMek sigma_pErk

J = 0;
dJdxi = zeros(length(z),1);
%n_t1 = 1;
for i = 1:n_u
    t_m = D.t{i};
    n_t = length(t_m);
    % evtl. an f_fun anpassen
    [status,~,~,y_i,~,sy_i,~] = f_fun(t_m,[theta;x_0],u(i,:));
    if status<0
        errorCount = errorCount-1;
    end
    y = y_i(:);
    S_xi = reshape(sy_i(:,:,1:n_theta),[],n_theta)*diag(theta);
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
                    bsxfun(@times,dscaledtheta,sigma2(:)),bsxfun(@times,dsigma2dtheta,sigma2(:)),...
                    zeros(length(y),n_x)];
                
    % Parameter derivative
    dydxi_ik = [S_xi,zeros(length(y),n_sigma),S_x0];
                
    %% Objective function (J)
    [J_i,grad_J] = J_fun(D.measurement{i}(:),y,sigma2(:),dydxi_ik,dsigmadtheta);
    J = J + J_i;
    
    %% Vector field
    
    dJdxi = dJdxi + grad_J;
end
% prior
[J_xi_prior,nabla_xi_J_prior,~] = J_prior([xi;z(n_theta+1:n_theta+n_sigma)],D.prior,D.sigma);
J = J + J_xi_prior;
dJdxi = dJdxi + [nabla_xi_J_prior;zeros(n_x,1)];

% penalty
[J_xi_pen,nabla_xi_J_pen,~] = J_pen([xi;z(n_theta+1:n_theta+n_sigma)],D.theta_max,D.theta_min,D.delta);
J = J + J_xi_pen;
dJdxi = dJdxi + [nabla_xi_J_pen;zeros(n_x,1)];
end