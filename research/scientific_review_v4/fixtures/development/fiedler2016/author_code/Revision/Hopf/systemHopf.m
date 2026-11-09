function [J,dJdtheta,f,S,F] = systemvanDerPol(r,z,f_rhs,D)
[f,grad_f]=f_rhs(1,z);

nabla_theta_f = grad_f(:,1);
nabla_x_f = grad_f(:,2:3);
% Sensitivity matrix (S)
S = -nabla_x_f\nabla_theta_f;
F = eye(1);
J = 0.5*sum(D-z(2:3))^2;
dJdtheta = -(D-z(2:3))'*S;
end