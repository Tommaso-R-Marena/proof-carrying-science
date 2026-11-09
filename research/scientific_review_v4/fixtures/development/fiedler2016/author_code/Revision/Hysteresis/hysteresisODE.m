function [f,grad_f] = hysteresisODE(t,z)
n = 20;
K = 1; %2.4
g = 1; %2.5/3
b = 1; %4

f = b*(z(2)^n)/(K^n+z(2)^n)-g*z(2)+z(1);
grad_f = [1 b*(K^n*n*z(2)^(n-1))/((K^n+z(2)^n)^2)-g];
end