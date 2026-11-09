function [J,dJdtheta] = J_normalv2(y_m,y,sigma2,dydtheta,dsigma2dtheta)
% calculation of loglikelihood value for non NaNs 
ind = find(~isnan(y_m));
J=sum(0.5*(log(2*pi*sigma2(ind))+(y_m(ind)-y(ind)).^2./sigma2(ind)));

%calculation of gradient with respect to theta
grad_J = zeros(size(y_m));
grad_J(ind) = -(y_m(ind)-y(ind))./sigma2(ind);

% calculation of gradient with respect to sigma^2
grad_J_sig = zeros(size(y_m));
grad_J_sig(ind) = 0.5*1./sigma2(ind).*(1-(y_m(ind)-y(ind)).^2./sigma2(ind));

% grad_J = grad_J*dydtheta + grad_J*dydsigma2*dsigma2dtheta
dJdtheta = (grad_J' * dydtheta + grad_J_sig' * dsigma2dtheta)';
end