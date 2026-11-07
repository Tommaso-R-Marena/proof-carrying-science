function [J,dJdtheta,f,S,F] = system_ErkDoseResp_JNormal(r,z,J_fun,J_pen,f_rhs,D,options)
%% Options
n_theta = options.n_theta;
n_x = options.n_x;

u = D.u;
n_u = length(u);
n_r = size(D.Ey,2);
n_sigma = length(z)-n_x*n_u-n_theta;

theta = z(1:n_theta);% parameters
x_0 = z(n_theta+n_sigma+1:end); % states
sigma2 = z(n_theta+1:n_theta+n_sigma); % noise

%% Assignment of parameters (theta) and states (x)
f =zeros(n_u,n_x);
S_dr = zeros(n_u,n_x,n_theta);
for i = 1:n_u
   [grad_f(:,:)]=f_rhs(1,x_0(1+(i-1)*n_x:i*n_x),theta,u(i));
   f(i,:) = grad_f(:,1)';
   nabla_theta_f = grad_f(:,2:n_theta+1);
   nabla_x_f = grad_f(:,n_theta+2:end);
   % Sensitivity matrix (S)
   S_dr(i,:,:) = -nabla_x_f\nabla_theta_f;
end

S = reshape(permute(S_dr,[2,1,3]),n_x*n_u,[]);
%S = bsxfun(@times,permute(S_dr,[1,3,2]), permute(S_dr,[3,1,2]));
x0_mat = reshape(x_0,n_x,[]);
y = x0_mat(n_x,:);
% dJdtheta = (nabla_theta_J + nabla_x_J*S)';
% f = [f;nabla_x_f];
f = f';
f = f(:);
%% Objective function (J)
J = 0;
S_y = zeros(n_theta+n_sigma);
dJdtheta = zeros(n_theta+n_sigma,1);

for i=1:n_r
    [Jr,grad_Jr] = J_fun(y',D.Ey(:,i),exp(sigma2)*ones(n_u,1));
    J = J + Jr;
    nabla_x_u_J = grad_Jr(1:length(y));
    nabla_sigma_J = grad_Jr(length(y)+1:end);
    dsigmadtheta = ones(n_u,1);
    nabla_sigma_J = nabla_sigma_J*(bsxfun(@times,dsigmadtheta,exp(sigma2)));
    
    dydtheta_u = squeeze(S_dr(:,n_x,:));
    
    A = sum(bsxfun(@times,permute(bsxfun(@times,1./exp(sigma2(:)),dydtheta_u),[2,3,1]),permute(dydtheta_u,[3,2,1])),3);
    %A = sum(bsxfun(@times,permute(dydtheta_u,[2,3,1]),permute(dydtheta_u,[3,2,1])),3);
    C = bsxfun(@times,-nabla_x_u_J,dsigmadtheta')*dydtheta_u;
    Cp = C';
    B = diag(0.5*(exp(sigma2(:))'.*(nabla_x_u_J.^2))*dsigmadtheta);
    S_y = S_y + [A , Cp; C, B];
    
    dJdtheta = dJdtheta + [(nabla_x_u_J*dydtheta_u)';nabla_sigma_J'];
end
S = [S, zeros(n_x*n_u,n_sigma)];

%% penalty function
[J_theta_pen,nabla_theta_J_pen,S_theta_pen] = J_pen([theta;z(n_theta+1:n_theta+n_sigma)],D.theta_max,D.theta_min,D.delta);
%[J_theta_pen,nabla_theta_J_pen,S_theta_pen] = J_pen(theta,D.theta_max,D.theta_min,D.delta*exp(max(0.1*r,100)));
J = J + J_theta_pen;
dJdtheta = dJdtheta + nabla_theta_J_pen;

%% Fisher Information matrix
%F = S_y+diag(diag(S_y+1e-2))*1e-2;%*eye(n_theta+n_sigma); %
F = S_y+diag(diag(S_y)+max(diag(S_y)))*1e+0+S_theta_pen;%*eye(n_theta+n_sigma); %
%F = nearestSPD(S_y)+1e-4*eye(n_theta+n_sigma);
%F = diag(diag(S_y)+max(diag(S_y)))*1e-2;
end