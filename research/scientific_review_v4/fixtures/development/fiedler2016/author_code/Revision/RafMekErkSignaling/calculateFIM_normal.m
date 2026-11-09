function FIM = calculateFIM_normal(y_m,y,sigma2,dydtheta,dsigmadtheta,d2sigmadtheta2)
ind = find(~isnan(y_m));

grad_J = zeros(size(y_m));
grad_J(ind) = (y_m(ind)-y(ind))./sigma2(ind);

grad_J_sig = zeros(size(y_m));
grad_J_sig(ind) = 0.5*1./sigma2(ind).*(1-(y_m(ind)-y(ind)).^2./sigma2(ind));

A = sum(bsxfun(@times,permute(bsxfun(@times,1./sigma2(:),dydtheta),[2,3,1]),permute(dydtheta,[3,2,1])),3);
C1 = sum(bsxfun(@times,permute(bsxfun(@times,grad_J./sigma2(:),dsigmadtheta),[2,3,1]),...
    permute(dydtheta,[3,2,1])),3);
C2 = sum(bsxfun(@times,permute(bsxfun(@times,grad_J./sigma2(:),dydtheta),[2,3,1]),...
    permute(dsigmadtheta,[3,2,1])),3);
% Cp = sum(bsxfun(@times,permute(bsxfun(@times,grad_J./sigma2(:),dydtheta),[2,3,1]),...
%     permute(dsigmadtheta,[3,2,1])),3);
D = sum(bsxfun(@times,permute(grad_J_sig,[3,2,1]),d2sigmadtheta2),3); % d2sigmadtheta2 stack of Hessian size(length(theta),length(theta),length(y))
%B = diag(0.5*(sigma2(:)'.*(grad_J.^2))*dsigmadtheta);
B = sum(bsxfun(@times,permute(bsxfun(@times,-(1./sigma2(:)).*grad_J_sig + 0.5*(1./sigma2(:)).*(grad_J.^2),dsigmadtheta),[2,3,1]),...
    permute(dsigmadtheta,[3,2,1])),3);

FIM = A + C1 + C2 + B + D;
end