function [J,dJdtheta,f,S,F] = systemHysteresis(r,z,f_rhs,D)
[f,grad_f]=f_rhs(1,z);

nabla_theta_f = grad_f(1);
nabla_x_f = grad_f(2);
% Sensitivity matrix (S)
S = -nabla_x_f\nabla_theta_f;
F = eye(1);
J = 0.5*(D-z(2))^2;
dJdtheta = -(D-z(2))*S;
end
