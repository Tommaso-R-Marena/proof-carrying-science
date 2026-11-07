function [f,grad_f] = vanDerPolODE(r,z)
% z(1)=mu, z(2)=x, z(3)=y
% x'=-y+x(mu-x^2-y^2); y'=x+y(mu-x^2-y^2) supercritical Hopfbifurcation

f = [-z(3)+z(2)*(z(1)-z(2)^2-z(3)^2);z(2)+z(3)*(z(1)-z(2)^2-z(3)^2)];

dfdtheta=[z(2);z(3)];
dfdx=[z(1)-z(2)^2-z(3)^2-2*z(2)^2;1-2*z(2)*z(3)];
dfdy=[-1-2*z(2)*z(3);z(1)-z(2)^2-z(3)^2-2*z(3)^2];

grad_f = [dfdtheta dfdx dfdy];
end