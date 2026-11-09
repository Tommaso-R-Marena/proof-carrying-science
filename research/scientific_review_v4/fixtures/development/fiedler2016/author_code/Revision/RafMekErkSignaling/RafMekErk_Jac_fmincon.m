function varargout = RafMekErk_Jac_fmincon(t, x, phi, k, n_sigma)
p = exp(phi(1:20));
n_x = length(x);
%n_sigma = 8;

xdot = [((exp(-t/p(10))*(exp(-t/p(9)) - 1) - p(8))*(x(1) - 1)*p(2)*p(7))/(p(7) + x(3)) - p(1)*x(1);
- p(3)*x(2) - ((x(2) - 1)*p(4)*x(1))/(k(1)/p(11) + 1);
- p(5)*x(3) - ((x(3) - 1)*p(6)*x(2))/(k(2)/p(12) + 1)];

nabla_x_f = [((exp(-t/p(10))*(exp(-t/p(9)) - 1) - p(8))*p(2)*p(7))/(p(7) + x(3)) - p(1), 0, -((exp(-t/p(10))*(exp(-t/p(9)) - 1) - p(8))*(x(1) - 1)*p(2)*p(7))/(p(7) + x(3))^2;
-((x(2) - 1)*p(4)*p(11))/(k(1) + p(11)), - p(3) - (p(4)*x(1))/(k(1)/p(11) + 1), 0;
0, -((x(3) - 1)*p(6)*p(12))/(k(2) + p(12)), - p(5) - (p(6)*x(2))/(k(2)/p(12) + 1)];

nabla_theta_f = [-x(1), ((exp(-t/p(10))*(exp(-t/p(9)) - 1) - p(8))*(x(1) - 1)*p(7))/(p(7) + x(3)), 0, 0, 0, 0, ((exp(-t/p(10))*(exp(-t/p(9)) - 1) - p(8))*(x(1) - 1)*p(2))/(p(7) + x(3)) - ((exp(-t/p(10))*(exp(-t/p(9)) - 1) - p(8))*(x(1) - 1)*p(2)*p(7))/(p(7) + x(3))^2, -((x(1) - 1)*p(2)*p(7))/(p(7) + x(3)), (t*exp(-t/p(9))*exp(-t/p(10))*(x(1) - 1)*p(2)*p(7))/((p(7) + x(3))*p(9)^2), (t*exp(-t/p(10))*(x(1) - 1)*(exp(-t/p(9)) - 1)*p(2)*p(7))/((p(7) + x(3))*p(10)^2), 0, 0, 0, 0, 0, 0, 0, 0, 0, 0;
0, 0, -x(2), -((x(2) - 1)*p(11)*x(1))/(k(1) + p(11)), 0, 0, 0, 0, 0, 0, -((x(2) - 1)*k(1)*p(4)*x(1))/(k(1) + p(11))^2, 0, 0, 0, 0, 0, 0, 0, 0, 0;
0, 0, 0, 0, -x(3), -((x(3) - 1)*p(12)*x(2))/(k(2) + p(12)), 0, 0, 0, 0, 0, -((x(3) - 1)*k(2)*p(6)*x(2))/(k(2) + p(12))^2, 0, 0, 0, 0, 0, 0, 0, 0];

nabla_theta_f = nabla_theta_f*diag(p);

    if nargout == 1
        varargout{1} = [xdot nabla_theta_f nabla_x_f];
    else
        varargout{1} = [];
        varargout{2} = -xdot;
        varargout{3} = [];
        %varargout{4} = -[nabla_theta_f nabla_x_f zeros(n_x,n_sigma)]';
        %falsche Reihenfolge? Noch einmal mit neuer probieren.
        varargout{4} = -[nabla_theta_f zeros(n_x,n_sigma) nabla_x_f]';
    end
end