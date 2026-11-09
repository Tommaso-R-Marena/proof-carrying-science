function [J_fmc,grad_J] = J_fmincon_DoseResp_normal(z,J_fun,J_pen,D,options)
n_theta = options.n_theta;
n_x = options.n_x;

u = options.u;
n_u = length(u);
n_r = size(D.Ey,2);

n_sigma = length(z)-n_x*n_u-n_theta;

theta = z(1:n_theta);% parameters
sigma2 = z(n_theta+1:n_theta+n_sigma); % noise
y = z(n_theta+n_sigma+n_x:n_x:end);

J = 0;
dJdtheta = zeros(n_u+n_sigma,1);

for i=1:n_r
    [Jr,grad_Jr] = J_fun(y,D.Ey(:,i),exp(sigma2)*ones(n_u,1));
    J = J + Jr;
    nabla_x_u_J = grad_Jr(1:length(y));
    nabla_sigma_J = grad_Jr(length(y)+1:end);
    dsigmadtheta = ones(n_u,1);
    nabla_sigma_J = nabla_sigma_J*(bsxfun(@times,dsigmadtheta,exp(sigma2)));
    
    dJdtheta = dJdtheta + [nabla_sigma_J';nabla_x_u_J'];
end

[J_theta_pen,nabla_theta_J_pen,~] = J_pen([theta;z(n_theta+1:n_theta+n_sigma)],D.theta_max,D.theta_min,D.delta);
J = J + J_theta_pen;

J_fmc = J;
grad_J = [nabla_theta_J_pen;zeros(n_x*n_u,1)];
grad_J(n_theta+n_sigma) = grad_J(n_theta+n_sigma)+dJdtheta(1); 
grad_J(n_theta+n_sigma+n_x:n_x:end) = dJdtheta(2:end);
end