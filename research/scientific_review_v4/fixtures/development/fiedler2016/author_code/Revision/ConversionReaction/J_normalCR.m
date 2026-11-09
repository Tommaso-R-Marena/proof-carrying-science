function [J,dJdtheta] = J_normalCR(y_m,y,dydtheta)

% calculation of loglikelihood value for non NaNs 
ind = find(~isnan(y_m));
J=sum(0.5*((y_m(ind)-y(ind)).^2.));

%calculation of gradient with respect to theta
grad_J = zeros(size(y_m));
grad_J(ind) = -(y_m(ind)-y(ind));

% grad_J = grad_J*dydtheta + grad_J*dydsigma2*dsigma2dtheta
dJdtheta = (grad_J' * dydtheta)';
end