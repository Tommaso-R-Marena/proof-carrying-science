function [J,grad_J,S_theta] = J_theta_normalPrior(theta,theta_prior,sigma)
ind = find(~isnan(theta_prior));

% J=sum(0.5*(log(2*pi*sigma^2)+(theta(ind)-theta_prior(ind)).^2/sigma^2));
J=sum(0.5*((theta(ind)-theta_prior(ind)).^2/sigma^2));
grad_J = zeros(size(theta));
grad_J(ind) = (theta(ind)-theta_prior(ind))/sigma^2;
s_diag = zeros(size(theta));
s_diag(ind) = 1/sigma^2*ones(1,length(ind));
S_theta = diag(s_diag);
end