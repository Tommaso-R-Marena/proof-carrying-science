% event.m is used to stop the simulation based optimization if some stop
% criterium is fullfilled
%
% 2015/12/07 Anna Fiedler

function[value,isterminal,direction]=event(t,y)
% norm gradient dtheta
global ng
% norm relative gradient dxs 
global ngx
% maximal number of steps permitted
global maxSteps
% maximal number of failed biological ODE simulations permitted
global errorCount

value = [max(ng,ngx)-1e-6, maxSteps, errorCount];
isterminal = [1 1 1];
direction =[0 0 0];
end