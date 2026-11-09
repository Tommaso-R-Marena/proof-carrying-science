function xdot = Erk_pathway_A_log_v2_xdot(t,x,theta,u)
theta = 10.^theta;
n_u = length(u);
n_x = length(x);
xdot = zeros(n_x,1);

for i=1:n_u
    xdot(1+(i-1)*n_x/n_u) =  theta(1)*u(i)*( theta(5) - x(1+(i-1)*n_x/n_u)) -  theta(2)*x(1+(i-1)*n_x/n_u);
    xdot(2+(i-1)*n_x/n_u) = (x(1+(i-1)*n_x/n_u) + theta(3))*( theta(6) - x(2+(i-1)*n_x/n_u)) -  theta(4)*x(2+(i-1)*n_x/n_u);
end

end
