function varargout = f_fmincon_DoseResp_v2(x,xi,D)
theta = 10.^xi;
n_x = length(x);
n_theta = length(theta);

u = D.u;
n_u = length(u);

xdot = zeros(n_x,1);
nabla_theta_f = zeros(n_x, n_theta);
nabla_x_f = zeros(n_x, n_x);

for i=1:n_u
    xdot(1+(i-1)*n_x/n_u) =  theta(1)*u(i)*( theta(5) - x(1+(i-1)*n_x/n_u)) -  theta(2)*x(1+(i-1)*n_x/n_u);
    xdot(2+(i-1)*n_x/n_u) = (x(1+(i-1)*n_x/n_u) + theta(3))*( theta(6) - x(2+(i-1)*n_x/n_u)) -  theta(4)*x(2+(i-1)*n_x/n_u);
    
    nabla_x_f(1+(i-1)*n_x/n_u:2+(i-1)*n_x/n_u,1+(i-1)*n_x/n_u:2+(i-1)*n_x/n_u) = [-theta(1)*u(i)-theta(2) 0;
                                theta(6)-x(2+(i-1)*n_x/n_u) -x(1+(i-1)*n_x/n_u)-theta(3)-theta(4)];
    nabla_theta_f(1+(i-1)*n_x/n_u,1)= u(i)*(theta(5)-x(1+(i-1)*n_x/n_u));
    nabla_theta_f(1+(i-1)*n_x/n_u,5)= theta(1)*u(i);
    nabla_theta_f(1+(i-1)*n_x/n_u,2)= -x(1+(i-1)*n_x/n_u);
    nabla_theta_f(2+(i-1)*n_x/n_u,4)= -x(2+(i-1)*n_x/n_u);
    nabla_theta_f(2+(i-1)*n_x/n_u,3)= theta(6)-x(2+(i-1)*n_x/n_u);
    nabla_theta_f(2+(i-1)*n_x/n_u,6)= x(1+(i-1)*n_x/n_u)+theta(3);
end
nabla_theta_f = log(10)*bsxfun(@times,nabla_theta_f,theta');
varargout{1} = [];
varargout{2} = -xdot;
varargout{3} = [];
varargout{4} = -[nabla_theta_f nabla_x_f]';
%varargout{1} = -xdot;
%varargout{2} = -[nabla_theta_f nabla_x_f];
end
