function grad = Erk_pathway_A_log_v2(t,x,theta,u)
%n_x = options.n_x;
n_theta = length(theta);
theta = 10.^theta;
n_x = length(x);
%s_0theta = reshape(ic(n_x+1:n_x*(n_theta+1)),n_x,n_theta);
% s_0theta = s_0theta(:);
% s_0x1 = reshape(ic(n_x*(n_theta+1)+1:end),n_x,n_x);
% s_0x1 = s_0x1(:);

xdot = [theta(1)*u*(theta(5)-x(1))-theta(2)*x(1);...
       (theta(3) + x(1))*(theta(6)-x(2))-theta(4)*x(2)];
nabla_x_f = [-theta(1)*u-theta(2) 0;
             theta(6)-x(2) -x(1)-theta(3)-theta(4)];
nabla_theta_f = zeros(n_x, n_theta);
nabla_theta_f(1,1)= u*(theta(5)-x(1));
nabla_theta_f(1,2)= -x(1);
nabla_theta_f(1,5)= theta(1)*u;
nabla_theta_f(2,3)= theta(6)-x(2);
nabla_theta_f(2,4)= -x(2);
nabla_theta_f(2,6)= x(1)+theta(3);
%nabla_theta_f1 = bsxfun(@times,nabla_theta_f,theta'*log(10));
nabla_theta_f = nabla_theta_f*diag(theta)*log(10);
% output_S_theta = nabla_x_f*s_0theta+nabla_theta_f;
% output_S_x1 = nabla_x_f*s_0x1;
%if strcmp(options.sim,'steady-state')
grad = [xdot nabla_theta_f nabla_x_f];
%else   
%varargout{1} = xdot; %; output_S_theta(:); output_S_x1(:)];
%end
end
