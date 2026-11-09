function [J,grad_J,S_theta] = J_theta_quadPen(theta,theta_max,theta_min,delta)
% Find non NaN values
ind_max = find(~isnan(theta_max));
ind_max2 = ~isinf(theta_max(ind_max));
ind_max = ind_max(ind_max2);
ind_min = find(~isnan(theta_min));
ind_min2 = ~isinf(theta_min(ind_min));
ind_min = ind_min(ind_min2);

% evaluate Objectivefunction
J = 0;
J = J + sum(delta*(max(0,theta_min(ind_min)-theta(ind_min)).^3)+delta*(max(0,theta(ind_max)-theta_max(ind_max)).^3));


% calculate gradient
grad_J = zeros(size(theta));
grad_J(ind_max) = delta*3*(max(0,theta(ind_max)-theta_max(ind_max)).^2);
grad_J(ind_min) = grad_J(ind_min)-3*delta*(max(0,-theta(ind_min)+theta_min(ind_min)).^2);

% calculate contribution to Fisher Information 
s_diag = zeros(size(theta));
s_diag(ind_max) = 6*delta*(max(0,theta(ind_max)-theta_max(ind_max)));
s_diag(ind_min) = s_diag(ind_min)+6*delta*(max(0,theta_min(ind_min)-theta(ind_min)));
S_theta = diag(s_diag);
end