% D = struct with D.measurements, D.conditions and D.t{i} time points for
% condition i
% noise ~ N(0,sigma_pMek*scaling) bzw. N(0, sigma_pErk*scaling)
function [J,dJdxi,f,S,F] = system_timeseriesDataCR(r,z,J_fun,f_fun,f_rhs,D,options)
%% Options
n_theta = options.n_theta;
n_x = length(z)-options.n_x;

u = D.conditions;
n_u = size(u,1);
n_r = size(D.measurement{1},2);

u_s = D.u_s;

theta = z(1:n_theta);
x_0 = z(n_theta+1:end);
%% System (f)
% Right-hand side of model for log parameters
[f,grad_f]=f_rhs(0,[theta;x_0],u_s);


nabla_theta_f = grad_f(1:n_theta);
nabla_x_f = grad_f(n_theta+1:end);

%f = [f,nabla_x_f];

% Sensitivity matrix (S)
S = -nabla_x_f\nabla_theta_f;

%% Assignment of parameters (theta) and states (x)
J = 0;
S_y = zeros(n_theta);
dJdxi = zeros(n_theta,1);

for i = 1:n_u
    t_m = D.t{i};
    ic = [0,0,1]';
    
    % evtl. an f_fun anpassen
    [~,x_sens] = ode15s(@(t,x) f_fun(t,[theta;x],u(i,:)),t_m,[x_0;ic]);
    
    xs = x_sens(:,1)';
    S_theta = x_sens(:,2:3);
    S_x0 = x_sens(:,4:end);
    
    %% Computation of derivatives
    % Parameter derivative
    dyxi_ik = S_theta + S_x0*S;
    
    %% Objective function (J)
    [J_i,grad_J] = J_fun(D.measurement{i}(:),xs(:),dyxi_ik);
    J = J + J_i;
  
    %% Calculation of FIM    
    %S_y = S_y + calculateFIM_normal(D.measurement{i}(:),y,sigma2(:),dyxi_ik,dsigmadtheta,d2sigmadtheta2);
    dJdxi = dJdxi + grad_J;
end

% Fischer Information
F = eye(n_theta+n_x);%S_y+diag(diag(S_y)+max(diag(S_y)))*1e+0+S_xi_prior+S_xi_pen;
end