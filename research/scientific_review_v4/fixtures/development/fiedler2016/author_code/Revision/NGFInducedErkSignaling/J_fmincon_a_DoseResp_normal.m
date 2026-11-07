function [J_fmc,grad_J] = J_fmincon_a_DoseResp_normal(z,J_fun,J_pen,D,options)
n_theta = options.n_theta;
n_sigma = length(z)-n_theta;

xi = z(1:n_theta);
sigma2 = z(n_theta+1:n_theta+n_sigma);

z = 10.^xi;
u = D.u;

n_u = length(u);
n_r = size(D.Ey,2);

% analytical steady state
x_10 = @(xi,u) 10^xi(1).*u*10^xi(5)./(10^xi(1).*u+10^xi(2));
x_20 = @(x1,xi,u) (10^xi(3)+x1)*10^xi(6)./(10^xi(3)+x1+10^xi(4));

x10 = x_10(xi,u);
x20 = x_20(x10,xi,u);

y = x20(:)';

dx_20dx_10 = ((z(3)+x10(:)+z(4))*z(6)-(z(3)+x10(:))*z(6))./((z(3)+x10(:)+z(4)).^2);

dx_10dtheta = bsxfun(@times,[u(:).*z(5)*z(2)./((z(1)*u(:)+z(2)).^2)...
    -u(:).*z(5)*z(1)./((z(1)*u(:)+z(2)).^2)...
    zeros(length(u),2) u(:).*z(1)./(z(1)*u(:)+z(2)) zeros(length(u),1)],log(10)*z');

dydtheta = bsxfun(@times,[zeros(length(u),2)...
    (z(4)*z(6))./((z(3)+x10(:)+z(4)).^2)...
    -(z(3)+x10(:))*z(6)./((z(3)+x10(:)+z(4)).^2) zeros(length(u),1)...
    (z(3)+x10(:))./(z(3)+x10(:)+z(4))],log(10)*z')+bsxfun(@times,dx_20dx_10,dx_10dtheta);

%% optimization
J = 0;
dJdtheta = zeros(n_theta+n_sigma,1);
for i=1:n_r
    [Jr,grad_Jr] = J_fun(y(:),D.Ey(:,i),exp(sigma2)*ones(n_u,1));
    J = J + Jr;
    nabla_x_u_J = grad_Jr(1:length(y));
    nabla_sigma_J = grad_Jr(length(y)+1:end);
    dsigmadtheta = ones(n_u,1);
    nabla_sigma_J = nabla_sigma_J*(bsxfun(@times,dsigmadtheta,exp(sigma2)));
    
    dJdtheta = dJdtheta + [(nabla_x_u_J*dydtheta)';nabla_sigma_J'];
end

[J_theta_pen,nabla_theta_J_pen,~] = J_pen([xi;sigma2],D.theta_max,D.theta_min,D.delta);
J = J + J_theta_pen;
J_fmc = J;

grad_J =dJdtheta +nabla_theta_J_pen;
end